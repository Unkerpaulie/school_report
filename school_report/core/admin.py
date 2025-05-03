from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile
from schools.models import AdministrationStaff

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'

    # Make phone_number more prominent
    fields = ('user_type', 'phone_number', 'must_change_password')

    def get_formset(self, request, obj=None, **kwargs):
        """
        Override to ensure a profile is always created for new users
        """
        formset = super().get_formset(request, obj, **kwargs)
        if not obj:  # This is a new user being created
            # Set default values for new profiles
            formset.form.base_fields['user_type'].initial = 'staff'
            # Make phone_number required for principals
            if 'user_type' in formset.form.base_fields and formset.form.base_fields['user_type'].initial == 'principal':
                formset.form.base_fields['phone_number'].required = True
        return formset

# Extend the default UserAdmin
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_user_type', 'get_school', 'is_staff')

    # Make first name, last name, and email required in the admin
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email'), 'classes': ('wide',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Make first name, last name, and email required in the add form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'email'),
        }),
    )

    def get_user_type(self, obj):
        try:
            return obj.profile.get_user_type_display()
        except UserProfile.DoesNotExist:
            return '-'
    get_user_type.short_description = 'User Type'

    def get_school(self, obj):
        """
        Get the school associated with the user
        """
        try:
            # For principals
            if obj.profile.user_type == 'principal' and hasattr(obj, 'administered_schools'):
                school = obj.administered_schools.first()
                if school:
                    return school.name

            # For teachers
            elif obj.profile.user_type == 'teacher' and hasattr(obj, 'teacher_profile'):
                return obj.teacher_profile.school.name

            # For administration staff
            elif obj.profile.user_type == 'administration' and hasattr(obj, 'admin_profile'):
                return obj.admin_profile.school.name

            return '-'
        except Exception:
            return '-'
    get_school.short_description = 'School'

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
