from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

class UserProfile(models.Model):
    """
    Comprehensive profile for all user types
    """
    USER_TYPE_CHOICES = [
        ('principal', 'Principal'),
        ('teacher', 'Teacher'),
        ('administration', 'Administration'),
    ]

    TITLE_CHOICES = [
        ('Mr', 'Mr'),
        ('Mrs', 'Mrs'),
        ('Ms', 'Ms'),
        ('Dr', 'Dr'),
        ('Prof', 'Prof'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    must_change_password = models.BooleanField(default=False)

    # Fields for all staff types
    title = models.CharField(max_length=10, choices=TITLE_CHOICES, blank=True, null=True)
    transfer_notes = models.TextField(blank=True, null=True, help_text="Notes about transfers")

    # Administration-specific fields
    position = models.CharField(max_length=100, blank=True, null=True,
                               help_text="Position or role in the school administration")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.get_full_name()} - {self.get_user_type_display()}"

    # Properties to maintain compatibility with existing code
    @property
    def first_name(self):
        return self.user.first_name

    @property
    def last_name(self):
        return self.user.last_name

    @property
    def contact_email(self):
        return self.user.email

    @property
    def is_active(self):
        return self.user.is_active

    @property
    def is_principal(self):
        return self.user_type == 'principal'

    @property
    def is_teacher(self):
        return self.user_type == 'teacher'

    @property
    def is_administration(self):
        return self.user_type == 'administration'

    def get_full_name(self):
        """Return the full name with title if available"""
        if self.title:
            return f"{self.title} {self.user.first_name} {self.user.last_name}"
        return f"{self.user.first_name} {self.user.last_name}"

    def get_current_school(self):
        """
        Get the current active school for this user
        Returns the School object or None if not assigned to any school
        """
        # For principals, get the administered school
        if self.is_principal and hasattr(self.user, 'administered_schools'):
            return self.user.administered_schools.first()

        # For teachers and administration, get from SchoolStaff
        try:
            from academics.models import SchoolYear
            from schools.models import SchoolStaff

            # Get current school year
            current_year = SchoolYear.objects.filter(
                start_year__lte=datetime.now().year
            ).order_by('-start_year').first()

            if current_year:
                # Get active school assignment for this user in the current year
                school_assignment = SchoolStaff.objects.filter(
                    staff=self,
                    year=current_year,
                    is_active=True
                ).first()

                if school_assignment:
                    return school_assignment.school
        except:
            pass

        return None

    @property
    def school(self):
        """
        Property to maintain compatibility with existing code
        """
        return self.get_current_school()

    # Compatibility methods to mimic Teacher/AdministrationStaff behavior
    @property
    def teacher_profile(self):
        """For compatibility with code expecting user.teacher_profile"""
        if self.is_teacher:
            return self
        return None

    @property
    def admin_profile(self):
        """For compatibility with code expecting user.admin_profile"""
        if self.is_administration or self.is_principal:
            return self
        return None

