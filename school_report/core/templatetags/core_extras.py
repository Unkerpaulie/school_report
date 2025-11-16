from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """
    Template filter to lookup a value in a dictionary by key
    Usage: {{ dict|lookup:key }}
    """
    if dictionary and hasattr(dictionary, 'get'):
        return dictionary.get(int(key) if str(key).isdigit() else key)
    return None

@register.filter
def add(value, arg):
    """
    Template filter to add a number to a value
    Usage: {{ value|add:5 }}
    """
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return value
