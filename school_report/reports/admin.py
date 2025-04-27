from django.contrib import admin
from .models import TermTest, StudentSubjectScore, StudentAttendance, QualitativeRating, TeacherRemark

@admin.register(TermTest)
class TermTestAdmin(admin.ModelAdmin):
    list_display = ('year', 'term', 'standard_subject', 'max_marks')
    list_filter = ('year', 'term', 'standard_subject__standard', 'standard_subject__subject')
    search_fields = ('standard_subject__standard__name', 'standard_subject__subject__name')

@admin.register(StudentSubjectScore)
class StudentSubjectScoreAdmin(admin.ModelAdmin):
    list_display = ('term_test', 'student', 'score', 'percentage')
    list_filter = ('term_test__year', 'term_test__term', 'term_test__standard_subject__standard')
    search_fields = ('student__first_name', 'student__last_name', 'term_test__standard_subject__subject__name')

@admin.register(StudentAttendance)
class StudentAttendanceAdmin(admin.ModelAdmin):
    list_display = ('year', 'term', 'student', 'days_present', 'days_late', 'attendance_percentage')
    list_filter = ('year', 'term')
    search_fields = ('student__first_name', 'student__last_name')

@admin.register(QualitativeRating)
class QualitativeRatingAdmin(admin.ModelAdmin):
    list_display = ('year', 'term', 'student', 'attitude', 'respect', 'parental_support',
                   'attendance', 'assignment_completion', 'class_participation', 'time_management')
    list_filter = ('year', 'term')
    search_fields = ('student__first_name', 'student__last_name')

@admin.register(TeacherRemark)
class TeacherRemarkAdmin(admin.ModelAdmin):
    list_display = ('year', 'term', 'student')
    list_filter = ('year', 'term')
    search_fields = ('student__first_name', 'student__last_name', 'remarks')
