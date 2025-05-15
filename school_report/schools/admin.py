from django.contrib import admin
from .models import School, Standard, Student
from core.models import UserProfile

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

# Register UserProfile in the core app's admin.py instead
# Removing this registration from schools/admin.py
