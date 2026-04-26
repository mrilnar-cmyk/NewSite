from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator

# Валидатор для символов формул (латиница, цифры, подчёркивание)
symbol_validator = RegexValidator(
    regex=r'^[a-zA-Z_][a-zA-Z0-9_]*$',
    message='Символ должен начинаться с буквы и содержать только латинские буквы, цифры и подчёркивание'
)


class Category(models.Model):
    """Категория для группировки формул"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='categories',
        verbose_name='Владелец'
    )
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


class Formula(models.Model):
    """Математическая формула"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='formulas',
        verbose_name='Владелец'
    )
    symbol = models.CharField(
        'Символ',
        max_length=50,
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
        blank=True,
        default='',
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
    order = models.PositiveIntegerField(
        'Порядок',
        default=0
    )
    is_input = models.BooleanField(
        'Входной параметр',
        default=False,
        help_text='Если отмечено - это входное значение, а не вычисляемая формула'
    )
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
        unique_together = ['user', 'symbol']

    def __str__(self):
        return f"{self.symbol} — {self.name}"

    def get_latex_symbol(self):
        """Красивый вывод symbol (с подчёркиваниями как в исходнике)."""
        s = (self.symbol or "").strip()
        if not s:
            return ""
        if len(s) == 1 and s.isalpha():
            return s
        return r'\mathrm{' + s.replace('_', r'\_') + '}'

    def get_display_expression(self):
        """Получить красиво отформатированное выражение"""
        expr = self.expression
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

    def get_latex_expression(self):
        """Преобразует expression (Python-подобное) в LaTeX для KaTeX, сохраняя скобки пользователя."""
        import re

        expr = (self.expression or "").strip()
        if not expr:
            return ""

        greek = {
            'alpha': r'\alpha', 'beta': r'\beta', 'gamma': r'\gamma',
            'delta': r'\delta', 'epsilon': r'\epsilon', 'zeta': r'\zeta',
            'eta': r'\eta', 'theta': r'\theta', 'lambda': r'\lambda',
            'mu': r'\mu', 'nu': r'\nu', 'xi': r'\xi', 'pi': r'\pi',
            'rho': r'\rho', 'sigma': r'\sigma', 'tau': r'\tau',
            'phi': r'\phi', 'chi': r'\chi', 'psi': r'\psi', 'omega': r'\omega',
        }

        def is_number(s: str) -> bool:
            try:
                float(s)
                return True
            except Exception:
                return False

        def symbol_to_latex(s: str) -> str:
            """Конвертация одиночного токена (переменная/число) -> LaTeX."""
            s = s.strip()
            if not s:
                return s
            if is_number(s):
                return s

            # греческие — только если токен РОВНО равен alpha/beta/... (не часть имени)
            if s in greek:
                return greek[s]

            # однобуквенные оставляем как есть
            if len(s) == 1 and s.isalpha():
                return s

            # все идентификаторы показываем как единое имя, "_" выводим буквально
            return r'\mathrm{' + s.replace('_', r'\_') + '}'

        def split_top_level(s: str, ops: set[str]):
            """Split by ops at top-level parentheses depth."""
            parts = []
            ops_found = []
            depth = 0
            cur = []
            i = 0
            while i < len(s):
                ch = s[i]
                if ch == '(':
                    depth += 1
                    cur.append(ch)
                elif ch == ')':
                    depth -= 1
                    cur.append(ch)
                elif depth == 0 and ch in ops:
                    # allow unary minus at start
                    if ch == '-' and not ''.join(cur).strip() and not parts:
                        cur.append(ch)
                    else:
                        parts.append(''.join(cur).strip())
                        ops_found.append(ch)
                        cur = []
                else:
                    cur.append(ch)
                i += 1
            parts.append(''.join(cur).strip())
            return parts, ops_found

        def is_wrapped_in_parens(s: str) -> bool:
            """True if s is entirely wrapped by one outer (...) pair."""
            s = s.strip()
            if len(s) < 2 or not (s[0] == '(' and s[-1] == ')'):
                return False
            depth = 0
            for i, ch in enumerate(s):
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                if depth == 0 and i < len(s) - 1:
                    return False
            return depth == 0

        def find_top_level_divisions(s: str):
            """Return list of indices of '/' at top-level."""
            depth = 0
            pos = []
            for i, ch in enumerate(s):
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                elif ch == '/' and depth == 0:
                    pos.append(i)
            return pos

        def wrap_if_needed_for_mul(den_part: str, latex: str) -> str:
            """
            Если часть знаменателя содержит + или - на верхнем уровне, нужно обернуть в скобки.
            """
            target = den_part.strip()
            if is_wrapped_in_parens(target):
                return latex
            p, _ = split_top_level(target, {'+', '-'})
            if len(p) > 1:
                return r'\left(' + latex + r'\right)'
            return latex

        def convert_expr(e: str) -> str:
            e = e.strip()
            if not e:
                return e

            # Сохраняем пользовательские скобки
            if is_wrapped_in_parens(e):
                inner = e[1:-1].strip()
                return r'\left(' + convert_expr(inner) + r'\right)'

            # + и -
            parts, ops_found = split_top_level(e, {'+', '-'})
            if len(parts) > 1:
                res = convert_expr(parts[0])
                for op, part in zip(ops_found, parts[1:]):
                    res += f' {op} ' + convert_expr(part)
                return res

            # Деление: собираем все top-level '/'
            div_positions = find_top_level_divisions(e)
            if div_positions:
                # Разбиваем на части по '/'
                all_parts = []
                prev = 0
                for p in div_positions:
                    all_parts.append(e[prev:p].strip())
                    prev = p + 1
                all_parts.append(e[prev:].strip())

                # СЛУЧАЙ 1: A / (B / C)  ->  (A*C) / B   (убираем "трёхэтажность")
                if len(all_parts) == 2:
                    A = all_parts[0]
                    D = all_parts[1]
                    if is_wrapped_in_parens(D):
                        inner = D[1:-1].strip()
                        inner_divs = find_top_level_divisions(inner)
                        if inner_divs:
                            idx = inner_divs[0]
                            B = inner[:idx].strip()
                            C = inner[idx + 1:].strip()
                            new_num = convert_expr(A) + r' \cdot ' + convert_expr(C)
                            new_den = convert_expr(B)
                            return r'\frac{' + new_num + '}{' + new_den + '}'

                    return r'\frac{' + convert_expr(A) + '}{' + convert_expr(D) + '}'

                # СЛУЧАЙ 2: A / b / c / d  ->  A / (b*c*d)
                A = all_parts[0]
                den_parts = all_parts[1:]

                den_latex_parts = []
                for p in den_parts:
                    pl = convert_expr(p)
                    pl = wrap_if_needed_for_mul(p, pl)
                    den_latex_parts.append(pl)

                den_latex = r' \cdot '.join(den_latex_parts)
                return r'\frac{' + convert_expr(A) + '}{' + den_latex + '}'

            # Умножение
            parts, _ = split_top_level(e, {'*'})
            if len(parts) > 1:
                return r' \cdot '.join(convert_expr(p) for p in parts)

            # Степень ** или ^
            depth = 0
            i = 0
            while i < len(e):
                ch = e[i]
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                elif depth == 0:
                    if e[i:i+2] == '**':
                        base = e[:i].strip()
                        exp = e[i+2:].strip()
                        return convert_expr(base) + '^{' + convert_expr(exp) + '}'
                    if ch == '^':
                        base = e[:i].strip()
                        exp = e[i+1:].strip()
                        return convert_expr(base) + '^{' + convert_expr(exp) + '}'
                i += 1

            # Функции
            func_map = {
                'sqrt': r'\sqrt',
                'sin': r'\sin', 'cos': r'\cos', 'tan': r'\tan',
                'tg': r'\tan', 'ctg': r'\cot',
                'asin': r'\arcsin', 'acos': r'\arccos', 'atan': r'\arctan',
                'log': r'\log', 'ln': r'\ln', 'log10': r'\log_{10}', 'log2': r'\log_{2}',
                'exp': r'\exp',
            }
            for fname, lf in func_map.items():
                if e.startswith(fname + '(') and e.endswith(')'):
                    inner = e[len(fname) + 1:-1].strip()
                    depth = 0
                    ok = True
                    for j, ch in enumerate(e[len(fname):]):
                        if ch == '(':
                            depth += 1
                        elif ch == ')':
                            depth -= 1
                        if depth == 0 and j < len(e[len(fname):]) - 1:
                            ok = False
                            break
                    if ok:
                        if fname == 'sqrt':
                            return r'\sqrt{' + convert_expr(inner) + '}'
                        return lf + r'\left(' + convert_expr(inner) + r'\right)'

            if e.startswith('abs(') and e.endswith(')'):
                inner = e[4:-1].strip()
                return r'\left|' + convert_expr(inner) + r'\right|'

            # атом
            return symbol_to_latex(e)

        return convert_expr(expr)


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

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='calculation_sessions',
        verbose_name='Владелец'
    )
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


