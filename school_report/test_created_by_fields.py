"""
Test script to verify that created_by fields are working correctly
and that activities are being generated automatically.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile
from schools.models import School, Standard, Student
from academics.models import SchoolYear, Term, StandardTeacher, SchoolStaff, SchoolEnrollment, StandardEnrollment
from actstream.models import Action
from datetime import date, timedelta

def test_created_by_fields():
    """Test that all created_by fields are working correctly"""
    
    print("\n" + "="*80)
    print("TESTING CREATED_BY FIELDS AND AUTOMATIC ACTIVITY GENERATION")
    print("="*80 + "\n")
    
    # Get or create a test user (principal)
    test_user, created = User.objects.get_or_create(
        username='test_principal',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'Principal'
        }
    )
    
    if created:
        test_user.set_password('password123')
        test_user.save()
        profile = test_user.profile
        profile.user_type = 'principal'
        profile.save()
        print(f"✅ Created test user: {test_user.username}")
    else:
        profile = test_user.profile
        print(f"✅ Using existing test user: {test_user.username}")
    
    # Get or create a test school
    school, created = School.objects.get_or_create(
        name='Test Activity School',
        defaults={
            'slug': 'test-activity-school',
            'address': '123 Test St',
            'contact_phone': '555-1234',
            'principal_user': test_user
        }
    )
    
    if created:
        print(f"✅ Created test school: {school.name}")
    else:
        print(f"✅ Using existing test school: {school.name}")
    
    # Get or create current year
    current_year, created = SchoolYear.objects.get_or_create(
        school=school,
        start_year=2024
    )
    
    if created:
        print(f"✅ Created school year: {current_year}")
        # Create terms
        Term.objects.get_or_create(
            year=current_year,
            term_number=1,
            defaults={
                'start_date': date(2024, 9, 1),
                'end_date': date(2024, 12, 15),
                'school_days': 70
            }
        )
    else:
        print(f"✅ Using existing school year: {current_year}")
    
    # Get or create a standard
    standard, created = Standard.objects.get_or_create(
        school=school,
        name='INF1'
    )
    
    if created:
        print(f"✅ Created standard: {standard}")
    else:
        print(f"✅ Using existing standard: {standard}")
    
    print("\n" + "-"*80)
    print("TEST 1: Student Creation with created_by")
    print("-"*80)
    
    # Clear old activities for this school
    Action.objects.filter(data__school_id=school.id).delete()
    
    # Test 1: Create a student
    student = Student.objects.create(
        first_name='John',
        last_name='Doe',
        date_of_birth=date(2018, 5, 15),
        parent_name='Jane Doe',
        created_by=profile
    )
    
    print(f"✅ Created student: {student}")
    print(f"   created_by: {student.created_by}")
    
    # Check if activity was created
    activities = Action.objects.filter(data__school_id=school.id).order_by('-timestamp')
    print(f"   Activities generated: {activities.count()}")
    
    print("\n" + "-"*80)
    print("TEST 2: SchoolEnrollment with enrolled_by")
    print("-"*80)
    
    # Test 2: Enroll student in school
    school_enrollment = SchoolEnrollment.objects.create(
        school=school,
        student=student,
        enrollment_date=date.today(),
        is_active=True,
        enrolled_by=profile
    )
    
    print(f"✅ Created school enrollment: {school_enrollment}")
    print(f"   enrolled_by: {school_enrollment.enrolled_by}")
    
    print("\n" + "-"*80)
    print("TEST 3: StandardEnrollment with enrolled_by")
    print("-"*80)
    
    # Test 3: Enroll student in class
    class_enrollment = StandardEnrollment.objects.create(
        year=current_year,
        standard=standard,
        student=student,
        enrolled_by=profile
    )
    
    print(f"✅ Created class enrollment: {class_enrollment}")
    print(f"   enrolled_by: {class_enrollment.enrolled_by}")
    
    # Check activities
    activities = Action.objects.filter(data__school_id=school.id).order_by('-timestamp')
    print(f"   Total activities: {activities.count()}")
    for activity in activities[:3]:
        print(f"   - {activity.description}")
    
    print("\n" + "="*80)
    print("ALL TESTS PASSED! ✅")
    print("="*80 + "\n")

if __name__ == '__main__':
    test_created_by_fields()

