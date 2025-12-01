"""
Test the Action model structure to understand how to filter by school
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report.settings')
django.setup()

from actstream.models import Action
from actstream import action
from core.models import UserProfile
from schools.models import School, Standard

print("=== Testing Action Model Structure ===\n")

# Get test data
school = School.objects.first()
teacher = UserProfile.objects.filter(user_type='teacher').first()
standard = Standard.objects.filter(school=school).first()

print(f"School: {school.name} (ID: {school.id})")
print(f"Teacher: {teacher.get_full_name()}")
print(f"Standard: {standard}\n")

# Create a test action with school_id
print("Creating test action with school_id...")
action.send(
    teacher.user,
    verb='test',
    description='Test action with school_id',
    school_id=school.id
)

# Get the latest action
latest_action = Action.objects.latest('timestamp')

print(f"\n✅ Latest Action Created:")
print(f"   Actor: {latest_action.actor}")
print(f"   Verb: {latest_action.verb}")
print(f"   Description: {latest_action.description}")
print(f"   Data field: {latest_action.data}")
print(f"   Data type: {type(latest_action.data)}")

# Try to filter by school_id
print(f"\n🔍 Testing Filters:")

# Method 1: Filter by data__school_id
try:
    filtered_1 = Action.objects.filter(data__school_id=school.id)
    print(f"   Method 1 (data__school_id={school.id}): Found {filtered_1.count()} actions")
except Exception as e:
    print(f"   Method 1 failed: {e}")

# Method 2: Filter by data__contains
try:
    filtered_2 = Action.objects.filter(data__contains={'school_id': school.id})
    print(f"   Method 2 (data__contains): Found {filtered_2.count()} actions")
except Exception as e:
    print(f"   Method 2 failed: {e}")

# Show all actions with their data
print(f"\n📋 All Actions:")
for act in Action.objects.all().order_by('-timestamp')[:5]:
    print(f"   - {act.verb}: data={act.data}")

# Clean up
latest_action.delete()
print(f"\n🧹 Cleaned up test action")

