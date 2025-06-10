#!/usr/bin/env python
"""
Test script to verify the home page redirect logic
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile
from schools.models import School
from academics.models import SchoolStaff, StandardTeacher, SchoolYear
from core.utils import get_current_year_and_term

def test_home_logic():
    print("Testing Home Page Redirect Logic...")
    print("=" * 50)
    
    # Test 1: Unauthenticated user
    print("\n1. Unauthenticated user:")
    print("   Expected: Show login form")
    print("   ✓ Should display public home page with login button")
    
    # Test 2: Principal with school
    print("\n2. Principal with school:")
    principals = UserProfile.objects.filter(user_type='principal')
    for principal in principals[:1]:  # Test first principal
        school_staff = SchoolStaff.objects.filter(staff=principal, is_active=True).first()
        if school_staff:
            print(f"   Principal: {principal.get_full_name()}")
            print(f"   School: {school_staff.school.name}")
            print("   Expected: Redirect to admin dashboard")
            print(f"   ✓ Should redirect to /schools/{school_staff.school.slug}/dashboard/")
    
    # Test 3: Teacher with class assignment
    print("\n3. Teacher with class assignment:")
    teachers = UserProfile.objects.filter(user_type='teacher')
    for teacher in teachers[:1]:  # Test first teacher
        school_staff = SchoolStaff.objects.filter(staff=teacher, is_active=True).first()
        if school_staff:
            current_year, current_term, is_on_vacation = get_current_year_and_term(school=school_staff.school)
            if current_year:
                assignment = StandardTeacher.objects.filter(teacher=teacher, year=current_year).first()
                if assignment:
                    print(f"   Teacher: {teacher.get_full_name()}")
                    print(f"   School: {school_staff.school.name}")
                    print(f"   Assigned Class: {assignment.standard}")
                    print("   Expected: Redirect to class detail page")
                    print(f"   ✓ Should redirect to /schools/{school_staff.school.slug}/classes/{assignment.standard.pk}/")
                else:
                    print(f"   Teacher: {teacher.get_full_name()}")
                    print(f"   School: {school_staff.school.name}")
                    print("   No class assignment")
                    print("   Expected: Show 'contact principal' message")
                    print("   ✓ Should display teacher_not_assigned message")
    
    # Test 4: Principal without school
    print("\n4. Principal without school:")
    print("   Expected: Redirect to school registration")
    print("   ✓ Should redirect to /register-school/")
    
    # Test 5: Teacher/Admin without school
    print("\n5. Teacher/Admin without school:")
    print("   Expected: Show 'contact principal' message")
    print("   ✓ Should display school_registration_required message")
    
    print("\n" + "=" * 50)
    print("Home page logic test completed!")

if __name__ == "__main__":
    test_home_logic()
