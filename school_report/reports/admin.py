from django.contrib import admin
from .models import (
    Test, TestSubject, TestScore, StudentTermReview
)

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'standard', 'term', 'test_type', 'test_date', 'created_by')
    list_filter = ('term__year', 'term__term_number', 'test_type', 'standard__school')
    search_fields = ('standard__name', 'description', 'created_by__user__first_name', 'created_by__user__last_name')

@admin.register(TestSubject)
class TestSubjectAdmin(admin.ModelAdmin):
    list_display = ('test', 'standard_subject', 'max_score')
    list_filter = ('test__term', 'test__standard__school')
    search_fields = ('test__description', 'standard_subject__subject_name')

@admin.register(TestScore)
class TestScoreAdmin(admin.ModelAdmin):
    list_display = ('test_subject', 'student', 'score', 'percentage')
    list_filter = ('test_subject__test__term', 'test_subject__test__standard')
    search_fields = ('student__first_name', 'student__last_name', 'test_subject__standard_subject__subject_name')



@admin.register(StudentTermReview)
class StudentTermReviewAdmin(admin.ModelAdmin):
    list_display = ('term', 'student', 'days_present', 'days_late', 'attendance_percentage',
                   'attitude', 'respect', 'parental_support', 'attendance',
                   'assignment_completion', 'class_participation', 'time_management')
    list_filter = ('term__year', 'term__term_number')
    search_fields = ('student__first_name', 'student__last_name', 'remarks')
