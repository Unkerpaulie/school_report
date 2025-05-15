from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from schools.models import School, Standard, Student
from core.models import UserProfile

class SchoolYear(models.Model):
    """
    Represents an academic year with three terms
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='years')
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
    
    def clean(self):
        """
        Validate that term dates are valid
        """
        from django.core.exceptions import ValidationError
        
        # Check that end date is after start date
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError({'end_date': f'{self.get_term_number_display()} end date must be after the start date.'})
        
        # Check for overlapping terms in the same year
        if self.year_id and self.start_date and self.end_date:
            overlapping_terms = Term.objects.filter(
                year=self.year,
                start_date__lte=self.end_date,
                end_date__gte=self.start_date
            ).exclude(pk=self.pk)
            
            if overlapping_terms.exists():
                raise ValidationError('Term dates overlap with another term in the same academic year.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class StandardTeacher(models.Model):
    """
    Represents the assignment of a teacher to a standard for a specific academic year
    """
    year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name='standard_teachers')
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name='teacher_assignments')
    # Change from Teacher to UserProfile with constraint
    teacher = models.ForeignKey(UserProfile, on_delete=models.CASCADE, 
                               related_name='standard_assignments',
                               limit_choices_to={'user_type': 'teacher'})
    is_active = models.BooleanField(default=True)
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
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name='student_enrollments')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='standard_enrollments')
    is_active = models.BooleanField(default=True)
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
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name='assigned_subjects')
    subject_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'standard', 'subject_name']

    def __str__(self):
        return f"{self.year} - {self.standard} - {self.subject_name}"
