from django.urls import path
from .views import (
    HomeView, SchoolRegistrationView, CustomLogoutView, SchoolUpdateView, CustomLoginView, SessionDebugView,
    GroupManagementView, GroupChangeConfirmationView, GroupChangeExecuteView
)

app_name = 'core'

urlpatterns = [
    # Public routes
    path('', HomeView.as_view(), name='home'),

    # Authentication routes
    path('register/', SchoolRegistrationView.as_view(), name='register_school'),
    path('logout/', CustomLogoutView.as_view(), name='custom_logout'),

    # School-specific routes
    path('<slug:school_slug>/school-info/', SchoolUpdateView.as_view(), name='school_update'),
    path('<slug:school_slug>/group-management/', GroupManagementView.as_view(), name='group_management'),
    path('<slug:school_slug>/group-management/confirm/<int:new_groups>/', GroupChangeConfirmationView.as_view(), name='group_change_confirmation'),
    path('<slug:school_slug>/group-management/execute/<int:new_groups>/', GroupChangeExecuteView.as_view(), name='group_change_execute'),
    # path('my-school/', SchoolRedirectView.as_view(), name='my_school'),

    # Debug route (remove in production)
    path('debug/session/', SessionDebugView.as_view(), name='session_debug'),


]
