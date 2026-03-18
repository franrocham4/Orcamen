from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get a value from a dict by key in templates."""
    if isinstance(dictionary, dict):
        return dictionary.get(str(key), '')
    return ''


@register.filter
def split(value, sep):
    """Split a string by separator."""
    return value.split(sep)
