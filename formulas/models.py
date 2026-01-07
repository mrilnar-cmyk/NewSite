from django.db import models
from django.core.validators import RegexValidator

# Валидатор для символов формул (латиница, цифры, подчёркивание)
symbol_validator = RegexValidator(
    regex=r'^[a-zA-Z_][a-zA-Z0-9_]*$',
    message='Символ должен начинаться с буквы и содержать только латинские буквы, цифры и подчёркивание'
)


class Category(models.Model):
    """Категория для группировки формул"""

    name = models.CharField(
        'Название',
        max_length=100
    )
    description = models.TextField(
        'Описание',
        blank=True
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительская категория'
    )
    order = models.PositiveIntegerField(
        'Порядок сортировки',
        default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['order', 'name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name

    def get_full_path(self):
        """Получить полный путь категории"""
        if self.parent:
            return f"{self.parent.get_full_path()} → {self.name}"
        return self.name

    def get_all_formulas(self):
        """Получить все формулы категории и подкатегорий"""
        formulas = list(self.formulas.all())
        for child in self.children.all():
            formulas.extend(child.get_all_formulas())
        return formulas


class Formula(models.Model):
    """Математическая формула"""

    symbol = models.CharField(
        'Символ',
        max_length=50,
        unique=True,
        validators=[symbol_validator],
        help_text='Уникальный идентификатор (например: K, Re, alpha1)'
    )
    name = models.CharField(
        'Название',
        max_length=200,
        help_text='Понятное название формулы'
    )
    expression = models.TextField(
        'Выражение',
        blank=True,  # Разрешаем пустое значение
        default='',  # Значение по умолчанию
        help_text='Математическое выражение (например: R1 * (1 - cos(alpha)))'
    )
    unit = models.CharField(
        'Единица измерения',
        max_length=50,
        blank=True,
        help_text='Единица измерения результата (например: м, кг, Вт)'
    )
    description = models.TextField(
        'Описание',
        blank=True,
        help_text='Подробное описание формулы'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='formulas',
        verbose_name='Категория'
    )

    # Порядок вычисления (для сортировки)
    order = models.PositiveIntegerField(
        'Порядок',
        default=0
    )

    # Флаг: это входной параметр или вычисляемая формула
    is_input = models.BooleanField(
        'Входной параметр',
        default=False,
        help_text='Если отмечено - это входное значение, а не вычисляемая формула'
    )

    # Значение по умолчанию (для входных параметров)
    default_value = models.FloatField(
        'Значение по умолчанию',
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Формула'
        verbose_name_plural = 'Формулы'
        ordering = ['category', 'order', 'symbol']

    def __str__(self):
        return f"{self.symbol} — {self.name}"

    def get_display_expression(self):
        """Получить красиво отформатированное выражение"""
        expr = self.expression
        # Заменяем символы на красивые
        replacements = {
            '*': ' × ',
            'sqrt': '√',
            'pi': 'π',
            'alpha': 'α',
            'beta': 'β',
            'gamma': 'γ',
            'delta': 'δ',
            'lambda': 'λ',
            'rho': 'ρ',
            'sigma': 'σ',
            'theta': 'θ',
            'omega': 'ω',
        }
        for old, new in replacements.items():
            expr = expr.replace(old, new)
        return expr


class FormulaVariable(models.Model):
    """Переменная, используемая в формуле"""

    TYPE_CHOICES = [
        ('input', 'Ввод вручную'),
        ('formula', 'Результат другой формулы'),
    ]

    formula = models.ForeignKey(
        Formula,
        on_delete=models.CASCADE,
        related_name='variables',
        verbose_name='Формула'
    )
    symbol = models.CharField(
        'Символ переменной',
        max_length=50,
        validators=[symbol_validator]
    )
    name = models.CharField(
        'Название',
        max_length=100,
        blank=True
    )
    var_type = models.CharField(
        'Тип',
        max_length=20,
        choices=TYPE_CHOICES,
        default='input'
    )
    unit = models.CharField(
        'Единица измерения',
        max_length=50,
        blank=True
    )
    default_value = models.FloatField(
        'Значение по умолчанию',
        null=True,
        blank=True
    )

    # Ссылка на другую формулу (если var_type='formula')
    source_formula = models.ForeignKey(
        Formula,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_as_variable_in',
        verbose_name='Формула-источник'
    )

    class Meta:
        verbose_name = 'Переменная формулы'
        verbose_name_plural = 'Переменные формул'
        unique_together = ['formula', 'symbol']
        ordering = ['symbol']

    def __str__(self):
        return f"{self.symbol} ({self.formula.symbol})"


class CalculationSession(models.Model):
    """Сессия вычислений - сохранённый набор значений"""

    name = models.CharField(
        'Название',
        max_length=200,
        help_text='Например: Вариант 1 - Иванов'
    )
    description = models.TextField(
        'Описание',
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Сессия вычислений'
        verbose_name_plural = 'Сессии вычислений'
        ordering = ['-updated_at']

    def __str__(self):
        return self.name


class SessionValue(models.Model):
    """Значение в сессии (введённое или вычисленное)"""

    session = models.ForeignKey(
        CalculationSession,
        on_delete=models.CASCADE,
        related_name='values',
        verbose_name='Сессия'
    )
    formula = models.ForeignKey(
        Formula,
        on_delete=models.CASCADE,
        related_name='session_values',
        verbose_name='Формула'
    )
    value = models.FloatField(
        'Значение',
        null=True,
        blank=True
    )
    is_calculated = models.BooleanField(
        'Вычислено автоматически',
        default=False
    )

    class Meta:
        verbose_name = 'Значение сессии'
        verbose_name_plural = 'Значения сессий'
        unique_together = ['session', 'formula']

    def __str__(self):
        return f"{self.formula.symbol} = {self.value}"


# Добавьте эти модели в конец файла formulas/models.py

class Project(models.Model):
    """Проект (группа вариантов)"""
    name = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'
        ordering = ['-updated_at']

    def __str__(self):
        return self.name


class Variant(models.Model):
    """Вариант задания"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Проект'
    )
    number = models.PositiveIntegerField('Номер варианта')
    student_name = models.CharField('ФИО студента', max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Вариант'
        verbose_name_plural = 'Варианты'
        unique_together = ['project', 'number']
        ordering = ['project', 'number']

    def __str__(self):
        return f"Вариант {self.number}" + (f" ({self.student_name})" if self.student_name else "")


class VariantValue(models.Model):
    """Значение переменной в варианте (введённое или вычисленное)"""
    variant = models.ForeignKey(
        Variant,
        on_delete=models.CASCADE,
        related_name='values',
        verbose_name='Вариант'
    )
    formula = models.ForeignKey(
        Formula,
        on_delete=models.CASCADE,
        related_name='variant_values',
        verbose_name='Формула'
    )
    value = models.FloatField('Значение', null=True, blank=True)
    is_input = models.BooleanField('Введено вручную', default=True)

    class Meta:
        verbose_name = 'Значение варианта'
        verbose_name_plural = 'Значения вариантов'
        unique_together = ['variant', 'formula']

    def __str__(self):
        return f"{self.formula.symbol} = {self.value}"


class VariantGenerationRule(models.Model):
    """Правило генерации значений для вариантов"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='generation_rules',
        verbose_name='Проект'
    )
    formula = models.ForeignKey(
        Formula,
        on_delete=models.CASCADE,
        related_name='generation_rules',
        verbose_name='Формула (входной параметр)'
    )
    min_value = models.FloatField('Минимальное значение')
    max_value = models.FloatField('Максимальное значение')
    step = models.FloatField('Шаг', default=1)

    class Meta:
        verbose_name = 'Правило генерации'
        verbose_name_plural = 'Правила генерации'
        unique_together = ['project', 'formula']

    def __str__(self):
        return f"{self.formula.symbol}: {self.min_value} - {self.max_value}"


class FormulaHistory(models.Model):
    """История изменений формулы"""
    formula = models.ForeignKey(
        Formula,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name='Формула'
    )
    action = models.CharField('Действие', max_length=50)  # created, updated, deleted
    old_expression = models.TextField('Старое выражение', blank=True)
    new_expression = models.TextField('Новое выражение', blank=True)
    old_values = models.JSONField('Старые значения', null=True, blank=True)
    new_values = models.JSONField('Новые значения', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'История формулы'
        verbose_name_plural = 'История формул'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.formula.symbol} - {self.action} ({self.created_at})"