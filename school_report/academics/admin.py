from django.contrib import admin
from .models import Year, Subject, StandardTeacher, Enrollment, StandardSubject

@admin.register(Year)
class YearAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'start_year')
    search_fields = ('start_year',)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(StandardTeacher)
class StandardTeacherAdmin(admin.ModelAdmin):
    list_display = ('year', 'standard', 'teacher', 'is_active')
    list_filter = ('year', 'standard__school', 'is_active')
    search_fields = ('teacher__first_name', 'teacher__last_name', 'standard__name')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('year', 'standard', 'student', 'is_active')
    list_filter = ('year', 'standard__school', 'is_active')
    search_fields = ('student__first_name', 'student__last_name', 'standard__name')

@admin.register(StandardSubject)
class StandardSubjectAdmin(admin.ModelAdmin):
    list_display = ('year', 'standard', 'subject')
    list_filter = ('year', 'standard__school', 'subject')
    search_fields = ('standard__name', 'subject__name')
