from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Получить значение из словаря по ключу"""
    if dictionary is None:
        return None
    return dictionary.get(key, '')


@register.filter
def floatformat_smart(value, decimals=4):
    """Форматирование числа с удалением лишних нулей"""
    if value is None:
        return ''
    try:
        formatted = f"{float(value):.{decimals}f}"
        # Удаляем лишние нули
        if '.' in formatted:
            formatted = formatted.rstrip('0').rstrip('.')
        return formatted
    except (ValueError, TypeError):
        return value