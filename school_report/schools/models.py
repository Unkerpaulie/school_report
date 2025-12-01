from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

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
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True)
    groups_per_standard = models.PositiveIntegerField(
        default=1,
        help_text="Number of groups/classes per standard level (applies to all standards)"
    )
    is_active = models.BooleanField(default=True)
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
    Each standard can have multiple groups/classes
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
    group_number = models.PositiveIntegerField(default=1, help_text="Group number within this standard level")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['school', 'name', 'group_number']
        ordering = ['name', 'group_number']

    def get_display_name(self):
        """
        Get display name: 'Infant 1 - 2' or 'Infant 1 - Mrs Charles'
        Shows teacher name if assigned, otherwise shows group number
        """
        base_name = self.get_name_display()

        # Check if teacher is assigned
        try:
            from core.utils import get_current_standard_teacher, get_current_year_and_term

            current_year, _, _ = get_current_year_and_term(school=self.school)
            if current_year:
                teacher_assignment = get_current_standard_teacher(self, current_year)
                if teacher_assignment and teacher_assignment.teacher:
                    teacher = teacher_assignment.teacher
                    return f"{base_name} - {teacher.title} {teacher.last_name}"
        except:
            # Fallback if utils not available or error occurs
            pass

        # No teacher assigned, show group number
        return f"{base_name} - {self.group_number}"

    def __str__(self):
        return f"{self.school.name} - {self.get_display_name()}"

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
    created_by = models.ForeignKey('core.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='created_students', help_text="User who created this student record")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self):
        """Return the student's full name"""
        return f"{self.first_name} {self.last_name}"


# Signal to create standard classes when a school is created
@receiver(post_save, sender=School)
def create_standard_classes(sender, instance, created, **kwargs):
    """
    Create standard classes for a newly created school
    Creates multiple groups per standard based on school's groups_per_standard setting
    """
    if created:
        # Create all standard classes for the school with groups
        for standard_code, standard_name in Standard.STANDARD_CHOICES:
            # Create multiple groups for each standard
            for group_number in range(1, instance.groups_per_standard + 1):
                Standard.objects.create(
                    school=instance,
                    name=standard_code,
                    group_number=group_number
                )