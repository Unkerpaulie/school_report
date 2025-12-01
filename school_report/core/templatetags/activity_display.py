"""
Template tags for displaying activity streams in templates.
"""

from django import template
from actstream.models import Action
from django.utils.timesince import timesince
from django.utils.html import format_html

register = template.Library()


@register.inclusion_tag('core/activity_stream_widget.html', takes_context=True)
def show_recent_activities(context, limit=10):
    """
    Display recent activities for the current school.

    Usage in template:
        {% load activity_display %}
        {% show_recent_activities 10 %}
    """
    request = context.get('request')

    # Get school from session
    school_id = request.session.get('user_school_id') if request else None

    # Filter activities by school
    if school_id:
        # Filter by school_id stored in the action's data field
        activities = Action.objects.filter(
            data__school_id=school_id
        ).order_by('-timestamp')[:limit]
    else:
        # If no school context, show no activities
        activities = Action.objects.none()

    return {
        'activities': activities,
        'request': request,
    }


@register.filter
def activity_icon(verb):
    """
    Return an appropriate icon class for the activity verb.
    
    Usage: {{ action.verb|activity_icon }}
    """
    icon_map = {
        'created': 'bi-plus-circle text-success',
        'updated': 'bi-pencil text-primary',
        'deleted': 'bi-trash text-danger',
        'enrolled': 'bi-person-plus text-info',
        'assigned': 'bi-person-check text-primary',
        'finalized reports': 'bi-check-circle text-success',
        'finalized term': 'bi-calendar-check text-success',
    }
    return icon_map.get(verb, 'bi-circle text-secondary')


@register.filter
def time_ago(timestamp):
    """
    Return a human-readable time ago string.
    
    Usage: {{ action.timestamp|time_ago }}
    """
    return timesince(timestamp) + " ago"

