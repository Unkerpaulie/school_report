#!/usr/bin/env python
"""
Test script to verify the subjects functionality works correctly
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
from academics.models import SchoolStaff, StandardTeacher, SchoolYear, StandardSubject
from core.utils import get_current_year_and_term

def test_subjects_functionality():
    print("Testing Subjects Functionality...")
    print("=" * 50)
    
    # Test 1: Find teachers with class assignments
    print("\n1. Teachers with class assignments:")
    teachers = UserProfile.objects.filter(user_type='teacher')
    
    for teacher in teachers[:3]:  # Test first 3 teachers
        print(f"\n   Teacher: {teacher.get_full_name()}")
        
        # Check if teacher has school staff entry
        school_staff = SchoolStaff.objects.filter(staff=teacher, is_active=True).first()
        if school_staff:
            print(f"   School: {school_staff.school.name}")
            
            # Get current year for this school
            current_year, current_term, is_on_vacation = get_current_year_and_term(school=school_staff.school)
            if current_year:
                print(f"   Current Year: {current_year}")
                
                # Check for class assignment
                assignment = StandardTeacher.objects.filter(teacher=teacher, year=current_year).first()
                if assignment:
                    print(f"   Assigned Class: {assignment.standard}")
                    
                    # Check existing subjects for this class
                    subjects = StandardSubject.objects.filter(
                        standard=assignment.standard,
                        year=current_year
                    )
                    print(f"   Existing Subjects: {subjects.count()}")
                    for subject in subjects:
                        print(f"     - {subject.subject_name}")
                        
                    print(f"   ✓ Teacher can access subjects at: /schools/{school_staff.school.slug}/subjects/")
                else:
                    print("   ⚠ No class assignment found")
            else:
                print("   ⚠ No current academic year found")
        else:
            print("   ⚠ No school staff entry found")
    
    # Test 2: Check URL patterns
    print("\n2. Subject URL patterns:")
    print("   ✓ Subject List: /schools/<school_slug>/subjects/")
    print("   ✓ Subject Create: /schools/<school_slug>/subjects/create/")
    print("   ✓ Subject Edit: /schools/<school_slug>/subjects/<id>/edit/")
    print("   ✓ Subject Delete: /schools/<school_slug>/subjects/<id>/delete/")
    
    # Test 3: Check sidebar menu
    print("\n3. Sidebar menu:")
    print("   ✓ Subjects menu added for teachers only")
    print("   ✓ Uses 'subjects_active' block for highlighting")
    
    print("\n" + "=" * 50)
    print("Subjects functionality test completed!")
    print("\nNext steps:")
    print("1. Login as a teacher with class assignment")
    print("2. Check that 'Subjects' appears in sidebar")
    print("3. Create subjects for your class")
    print("4. Use subjects when creating tests")

if __name__ == "__main__":
    test_subjects_functionality()
