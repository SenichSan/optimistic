from django import template
import html

register = template.Library()


@register.filter(name="unescape_html")
def unescape_html(value):
    """
    Convert HTML entities like &mdash; into their Unicode characters.
    Safe to use after striptags. If value is not a string, return as-is.
    """
    if value is None:
        return value
    try:
        return html.unescape(str(value))
    except Exception:
        return value


@register.filter(name="dotdec")
def dotdec(value):
    """
    Force decimal separator to dot. Useful for JSON-LD price fields.
    Works with numbers and strings; returns original on error.
    """
    try:
        return str(value).replace(',', '.')
    except Exception:
        return value
