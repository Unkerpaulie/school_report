from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import UserProfile

class SchoolYear(models.Model):
    """
    Represents an academic year with three terms
    """
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='years')
    start_year = models.PositiveIntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_year']

    def __str__(self):
        return f"{self.start_year}-{self.start_year + 1} Academic Year"

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
    Represents the assignment of a teacher to a standard for a specific academic year
    """
    year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='standard_teachers')
    standard = models.ForeignKey('schools.Standard', on_delete=models.CASCADE, related_name='teacher_assignments')
    # Change from Teacher to UserProfile with constraint
    teacher = models.ForeignKey('core.UserProfile', on_delete=models.CASCADE, 
                               related_name='standard_assignments',
                               limit_choices_to={'user_type': 'teacher'})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'standard', 'teacher']

    def __str__(self):
        return f"{self.year} - {self.standard} - {self.teacher.get_full_name()}"

class Enrollment(models.Model):
    """
    Represents the enrollment of a student in a standard for a specific academic year
    """
    year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='enrollments')
    standard = models.ForeignKey('schools.Standard', on_delete=models.CASCADE, related_name='student_enrollments')
    student = models.ForeignKey('schools.Student', on_delete=models.CASCADE, related_name='standard_enrollments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'standard', 'student']

    def __str__(self):
        return f"{self.year} - {self.standard} - {self.student}"

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
    Represents the assignment of a staff member to a school for a specific academic year
    Similar to the Enrollment model for students
    """
    year = models.ForeignKey('academics.SchoolYear', on_delete=models.CASCADE, related_name='school_staff')
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='staff_assignments')
    staff = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='school_assignments')
    position = models.CharField(max_length=100, blank=True, null=True,
                               help_text="Position or role in the school")
    transfer_notes = models.TextField(blank=True, null=True, help_text="Notes about staff transfers")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'school', 'staff']
        ordering = ['-year__start_year', 'staff__user__last_name', 'staff__user__first_name']
        verbose_name = 'School Staff'
        verbose_name_plural = 'School Staff'

    def __str__(self):
        return f"{self.year} - {self.school} - {self.staff.get_full_name()}"

