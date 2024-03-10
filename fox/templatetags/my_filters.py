# my_filters.py
from django import template

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiplies the value by the argument"""
    try:
        return value * arg
    except (ValueError, TypeError):
        try:
            return int(value) * arg
        except (ValueError, TypeError):
            return ''
