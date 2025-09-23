#!/usr/bin/env python
"""
Test script for the enhanced vacation detection system.
"""
import os
import sys
import django
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report.settings.development')
django.setup()

from schools.models import School
from academics.models import SchoolYear, Term
from core.utils import get_current_year_and_term

def test_vacation_detection():
    """Test the enhanced vacation detection system."""
    print("🧪 Testing Enhanced Vacation Detection System")
    print("=" * 50)
    
    # Get or create a test school
    school, created = School.objects.get_or_create(
        name="Test School",
        defaults={
            'slug': 'test-school',
            'address': '123 Test St',
            'contact_phone': '555-0123',
            'contact_email': 'test@school.com'
        }
    )
    
    if created:
        print(f"✅ Created test school: {school.name}")
    else:
        print(f"✅ Using existing test school: {school.name}")
    
    # Create two consecutive school years for proper summer vacation testing
    current_year = 2024
    next_year = 2025

    # Create or get the current school year (2024-2025)
    school_year_2024, created_2024 = SchoolYear.objects.get_or_create(
        school=school,
        start_year=current_year,
        defaults={}
    )

    if created_2024:
        print(f"✅ Created school year: {school_year_2024}")

        # Create test terms for 2024-2025 academic year
        terms_data_2024 = [
            {
                'term_number': 1,
                'start_date': date(2024, 9, 1),
                'end_date': date(2024, 12, 15),
                'school_days': 70
            },
            {
                'term_number': 2,
                'start_date': date(2025, 1, 8),
                'end_date': date(2025, 4, 12),
                'school_days': 65
            },
            {
                'term_number': 3,
                'start_date': date(2025, 4, 22),
                'end_date': date(2025, 7, 5),
                'school_days': 55
            }
        ]

        for term_data in terms_data_2024:
            Term.objects.create(
                year=school_year_2024,
                **term_data
            )
        print("✅ Created terms for 2024-2025")
    else:
        print(f"✅ Using existing school year: {school_year_2024}")

    # Create or get the next school year (2025-2026)
    school_year_2025, created_2025 = SchoolYear.objects.get_or_create(
        school=school,
        start_year=next_year,
        defaults={}
    )

    if created_2025:
        print(f"✅ Created school year: {school_year_2025}")

        # Create test terms for 2025-2026 academic year
        terms_data_2025 = [
            {
                'term_number': 1,
                'start_date': date(2025, 9, 1),
                'end_date': date(2025, 12, 15),
                'school_days': 70
            },
            {
                'term_number': 2,
                'start_date': date(2026, 1, 8),
                'end_date': date(2026, 4, 12),
                'school_days': 65
            },
            {
                'term_number': 3,
                'start_date': date(2026, 4, 22),
                'end_date': date(2026, 7, 5),
                'school_days': 55
            }
        ]

        for term_data in terms_data_2025:
            Term.objects.create(
                year=school_year_2025,
                **term_data
            )
        print("✅ Created terms for 2025-2026")
    else:
        print(f"✅ Using existing school year: {school_year_2025}")
    
    # Test different dates and their vacation status
    test_dates = [
        # During Term 1 of 2024-2025
        (date(2024, 10, 15), "During Term 1 (2024-2025)", 1, None),

        # Christmas Vacation (between Term 1 and 2 of 2024-2025)
        (date(2024, 12, 20), "Christmas Vacation", None, 'christmas'),
        (date(2025, 1, 5), "Christmas Vacation", None, 'christmas'),

        # During Term 2 of 2024-2025
        (date(2025, 2, 15), "During Term 2 (2024-2025)", 2, None),

        # Easter Vacation (between Term 2 and 3 of 2024-2025)
        (date(2025, 4, 15), "Easter Vacation", None, 'easter'),
        (date(2025, 4, 20), "Easter Vacation", None, 'easter'),

        # During Term 3 of 2024-2025
        (date(2025, 5, 15), "During Term 3 (2024-2025)", 3, None),

        # Summer Vacation (after Term 3 ends, now in 2025-2026 academic year)
        # Current year should be 2025-2026, but before Term 1 starts
        (date(2025, 7, 15), "Summer Vacation (in 2025-2026)", None, 'summer'),
        (date(2025, 8, 15), "Summer Vacation (in 2025-2026)", None, 'summer'),

        # During Term 1 of 2025-2026 (after summer vacation ends)
        (date(2025, 10, 15), "During Term 1 (2025-2026)", 1, None),
    ]
    
    print("\n🔍 Testing Vacation Detection:")
    print("-" * 50)
    
    # Temporarily override timezone.now() for testing
    from unittest.mock import patch
    
    for test_date, description, expected_term, expected_vacation in test_dates:
        with patch('core.utils.timezone') as mock_timezone:
            mock_timezone.now.return_value.date.return_value = test_date
            
            year, term, vacation_status = get_current_year_and_term(school=school)
            
            # Format vacation status for display
            vacation_display = vacation_status if vacation_status else "None"
            term_display = term if term else "None"
            
            # Check if results match expectations
            term_match = term == expected_term
            vacation_match = vacation_status == expected_vacation
            
            status = "✅" if (term_match and vacation_match) else "❌"
            
            print(f"{status} {test_date} ({description}):")
            print(f"    Term: {term_display} (expected: {expected_term})")
            print(f"    Vacation: {vacation_display} (expected: {expected_vacation})")
            
            if not (term_match and vacation_match):
                print(f"    ⚠️  MISMATCH DETECTED!")
            print()
    
    print("🎯 Test Summary:")
    print("- Christmas Vacation: Between Term 1 and Term 2 (within same academic year)")
    print("- Easter Vacation: Between Term 2 and Term 3 (within same academic year)")
    print("- Summer Vacation: After Term 3 ends, system transitions to NEXT academic year")
    print("  * Current year becomes 2025-2026, but we're before Term 1 starts")
    print("  * This allows student advancement and administrative preparation")
    print("- Academic Year Transition: Happens immediately after Term 3 ends")
    print("\n✨ Enhanced vacation detection system test completed!")

if __name__ == '__main__':
    test_vacation_detection()
