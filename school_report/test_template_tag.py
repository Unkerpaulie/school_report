"""
Test the activity template tag
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report.settings')
django.setup()

from django.template import Template, Context
from django.test import RequestFactory
from actstream.models import Action

# Create a fake request
factory = RequestFactory()
request = factory.get('/')

# Get activities
activities = Action.objects.all().order_by('-timestamp')[:10]

print(f"Found {activities.count()} activities")

# Test the template tag
template_string = """
{% load activity_display %}
{% show_recent_activities 10 %}
"""

template = Template(template_string)
context = Context({'request': request})

try:
    output = template.render(context)
    print("\n=== Template rendered successfully ===")
    print(output[:500])  # Print first 500 chars
except Exception as e:
    print(f"\n=== Error rendering template ===")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

