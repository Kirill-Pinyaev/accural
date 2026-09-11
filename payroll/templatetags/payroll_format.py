from decimal import Decimal, InvalidOperation

from django import template


register = template.Library()


@register.filter
def spaced_number(value, digits=2):
    if value in (None, ""):
        return ""

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return value

    try:
        digits = int(digits)
    except (TypeError, ValueError):
        digits = 2

    formatted = f"{amount:,.{digits}f}"
    return formatted.replace(",", " ").replace(".", ",")
