"""
Test script to generate sample activity data
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile
from schools.models import School, Standard, Student
from academics.models import SchoolYear, Term, StandardEnrollment
from reports.models import Test
from core.activity_utils import (
    create_test_activity,
    create_student_enrollment_activity,
    create_teacher_assignment_activity
)

# Get the first school
school = School.objects.first()
if not school:
    print("No school found. Please create a school first.")
    exit()

print(f"Using school: {school.name}")

# Get the first teacher
teacher = UserProfile.objects.filter(user_type='teacher').first()
if not teacher:
    print("No teacher found. Please create a teacher first.")
    exit()

print(f"Using teacher: {teacher.get_full_name()}")

# Get the first standard
standard = Standard.objects.filter(school=school).first()
if not standard:
    print("No standard found. Please create a standard first.")
    exit()

print(f"Using standard: {standard}")

# Get current year
year = SchoolYear.objects.filter(school=school).first()
if not year:
    print("No school year found. Please create a school year first.")
    exit()

print(f"Using year: {year}")

# Get first term
term = Term.objects.filter(year=year).first()
if not term:
    print("No term found. Please create a term first.")
    exit()

print(f"Using term: {term}")

# Create a test activity
print("\n--- Creating test activity ---")
test = Test.objects.filter(standard=standard, term=term).first()
if test:
    create_test_activity(teacher, test, verb='created')
    print(f"✅ Created activity for test: {test}")
else:
    print("No test found to create activity for")

# Create a student enrollment activity
print("\n--- Creating student enrollment activity ---")
student = Student.objects.first()
if student:
    create_student_enrollment_activity(teacher, student, standard, verb='enrolled')
    print(f"✅ Created activity for student enrollment: {student.get_full_name()}")
else:
    print("No student found to create activity for")

# Create a teacher assignment activity
print("\n--- Creating teacher assignment activity ---")
principal = UserProfile.objects.filter(user_type='principal').first()
if principal:
    create_teacher_assignment_activity(principal, teacher, standard, verb='assigned')
    print(f"✅ Created activity for teacher assignment: {teacher.get_full_name()}")
else:
    print("No principal found to create activity for")

print("\n✅ Activity generation complete!")
print("Check the dashboard to see the recent activities.")

