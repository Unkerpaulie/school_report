from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    path('school-year/', views.SchoolYearSetupView.as_view(), name='school_year_setup'),
]
