from django.urls import path
from .views import (
    HomeView, SchoolRegistrationView, CustomLogoutView
)

app_name = 'core'

urlpatterns = [
    # Public routes
    path('', HomeView.as_view(), name='home'),

    # Authentication routes
    path('register/', SchoolRegistrationView.as_view(), name='register_school'),
    path('logout/', CustomLogoutView.as_view(), name='custom_logout'),

    # School-specific routes
    # path('my-school/', SchoolRedirectView.as_view(), name='my_school'),


]
