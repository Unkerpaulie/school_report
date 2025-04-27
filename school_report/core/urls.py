from django.urls import path
from .views import HomeView, SchoolRegistrationView, ProfileView

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('register/', SchoolRegistrationView.as_view(), name='register_school'),
    path('profile/', ProfileView.as_view(), name='profile'),
]
