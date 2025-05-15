from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'

    # Make phone_number more prominent
    fields = ('user_type', 'phone_number', 'must_change_password', 'school', 'title', 'position', 'transfer_notes')

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
            return obj.profile.school.name if obj.profile.school else '-'
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

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Add a standalone UserProfile admin for direct access
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'user_type', 'school', 'contact_email', 'phone_number', 'is_active')
    list_filter = ('user_type', 'school', 'user__is_active')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'phone_number')
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Name'
    
    def contact_email(self, obj):
        return obj.contact_email
    contact_email.short_description = 'Email'
    
    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = 'Active'
