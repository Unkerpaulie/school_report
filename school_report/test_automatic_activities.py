"""
Test automatic activity generation via signals
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile
from schools.models import School, Standard, Student
from academics.models import SchoolYear, Term, StandardEnrollment, StandardSubject
from reports.models import Test
from actstream.models import Action

print("=" * 80)
print("TESTING AUTOMATIC ACTIVITY GENERATION")
print("=" * 80)

# Get test data
school = School.objects.first()
teacher = UserProfile.objects.filter(user_type='teacher').first()
standard = Standard.objects.filter(school=school).first()
year = SchoolYear.objects.filter(school=school).first()
term = Term.objects.filter(year=year).first()

print(f"\n📋 Test Data:")
print(f"   School: {school.name} (ID: {school.id})")
print(f"   Teacher: {teacher.get_full_name()}")
print(f"   Standard: {standard}")
print(f"   Year: {year}")
print(f"   Term: {term}")

# Count activities before
activity_count_before = Action.objects.count()
print(f"\n📊 Activities before: {activity_count_before}")

# Test 1: Create a test (should trigger signal)
print(f"\n\n{'='*80}")
print("TEST 1: Create Test (should auto-generate activity)")
print("="*80)

test = Test.objects.create(
    test_type="quiz",
    term=term,
    standard=standard,
    created_by=teacher,
    test_date="2025-12-15",
    description="Automatic Activity Test"
)
print(f"✅ Created test: {test}")

# Check if activity was created
activity_count_after = Action.objects.count()
print(f"📊 Activities after: {activity_count_after}")
print(f"📊 New activities: {activity_count_after - activity_count_before}")

if activity_count_after > activity_count_before:
    latest_activity = Action.objects.latest('timestamp')
    print(f"\n✅ Latest Activity:")
    print(f"   Actor: {latest_activity.actor}")
    print(f"   Verb: {latest_activity.verb}")
    print(f"   Description: {latest_activity.description}")
    print(f"   Data: {latest_activity.data}")
    print(f"   School ID in data: {latest_activity.data.get('school_id') if latest_activity.data else 'None'}")
else:
    print(f"\n❌ NO ACTIVITY WAS CREATED!")

# Test 2: Create a subject (should trigger signal)
print(f"\n\n{'='*80}")
print("TEST 2: Create Subject (should auto-generate activity)")
print("="*80)

activity_count_before = Action.objects.count()

subject = StandardSubject.objects.create(
    year=year,
    standard=standard,
    subject_name="Automatic Activity Test Subject",
    created_by=teacher
)
print(f"✅ Created subject: {subject}")

activity_count_after = Action.objects.count()
print(f"📊 Activities: {activity_count_before} → {activity_count_after} (+{activity_count_after - activity_count_before})")

if activity_count_after > activity_count_before:
    latest_activity = Action.objects.latest('timestamp')
    print(f"\n✅ Latest Activity:")
    print(f"   Actor: {latest_activity.actor}")
    print(f"   Verb: {latest_activity.verb}")
    print(f"   Description: {latest_activity.description}")
    print(f"   Data: {latest_activity.data}")
else:
    print(f"\n❌ NO ACTIVITY WAS CREATED!")

# Test 3: Filter activities by school
print(f"\n\n{'='*80}")
print("TEST 3: Filter Activities by School")
print("="*80)

all_activities = Action.objects.all()
school_activities = Action.objects.filter(data__school_id=school.id)

print(f"📊 Total activities: {all_activities.count()}")
print(f"📊 Activities for {school.name}: {school_activities.count()}")

print(f"\n📋 Recent activities for {school.name}:")
for i, activity in enumerate(school_activities.order_by('-timestamp')[:5], 1):
    print(f"\n{i}. {activity.actor} {activity.verb}")
    if activity.description:
        print(f"   Description: {activity.description}")
    print(f"   Timestamp: {activity.timestamp}")

# Clean up
print(f"\n\n{'='*80}")
print("CLEANUP")
print("="*80)
subject.delete()
test.delete()
print(f"✅ Cleaned up test data")

print(f"\n\n{'='*80}")
print("✅ TESTING COMPLETE!")
print("="*80)

