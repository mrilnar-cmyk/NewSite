from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from .models import Formula, FormulaHistory


@receiver(pre_save, sender=Formula)
def formula_pre_save(sender, instance, **kwargs):
    """Сохраняем старые значения перед изменением"""
    if instance.pk:
        try:
            old_instance = Formula.objects.get(pk=instance.pk)
            instance._old_expression = old_instance.expression
            instance._old_values = {
                'name': old_instance.name,
                'symbol': old_instance.symbol,
                'unit': old_instance.unit,
                'is_input': old_instance.is_input,
                'default_value': old_instance.default_value,
                'category_id': old_instance.category_id,
            }
            instance._is_new = False
        except Formula.DoesNotExist:
            instance._is_new = True
    else:
        instance._is_new = True


@receiver(post_save, sender=Formula)
def formula_post_save(sender, instance, created, **kwargs):
    """Записываем в историю после сохранения"""
    if created:
        # Новая формула
        FormulaHistory.objects.create(
            formula=instance,
            action='created',
            new_expression=instance.expression,
            new_values={
                'name': instance.name,
                'symbol': instance.symbol,
                'unit': instance.unit,
                'is_input': instance.is_input,
                'default_value': instance.default_value,
                'category_id': instance.category_id,
            }
        )
    else:
        # Обновление формулы
        old_expression = getattr(instance, '_old_expression', '')
        old_values = getattr(instance, '_old_values', {})

        # Проверяем, были ли изменения
        new_values = {
            'name': instance.name,
            'symbol': instance.symbol,
            'unit': instance.unit,
            'is_input': instance.is_input,
            'default_value': instance.default_value,
            'category_id': instance.category_id,
        }

        if old_expression != instance.expression or old_values != new_values:
            FormulaHistory.objects.create(
                formula=instance,
                action='updated',
                old_expression=old_expression,
                new_expression=instance.expression,
                old_values=old_values,
                new_values=new_values
            )


@receiver(pre_delete, sender=Formula)
def formula_pre_delete(sender, instance, **kwargs):
    """Записываем удаление в историю"""
    # Создаём запись об удалении (привязываем к None)
    FormulaHistory.objects.create(
        formula=None,  # Формула будет удалена
        action='deleted',
        old_expression=instance.expression,
        old_values={
            'symbol': instance.symbol,
            'name': instance.name,
            'unit': instance.unit,
        }
    )