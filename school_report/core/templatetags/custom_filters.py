from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using a key.
    Usage: {{ dictionary|get_item:key }}
    
    This filter is used throughout the application to access dictionary values
    by key in templates.
    """
    if dictionary is None:
        return None
    return dictionary.get(key)
