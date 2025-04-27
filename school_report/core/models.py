from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """
    Extension of the built-in User model for additional profile information
    """
    USER_TYPE_CHOICES = [
        ('principal', 'Principal'),
        ('teacher', 'Teacher'),
        ('staff', 'Non-teaching Staff'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    must_change_password = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_user_type_display()}"

class Person(models.Model):
    """
    Abstract base class for people in the system (teachers, students)
    """
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
