from django.db import models
from django.core.files.storage import FileSystemStorage
from core.models import Person

fs = FileSystemStorage(location='media/school_logos/')

class School(models.Model):
    """
    Represents a primary school in the system
    """
    name = models.CharField(max_length=200)
    address = models.TextField()
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    principal = models.CharField(max_length=200, blank=True, null=True)
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True, storage=fs)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Standard(models.Model):
    """
    Represents a grade level (Infant 1-2, Standard 1-5) in a school
    """
    STANDARD_CHOICES = [
        ('INF1', 'Infant 1'),
        ('INF2', 'Infant 2'),
        ('STD1', 'Standard 1'),
        ('STD2', 'Standard 2'),
        ('STD3', 'Standard 3'),
        ('STD4', 'Standard 4'),
        ('STD5', 'Standard 5'),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='standards')
    name = models.CharField(max_length=50, choices=STANDARD_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['school', 'name']

    def __str__(self):
        return f"{self.school.name} - {self.get_name_display()}"

class Teacher(Person):
    """
    Represents a teacher in the school system
    """
    TITLE_CHOICES = [
        ('Mr', 'Mr'),
        ('Mrs', 'Mrs'),
        ('Ms', 'Ms'),
        ('Dr', 'Dr'),
        ('Prof', 'Prof'),
    ]

    title = models.CharField(max_length=10, choices=TITLE_CHOICES)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='teachers')

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.title} {self.first_name} {self.last_name}"

class Student(Person):
    """
    Represents a student in the school system
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='students')
    date_of_birth = models.DateField()
    parent_name = models.CharField(max_length=200, help_text="Full name of parent or guardian")

    class Meta:
        ordering = ['last_name', 'first_name']
