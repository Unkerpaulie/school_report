from django.db import models
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import UserProfile

fs = FileSystemStorage(location='media/school_logos/')

class School(models.Model):
    """
    Represents a primary school in the system
    """
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, help_text="URL-friendly version of the school name")
    address = models.TextField()
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    principal_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='administered_schools')
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True, storage=fs)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Generate slug from name if not provided
        if not self.slug:
            self.slug = slugify(self.name)

        # Ensure slug is unique
        original_slug = self.slug
        counter = 1
        while School.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1

        super().save(*args, **kwargs)

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

class Student(models.Model):
    """
    Represents a student in the school system
    """
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    date_of_birth = models.DateField()
    parent_name = models.CharField(max_length=200, help_text="Full name of parent or guardian")
    transfer_notes = models.TextField(blank=True, null=True, help_text="Notes about student transfers")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        
    def __str__(self):
        return f"{self.first_name} {self.last_name}"

# Signal to create standard classes when a school is created
@receiver(post_save, sender=School)
def create_standard_classes(sender, instance, created, **kwargs):
    """
    Create standard classes for a newly created school
    """
    if created:
        # Create all standard classes for the school
        for standard_code, standard_name in Standard.STANDARD_CHOICES:
            Standard.objects.create(
                school=instance,
                name=standard_code
            )