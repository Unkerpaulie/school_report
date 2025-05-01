from django.urls import path, include
from .views import (
    HomeView, SchoolRegistrationView, ProfileView, CustomLogoutView,
    SchoolRedirectView
)

app_name = 'core'

urlpatterns = [
    # Public routes
    path('', HomeView.as_view(), name='home'),

    # Authentication routes
    path('register/', SchoolRegistrationView.as_view(), name='register_school'),
    path('<slug:school_slug>/profile/', ProfileView.as_view(), name='profile'),
    path('logout/', CustomLogoutView.as_view(), name='custom_logout'),

    # School-specific routes
    path('my-school/', SchoolRedirectView.as_view(), name='my_school'),


]
