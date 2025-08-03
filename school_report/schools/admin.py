from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import School, Standard, Student
from academics.models import SchoolStaff


def link_to_principal(obj):
    if obj.principal_user:
        url = reverse('admin:core_userprofile_change', args=[obj.principal_user_id])
        return format_html('<a href="{}">{}</a>', url, obj.principal_user.get_full_name())
    return "-"
link_to_principal.short_description = 'Principal'


def link_to_school(obj):
    url = reverse('admin:schools_school_change', args=[obj.school_id])
    return format_html('<a href="{}">{}</a>', url, obj.school)
link_to_school.short_description = 'School'


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', link_to_principal, 'contact_phone', 'contact_email', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'principal_user__user__username', 'principal_user__user__first_name', 'principal_user__user__last_name')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('name', 'principal_user', 'contact_phone', 'contact_email', 'is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(Standard)
class StandardAdmin(admin.ModelAdmin):
    list_display = ('display_name', link_to_school, 'created_at', 'updated_at')
    list_filter = ('school', 'created_at')
    search_fields = ('name', 'school__name')
    ordering = ('school', 'name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    def display_name(self, obj):
        return obj.get_name_display()
    display_name.short_description = 'Standard'
    
    fieldsets = (
        (None, {
            'fields': ('school', 'name', 'created_at', 'updated_at')
        }),
    )


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'date_of_birth', 'parent_name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('first_name', 'last_name', 'parent_name')
    ordering = ('last_name', 'first_name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    get_full_name.short_description = 'Name'
    
    fieldsets = (
        (None, {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'parent_name', 'is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(SchoolStaff)
class SchoolStaffAdmin(admin.ModelAdmin):
    list_display = ('staff', link_to_school, 'position', 'hire_date', 'is_active', 'created_at', 'updated_at')
    list_filter = ('school', 'is_active', 'staff__user_type', 'hire_date', 'created_at')
    search_fields = (
        'staff__user__first_name', 'staff__user__last_name',
        'position', 'school__name',
        'staff__user__username'
    )
    ordering = ('school', 'staff__user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('school', 'staff', 'position', 'hire_date', 'transfer_notes', 'is_active', 'created_at', 'updated_at')
        }),
    )
