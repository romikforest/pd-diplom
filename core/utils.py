import collections
from decimal import Decimal
# from django.urls import reverse
# from django.utils.translation import gettext_lazy as t


def is_dict(value):
    """
    Проверка, что объект value имеет поведение словаря
    """
    return isinstance(value, collections.Mapping)

def is_list(value):
    """
    Проверка, что объект value является списком
    """
    return type(value) == list
    # return isinstance(value, collections.Iterable)

# Конверторы. Возвращают None при ошибке:

def to_float(value):
    """
    Преобразование значения в число с плавающей точкой.
    При неудаче возвращается None
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def to_int(value):
    """
    Преобразование значения в целое со знаком.
    При неудаче возвращается None
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def to_positive_int(value):
    """
    Преобразование значения в неотрицательное целое.
    При неудаче возвращается None
    """
    try:
        value = int(value)
        return value if value >= 0 else None
    except (ValueError, TypeError):
        return None

def to_decimal(value):
    """
    Преобразование значения в большое число с фиксированной дробной частью.
    При неудаче возвращается None
    """
    value = to_float(value)
    return None if value is None else Decimal.from_float(value)

def to_positive_decimal(value):
    """
    Преобразование значения в неотрицательное большое число с фиксированной дробной частью.
    При неудаче возвращается None
    """
    value = to_float(value)
    return None if value is None or value < 0 else Decimal.from_float(value)



