from __future__ import division

from django.template import Library


register = Library()


@register.filter
def division(value, arg):
    """Divide the arg by the value."""
    try:
        return value / arg
    except (ValueError, TypeError):
        try:
            return value / arg
        except Exception:
            return ''
division.is_safe = False
