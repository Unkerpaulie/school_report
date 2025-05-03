from django.contrib import admin
from .models import School, Standard, Teacher, Student, AdministrationStaff

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'principal_name', 'principal_user', 'contact_phone', 'contact_email', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'principal_name', 'principal_user__username')

@admin.register(Standard)
class StandardAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'school')
    list_filter = ('school', 'name')
    search_fields = ('name', 'school__name')

    def display_name(self, obj):
        return obj.get_name_display()
    display_name.short_description = 'Standard'

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'title', 'school', 'contact_email', 'user', 'get_user_type', 'is_active')
    list_filter = ('school', 'is_active', 'user__profile__user_type')
    search_fields = ('first_name', 'last_name', 'school__name', 'contact_email', 'user__username')

    def get_user_type(self, obj):
        """
        Get the user type from the associated user profile
        """
        if obj.user and hasattr(obj.user, 'profile'):
            return obj.user.profile.get_user_type_display()
        return '-'
    get_user_type.short_description = 'Role'

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'parent_name', 'school', 'date_of_birth', 'is_active')
    list_filter = ('school', 'is_active')
    search_fields = ('first_name', 'last_name', 'parent_name', 'school__name')
    readonly_fields = ('transfer_notes',)

@admin.register(AdministrationStaff)
class AdministrationStaffAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'title', 'position', 'school', 'contact_email', 'user', 'get_user_type', 'is_active')
    list_filter = ('school', 'is_active', 'position')
    search_fields = ('first_name', 'last_name', 'school__name', 'contact_email', 'user__username', 'position')

    def get_user_type(self, obj):
        """
        Get the user type from the associated user profile
        """
        if obj.user and hasattr(obj.user, 'profile'):
            return obj.user.profile.get_user_type_display()
        return '-'
    get_user_type.short_description = 'Role'
