"""
Check if activities were created successfully
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report.settings')
django.setup()

from actstream.models import Action

print("=== Checking Activities ===\n")

activities = Action.objects.all().order_by('-timestamp')

if activities.exists():
    print(f"Found {activities.count()} activities:\n")
    for activity in activities[:10]:
        print(f"- {activity.actor} {activity.verb} {activity.action_object}")
        if activity.description:
            print(f"  Description: {activity.description}")
        print(f"  Timestamp: {activity.timestamp}")
        print()
else:
    print("No activities found.")

