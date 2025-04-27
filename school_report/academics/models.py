from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from schools.models import School, Standard, Teacher, Student

class Year(models.Model):
    """
    Represents an academic year with three terms
    """
    start_year = models.PositiveIntegerField()

    # Term 1
    term1_start_date = models.DateField()
    term1_end_date = models.DateField()
    term1_school_days = models.PositiveIntegerField()

    # Term 2
    term2_start_date = models.DateField()
    term2_end_date = models.DateField()
    term2_school_days = models.PositiveIntegerField()

    # Term 3
    term3_start_date = models.DateField()
    term3_end_date = models.DateField()
    term3_school_days = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_year']

    def __str__(self):
        return f"{self.start_year}-{self.start_year + 1} Academic Year"

class Subject(models.Model):
    """
    Represents a subject taught in school
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class StandardTeacher(models.Model):
    """
    Represents the assignment of a teacher to a standard for a specific academic year
    """
    year = models.ForeignKey(Year, on_delete=models.CASCADE, related_name='standard_teachers')
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name='teacher_assignments')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='standard_assignments')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'standard', 'teacher']

    def __str__(self):
        return f"{self.year} - {self.standard} - {self.teacher}"

class Enrollment(models.Model):
    """
    Represents the enrollment of a student in a standard for a specific academic year
    """
    year = models.ForeignKey(Year, on_delete=models.CASCADE, related_name='enrollments')
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
    Represents a subject assigned to a standard for a specific academic year
    """
    year = models.ForeignKey(Year, on_delete=models.CASCADE, related_name='standard_subjects')
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name='assigned_subjects')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='standard_assignments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['year', 'standard', 'subject']

    def __str__(self):
        return f"{self.year} - {self.standard} - {self.subject}"
