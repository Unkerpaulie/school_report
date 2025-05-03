from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, raw, **kwargs):
    """
    Create a UserProfile for a newly created User

    The 'raw' parameter is True when the model is being created during a fixture load
    or when loading from admin loaddata.
    """
    # Skip during fixtures loading or if the profile already exists
    if raw or hasattr(instance, '_profile_creating'):
        return

    # Check if a profile already exists
    if created and not hasattr(instance, 'profile'):
        # Default to administration user type if not specified
        UserProfile.objects.create(user=instance, user_type='administration')

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, raw, **kwargs):
    """
    Save the UserProfile when the User is saved
    """
    # Skip during fixtures loading or if we're in the process of creating a profile
    if raw or hasattr(instance, '_profile_creating'):
        return

    # Only try to save existing profiles
    if hasattr(instance, 'profile'):
        # Set a flag to prevent infinite recursion
        instance._profile_creating = True
        instance.profile.save()
        delattr(instance, '_profile_creating')
