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
        if '.' in formatted:
            formatted = formatted.rstrip('0').rstrip('.')
        return formatted
    except (ValueError, TypeError):
        return value


@register.filter
def add(value, arg):
    """Сложение для шаблонов"""
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def rjust(value, length):
    """Повторяет символ указанное количество раз"""
    try:
        return value * int(length)
    except (ValueError, TypeError):
        return value
@register.filter
def dot_decimal(value):
    """Преобразует число в строку с точкой в качестве разделителя"""
    if value is None:
        return '0'
    try:
        # Преобразуем в float и форматируем с точкой
        return str(float(value)).replace(',', '.')
    except (ValueError, TypeError):
        return '0'