"""
Activity Stream Utilities
Helper functions for creating human-readable activity descriptions.

This module provides utilities to generate user-facing activity feed entries
that are displayed on the dashboard for principals and administrators.
"""

from actstream import action
from django.contrib.contenttypes.models import ContentType


def get_actor_display_name(user_profile):
    """
    Get a formatted display name for an actor (user).
    Returns: "Mr. Smith" or "Mrs. Johnson"
    """
    if user_profile and hasattr(user_profile, 'get_full_name_with_title'):
        return user_profile.get_full_name_with_title()
    elif user_profile and hasattr(user_profile, 'get_full_name'):
        return user_profile.get_full_name()
    return "Unknown User"


def create_test_activity(actor, test, verb='created'):
    """
    Create activity for test creation/update/deletion.
    
    Args:
        actor: UserProfile who performed the action
        test: Test object
        verb: 'created', 'updated', or 'deleted'
    
    Example output: "Mr. Henry created Midterm Test for Standard 3A"
    """
    actor_name = get_actor_display_name(actor)
    test_type = test.get_test_type_display() if hasattr(test, 'get_test_type_display') else 'Test'
    standard_name = test.standard.get_display_name() if hasattr(test.standard, 'get_display_name') else str(test.standard)
    
    description = f"{verb.capitalize()} {test_type} for {standard_name}"
    
    action.send(
        actor.user if hasattr(actor, 'user') else actor,
        verb=verb,
        action_object=test,
        target=test.standard,
        description=description
    )


def create_report_finalization_activity(actor, term, standard, student_count):
    """
    Create activity for report finalization.
    
    Example output: "Principal Smith finalized 25 reports for Standard 2B, Term 1"
    """
    actor_name = get_actor_display_name(actor)
    standard_name = standard.get_display_name() if hasattr(standard, 'get_display_name') else str(standard)
    term_display = f"Term {term.term_number}" if hasattr(term, 'term_number') else str(term)
    
    description = f"Finalized {student_count} reports for {standard_name}, {term_display}"
    
    action.send(
        actor.user if hasattr(actor, 'user') else actor,
        verb='finalized reports',
        action_object=term,
        target=standard,
        description=description
    )


def create_student_enrollment_activity(actor, student, standard, verb='enrolled'):
    """
    Create activity for student enrollment/transfer.
    
    Example output: "Mrs. Johnson enrolled John Doe in Standard 1A"
    """
    actor_name = get_actor_display_name(actor)
    student_name = student.get_full_name() if hasattr(student, 'get_full_name') else str(student)
    standard_name = standard.get_display_name() if hasattr(standard, 'get_display_name') else str(standard)
    
    description = f"{verb.capitalize()} {student_name} in {standard_name}"
    
    action.send(
        actor.user if hasattr(actor, 'user') else actor,
        verb=verb,
        action_object=student,
        target=standard,
        description=description
    )


def create_teacher_assignment_activity(actor, teacher, standard, verb='assigned'):
    """
    Create activity for teacher assignment to class.
    
    Example output: "Principal Smith assigned Mr. Henry to Standard 3A"
    """
    actor_name = get_actor_display_name(actor)
    teacher_name = get_actor_display_name(teacher)
    standard_name = standard.get_display_name() if hasattr(standard, 'get_display_name') else str(standard)
    
    description = f"{verb.capitalize()} {teacher_name} to {standard_name}"
    
    action.send(
        actor.user if hasattr(actor, 'user') else actor,
        verb=verb,
        action_object=teacher,
        target=standard,
        description=description
    )


def create_subject_activity(actor, subject, standard, verb='created'):
    """
    Create activity for subject creation/update.
    
    Example output: "Mr. Henry created Mathematics subject for Standard 3A"
    """
    actor_name = get_actor_display_name(actor)
    subject_name = subject.subject_name if hasattr(subject, 'subject_name') else str(subject)
    standard_name = standard.get_display_name() if hasattr(standard, 'get_display_name') else str(standard)
    
    description = f"{verb.capitalize()} {subject_name} subject for {standard_name}"
    
    action.send(
        actor.user if hasattr(actor, 'user') else actor,
        verb=verb,
        action_object=subject,
        target=standard,
        description=description
    )


def create_term_finalization_activity(actor, term):
    """
    Create activity for term finalization.
    
    Example output: "Principal Smith finalized Term 1 for 2024-2025"
    """
    actor_name = get_actor_display_name(actor)
    term_display = f"Term {term.term_number}" if hasattr(term, 'term_number') else str(term)
    year_display = str(term.year) if hasattr(term, 'year') else ""
    
    description = f"Finalized {term_display} for {year_display}"
    
    action.send(
        actor.user if hasattr(actor, 'user') else actor,
        verb='finalized term',
        action_object=term,
        description=description
    )

