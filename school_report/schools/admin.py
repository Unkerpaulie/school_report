from django.contrib import admin
from .models import School, Standard, Teacher, Student

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'principal', 'contact_phone', 'contact_email')
    search_fields = ('name', 'principal')

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
    list_display = ('first_name', 'last_name', 'title', 'school', 'is_active')
    list_filter = ('school', 'is_active')
    search_fields = ('first_name', 'last_name', 'school__name')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'parent_name', 'school', 'date_of_birth', 'is_active')
    list_filter = ('school', 'is_active')
    search_fields = ('first_name', 'last_name', 'parent_name', 'school__name')
