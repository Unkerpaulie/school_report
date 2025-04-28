from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'

    def get_formset(self, request, obj=None, **kwargs):
        """
        Override to ensure a profile is always created for new users
        """
        formset = super().get_formset(request, obj, **kwargs)
        if not obj:  # This is a new user being created
            # Set default values for new profiles
            formset.form.base_fields['user_type'].initial = 'staff'
        return formset

# Extend the default UserAdmin
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_user_type', 'is_staff')

    def get_user_type(self, obj):
        try:
            return obj.profile.get_user_type_display()
        except UserProfile.DoesNotExist:
            return '-'
    get_user_type.short_description = 'User Type'

    def save_model(self, request, obj, form, change):
        """
        Override save_model to handle profile creation properly
        """
        # Set a flag to prevent signal from creating a duplicate profile
        obj._profile_creating = True
        super().save_model(request, obj, form, change)

        # If this is a new user, the profile will be created by the inline
        # If it's an existing user, the profile will be updated by the inline

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
