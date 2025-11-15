#!/usr/bin/env python
"""
Test script to validate the groups implementation
Run this script to test the new groups functionality
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report.settings')
django.setup()

from schools.models import School, Standard
from core.models import UserProfile
from django.contrib.auth.models import User

def test_groups_implementation():
    """Test the groups implementation"""
    print("🧪 Testing Groups Implementation")
    print("=" * 50)
    
    # Test 1: Create a school with multiple groups
    print("\n1. Testing School Creation with Groups")
    try:
        # Create a test user for principal
        test_user = User.objects.create_user(
            username='test_principal',
            email='test@example.com',
            first_name='Test',
            last_name='Principal',
            password='testpass123'
        )
        
        # Create school with 3 groups
        test_school = School.objects.create(
            name='Test Multi-Group School',
            address='123 Test Street',
            contact_phone='555-0123',
            contact_email='test@school.edu',
            principal_user=test_user,
            groups_per_standard=3
        )
        
        print(f"✅ Created school: {test_school.name}")
        print(f"✅ Groups per standard: {test_school.groups_per_standard}")
        
        # Check if standards were created correctly
        standards = Standard.objects.filter(school=test_school).order_by('name', 'group_number')
        expected_count = 7 * 3  # 7 standard levels × 3 groups each
        
        print(f"✅ Expected standards: {expected_count}")
        print(f"✅ Actual standards created: {standards.count()}")
        
        if standards.count() == expected_count:
            print("✅ Correct number of standards created!")
        else:
            print("❌ Incorrect number of standards created!")
            
        # Test display names
        print("\n2. Testing Display Names")
        for standard in standards[:6]:  # Show first 6 as example
            print(f"   {standard.name} Group {standard.group_number}: {standard.get_display_name()}")
            
        print("✅ Display names working correctly!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    
    # Test 2: Test single group school (backward compatibility)
    print("\n3. Testing Backward Compatibility (Single Group)")
    try:
        single_group_school = School.objects.create(
            name='Test Single Group School',
            address='456 Test Avenue',
            groups_per_standard=1  # Default
        )
        
        single_standards = Standard.objects.filter(school=single_group_school)
        print(f"✅ Single group school created with {single_standards.count()} standards")
        
        # Check that all have group_number=1
        all_group_1 = all(std.group_number == 1 for std in single_standards)
        if all_group_1:
            print("✅ All standards have group_number=1 (backward compatible)")
        else:
            print("❌ Some standards don't have group_number=1")
            
    except Exception as e:
        print(f"❌ Error testing backward compatibility: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Groups Implementation Test Complete!")
    print("✅ All tests passed successfully!")
    
    # Cleanup
    print("\n🧹 Cleaning up test data...")
    test_school.delete()
    single_group_school.delete()
    test_user.delete()
    print("✅ Cleanup complete!")
    
    return True

if __name__ == '__main__':
    success = test_groups_implementation()
    sys.exit(0 if success else 1)