class Project(models.Model):
    """Проект (группа вариантов)"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='projects',
        verbose_name='Владелец'
    )
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
    
    formulas_snapshot = models.JSONField(
        'Снимок формул',
        null=True,
        blank=True,
        help_text='JSON с формулами на момент создания варианта'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_recalculated_at = models.DateTimeField(
        'Дата последнего пересчёта',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Вариант'
        verbose_name_plural = 'Варианты'
        unique_together = ['project', 'number']
        ordering = ['project', 'number']

    def __str__(self):
        return f"Вариант {self.number}" + (f" ({self.student_name})" if self.student_name else "")

class VariantValue(models.Model):
    """Значение переменной в варианте"""

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



class FormulaChart(models.Model):
    """Настройки графика для формулы"""

    CHART_TYPES = [
        ('line', 'Линейный'),
        ('scatter', 'Точечный'),
        ('bar', 'Столбчатый'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='charts',
        verbose_name='Владелец'
    )
    name = models.CharField('Название графика', max_length=200)
    formula = models.ForeignKey(
        Formula,
        on_delete=models.CASCADE,
        related_name='charts',
        verbose_name='Формула (Y)'
    )
    x_variable = models.CharField(
        'Переменная по оси X',
        max_length=50,
        help_text='Символ переменной для оси X'
    )
    x_min = models.FloatField('X минимум', default=0.0)
    x_max = models.FloatField('X максимум', default=0.0)
    invert_y = models.BooleanField('Инвертировать ось Y', default=False)
    x_steps = models.PositiveIntegerField('Количество точек', default=50)
    chart_type = models.CharField(
        'Тип графика',
        max_length=20,
        choices=CHART_TYPES,
        default='line'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'График'
        verbose_name_plural = 'Графики'

    def __str__(self):
        return f"{self.name}: {self.formula.symbol}({self.x_variable})"


class ChatMessage(models.Model):
    """Сообщение в чате с AI"""
    
    ROLE_CHOICES = [
        ('user', 'Пользователь'),
        ('assistant', 'Ассистент'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_messages',
        verbose_name='Пользователь'
    )
    role = models.CharField(
        'Роль',
        max_length=20,
        choices=ROLE_CHOICES
    )
    content = models.TextField('Содержимое')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Сообщение чата'
        verbose_name_plural = 'Сообщения чата'
        ordering = ['created_at']
    
    def __str__(self):
        return f"[{self.role}] {self.content[:50]}..."