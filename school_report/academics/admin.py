from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import SchoolYear, Term, StandardTeacher, Enrollment, StandardSubject


def link_to_school_year(obj):
    url = reverse('admin:academics_schoolyear_change', args=[obj.year_id])
    return format_html('<a href="{}">{}</a>', url, obj.year)
link_to_school_year.short_description = 'School Year'


def link_to_standard(obj):
    url = reverse('admin:schools_standard_change', args=[obj.standard_id])
    return format_html('<a href="{}">{}</a>', url, obj.standard)
link_to_standard.short_description = 'Standard'


def link_to_teacher(obj):
    url = reverse('admin:core_userprofile_change', args=[obj.teacher_id])
    return format_html('<a href="{}">{}</a>', url, obj.teacher.get_full_name())
link_to_teacher.short_description = 'Teacher'


def link_to_student(obj):
    url = reverse('admin:schools_student_change', args=[obj.student_id])
    return format_html('<a href="{}">{}</a>', url, obj.student.get_full_name())
link_to_student.short_description = 'Student'


@admin.register(SchoolYear)
class SchoolYearAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'start_year', 'school', 'created_at', 'updated_at')
    list_filter = ('school', 'created_at')
    search_fields = ('start_year', 'school__name')
    ordering = ('-start_year',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('school', 'start_year', 'created_at', 'updated_at')
        }),
    )


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('__str__', link_to_school_year, 'term_number', 'start_date', 'end_date', 'school_days', 'created_at', 'updated_at')
    list_filter = ('year', 'term_number', 'created_at')
    search_fields = ('year__start_year',)
    ordering = ('year', 'term_number')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('year', 'term_number', 'start_date', 'end_date', 'school_days', 'created_at', 'updated_at')
        }),
    )


@admin.register(StandardTeacher)
class StandardTeacherAdmin(admin.ModelAdmin):
    list_display = ('year', link_to_standard, link_to_teacher, 'created_at', 'updated_at')
    list_filter = ('year', 'standard__school', 'created_at')
    search_fields = ('teacher__first_name', 'teacher__last_name', 'standard__name')
    ordering = ('year', 'standard__name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('year', 'standard', 'teacher', 'created_at', 'updated_at')
        }),
    )


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('year', link_to_standard, link_to_student, 'created_at', 'updated_at')
    list_filter = ('year', 'standard__school', 'created_at')
    search_fields = ('student__first_name', 'student__last_name', 'standard__name')
    ordering = ('year', 'standard__name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('year', 'standard', 'student', 'created_at', 'updated_at')
        }),
    )


@admin.register(StandardSubject)
class StandardSubjectAdmin(admin.ModelAdmin):
    list_display = ('year', link_to_standard, 'subject_name', 'created_by', 'created_at', 'updated_at')
    list_filter = ('year', 'standard__school', 'created_at')
    search_fields = ('standard__name', 'subject_name', 'created_by__user__first_name', 'created_by__user__last_name')
    ordering = ('year', 'standard__name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('year', 'standard', 'subject_name', 'description', 'created_by', 'created_at', 'updated_at')
        }),
    )
