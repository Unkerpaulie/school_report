"""
Signals for automatic activity stream generation.

This module listens to model changes and automatically creates
user-friendly activity stream entries for important actions.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from actstream import action
from django.contrib.contenttypes.models import ContentType


def get_actor_from_instance(instance):
    """
    Try to get the actor (user) from the instance.
    Returns the UserProfile if found, otherwise None.
    """
    # Check if instance has created_by or updated_by
    if hasattr(instance, 'created_by') and instance.created_by:
        return instance.created_by

    # Check for model-specific created_by field names
    if hasattr(instance, 'enrolled_by') and instance.enrolled_by:
        return instance.enrolled_by

    if hasattr(instance, 'assigned_by') and instance.assigned_by:
        return instance.assigned_by

    if hasattr(instance, 'added_by') and instance.added_by:
        return instance.added_by

    # Check if instance has a user attribute
    if hasattr(instance, 'user') and instance.user:
        if hasattr(instance.user, 'profile'):
            return instance.user.profile
        return instance.user

    # Check if instance has a teacher attribute
    if hasattr(instance, 'teacher') and instance.teacher:
        return instance.teacher

    # Check if instance has a student attribute with user
    if hasattr(instance, 'student') and instance.student:
        if hasattr(instance.student, 'user') and instance.student.user:
            if hasattr(instance.student.user, 'profile'):
                return instance.student.user.profile

    return None


def get_school_from_instance(instance):
    """
    Try to get the school from the instance for filtering purposes.
    Returns the School object if found, otherwise None.
    """
    # Direct school attribute
    if hasattr(instance, 'school') and instance.school:
        return instance.school
    
    # Through standard
    if hasattr(instance, 'standard') and instance.standard:
        if hasattr(instance.standard, 'school'):
            return instance.standard.school
    
    # Through year
    if hasattr(instance, 'year') and instance.year:
        if hasattr(instance.year, 'school'):
            return instance.year.school
    
    # Through term
    if hasattr(instance, 'term') and instance.term:
        if hasattr(instance.term, 'year') and instance.term.year:
            if hasattr(instance.term.year, 'school'):
                return instance.term.year.school
    
    return None


# Test Model Signals
@receiver(post_save, sender='reports.Test')
def create_test_activity(sender, instance, created, **kwargs):
    """Create activity when a test is created or updated"""
    if created:
        actor = get_actor_from_instance(instance)
        school = get_school_from_instance(instance)
        
        if actor:
            action.send(
                actor,
                verb='created',
                action_object=instance,
                target=instance.standard,
                description=f"Created {instance.get_test_type_display()} for {instance.standard.get_display_name()}",
                school_id=school.id if school else None
            )


@receiver(post_delete, sender='reports.Test')
def delete_test_activity(sender, instance, **kwargs):
    """Create activity when a test is deleted"""
    actor = get_actor_from_instance(instance)
    school = get_school_from_instance(instance)
    
    if actor:
        action.send(
            actor,
            verb='deleted',
            description=f"Deleted {instance.get_test_type_display()} for {instance.standard.get_display_name()}",
            school_id=school.id if school else None
        )


# Student Enrollment Signals
@receiver(post_save, sender='academics.StandardEnrollment')
def create_enrollment_activity(sender, instance, created, **kwargs):
    """Create activity when a student is enrolled"""
    if created:
        actor = get_actor_from_instance(instance)
        school = get_school_from_instance(instance)
        
        if actor:
            action.send(
                actor,
                verb='enrolled',
                action_object=instance.student,
                target=instance.standard,
                description=f"Enrolled {instance.student.get_full_name()} in {instance.standard.get_display_name()}",
                school_id=school.id if school else None
            )


# Teacher Assignment Signals
@receiver(post_save, sender='academics.StandardTeacher')
def create_teacher_assignment_activity(sender, instance, created, **kwargs):
    """Create activity when a teacher is assigned to a class"""
    if created:
        actor = get_actor_from_instance(instance)
        school = get_school_from_instance(instance)

        if actor:
            action.send(
                actor,
                verb='assigned',
                action_object=instance.teacher,
                target=instance.standard,
                description=f"Assigned {instance.teacher.get_full_name()} to {instance.standard.get_display_name()}",
                school_id=school.id if school else None
            )


# Subject Signals
@receiver(post_save, sender='academics.StandardSubject')
def create_subject_activity(sender, instance, created, **kwargs):
    """Create activity when a subject is created"""
    if created:
        actor = get_actor_from_instance(instance)
        school = get_school_from_instance(instance)

        if actor:
            action.send(
                actor,
                verb='created',
                action_object=instance,
                target=instance.standard,
                description=f"Created {instance.subject_name} subject for {instance.standard.get_display_name()}",
                school_id=school.id if school else None
            )


# Report Finalization Signals
@receiver(post_save, sender='reports.StudentTermReview')
def create_report_finalization_activity(sender, instance, created, update_fields, **kwargs):
    """Create activity when reports are finalized"""
    # Only create activity when is_finalized changes to True
    if not created and update_fields and 'is_finalized' in update_fields:
        if instance.is_finalized and instance.finalized_by:
            school = get_school_from_instance(instance)

            # Count how many reports were finalized for this term/class
            from reports.models import StudentTermReview
            finalized_count = StudentTermReview.objects.filter(
                term=instance.term,
                student__current_standard=instance.student.current_standard,
                is_finalized=True
            ).count()

            action.send(
                instance.finalized_by,
                verb='finalized reports',
                target=instance.student.current_standard,
                description=f"Finalized {finalized_count} reports for {instance.student.current_standard.get_display_name()}, {instance.term}",
                school_id=school.id if school else None
            )


# School Staff Signals
@receiver(post_save, sender='academics.SchoolStaff')
def create_staff_activity(sender, instance, created, **kwargs):
    """Create activity when staff is added to school"""
    if created:
        actor = get_actor_from_instance(instance)

        # Get position display
        position = instance.position if instance.position else "Staff"

        action.send(
            actor if actor else instance.staff,
            verb='added',
            action_object=instance.staff,
            target=instance.school,
            description=f"Added {instance.staff.get_full_name()} as {position} to {instance.school.name}",
            school_id=instance.school.id
        )


# Student Signals
@receiver(post_save, sender='schools.Student')
def create_student_activity(sender, instance, created, **kwargs):
    """Create activity when a student is created"""
    if created:
        actor = get_actor_from_instance(instance)
        school = instance.school if hasattr(instance, 'school') else None

        if actor:
            action.send(
                actor,
                verb='created',
                action_object=instance,
                description=f"Added new student {instance.get_full_name()}",
                school_id=school.id if school else None
            )

