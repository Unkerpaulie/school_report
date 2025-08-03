from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import UserProfile

class SchoolYear(models.Model):
    """
    Represents an academic year with three terms
    """
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='years')
    start_year = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['school', 'start_year']
        ordering = ['-start_year']

    def __str__(self):
        return f"{self.start_year}-{self.start_year + 1}"

class Term(models.Model):
    """
    Represents a term within an academic year
    """
    TERM_CHOICES = [
        (1, 'Term 1'),
        (2, 'Term 2'),
        (3, 'Term 3'),
    ]
    
    year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='terms')
    term_number = models.PositiveSmallIntegerField(choices=TERM_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    school_days = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'term_number']
        ordering = ['year', 'term_number']

    def __str__(self):
        return f"{self.year} - {self.get_term_number_display()}"
    
class StandardTeacher(models.Model):
    """
    Represents teacher assignment history for a specific academic year.
    Latest record with non-null standard = current assignment.
    Latest record with null standard = unassigned.
    """
    year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='standard_teachers')
    standard = models.ForeignKey('schools.Standard', on_delete=models.CASCADE,
                               related_name='teacher_assignments',
                               null=True, blank=True)  # Null = unassigned
    teacher = models.ForeignKey('core.UserProfile', on_delete=models.CASCADE,
                               related_name='standard_assignments',
                               limit_choices_to={'user_type': 'teacher'},
                               null=True, blank=True)  # Null = unassigned
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Remove unique constraint to allow assignment history
        ordering = ['-created_at']  # Latest first

    def __str__(self):
        if self.standard and self.teacher:
            return f"{self.year} - {self.standard} - {self.teacher.get_full_name()}"
        elif self.standard and not self.teacher:
            return f"{self.year} - {self.standard} - No Teacher Assigned"
        elif not self.standard and self.teacher:
            return f"{self.year} - {self.teacher.get_full_name()} - Unassigned"
        else:
            return f"{self.year} - Invalid Assignment Record"

class Enrollment(models.Model):
    """
    Represents student enrollment history for a specific academic year.
    Latest record with non-null standard = current enrollment.
    Latest record with null standard = unenrolled.
    """
    year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='enrollments')
    standard = models.ForeignKey('schools.Standard', on_delete=models.CASCADE,
                               related_name='student_enrollments',
                               null=True, blank=True)  # Null = unenrolled
    student = models.ForeignKey('schools.Student', on_delete=models.CASCADE, related_name='standard_enrollments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Remove unique constraint to allow enrollment history
        ordering = ['-created_at']  # Latest first

    def __str__(self):
        if self.standard:
            return f"{self.year} - {self.standard} - {self.student}"
        else:
            return f"{self.year} - Unenrolled - {self.student}"

class StandardSubject(models.Model):
    """
    Represents a subject taught in a standard for a specific academic year
    """
    year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='standard_subjects')
    standard = models.ForeignKey('schools.Standard', on_delete=models.CASCADE, related_name='assigned_subjects')
    subject_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('core.UserProfile', on_delete=models.CASCADE, 
                                 related_name='created_subjects',
                                 limit_choices_to={'user_type': 'teacher'})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'standard', 'subject_name']

    def __str__(self):
        return f"{self.year} - {self.standard} - {self.subject_name}"

class SchoolStaff(models.Model):
    """
    Represents the employment relationship between a staff member and a school.
    This is persistent across academic years - staff don't need to be "reassigned"
    to the school each year, only teachers get reassigned to different classes.
    """
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='staff_members')
    staff = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='school_employment')
    position = models.CharField(max_length=100, blank=True, null=True,
                               help_text="Position or role in the school (e.g., Principal, Vice Principal, Secretary)")
    hire_date = models.DateField(null=True, blank=True, help_text="Date when staff member was hired")
    transfer_notes = models.TextField(blank=True, null=True, help_text="Notes about staff transfers or role changes")
    is_active = models.BooleanField(default=True, help_text="False if staff member has left the school")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['school', 'staff']  # One employment record per staff per school
        ordering = ['staff__user__last_name', 'staff__user__first_name']
        verbose_name = 'School Staff Member'
        verbose_name_plural = 'School Staff Members'

    def __str__(self):
        position_str = f" ({self.position})" if self.position else ""
        return f"{self.staff.get_full_name()}{position_str} - {self.school.name}"

