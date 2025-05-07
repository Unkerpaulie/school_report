from django.urls import path
from .views import (
    StaffListView, TeacherCreateView, AdminStaffCreateView, StudentListView,
    StandardListView, StandardDetailView, TeacherAssignmentCreateView,
    TeacherUnassignView
)
from .dashboard import SchoolDashboardView

app_name = 'schools'

urlpatterns = [
    # Dashboard URL (empty path for the school root)
    path('', SchoolDashboardView.as_view(), name='dashboard'),

    # Staff URLs
    path('staff/', StaffListView.as_view(), name='staff_list'),
    path('staff/add-teacher/', TeacherCreateView.as_view(), name='teacher_add'),
    path('staff/add-admin/', AdminStaffCreateView.as_view(), name='admin_staff_add'),

    # Student URLs
    path('students/', StudentListView.as_view(), name='student_list'),

    # Class/Standard URLs
    path('classes/', StandardListView.as_view(), name='standard_list'),
    path('classes/assign-teacher/<int:pk>/', TeacherAssignmentCreateView.as_view(), name='assign_teacher'),
    path('classes/unassign-teacher/<int:assignment_id>/', TeacherUnassignView.as_view(), name='unassign_teacher'),
    path('classes/<int:pk>/', StandardDetailView.as_view(), name='standard_detail'),
]
