from django.urls import path
from .views import (
    TeacherListView, TeacherCreateView, StudentListView,
    StandardListView, StandardDetailView, TeacherAssignmentCreateView
)

app_name = 'schools'

urlpatterns = [
    # Teacher URLs
    path('teachers/', TeacherListView.as_view(), name='teacher_list'),
    path('teachers/add/', TeacherCreateView.as_view(), name='teacher_add'),

    # Student URLs
    path('students/', StudentListView.as_view(), name='student_list'),

    # Class/Standard URLs
    path('classes/', StandardListView.as_view(), name='standard_list'),
    path('classes/<int:pk>/', StandardDetailView.as_view(), name='standard_detail'),
    path('classes/assign-teacher/', TeacherAssignmentCreateView.as_view(), name='assign_teacher'),
]
