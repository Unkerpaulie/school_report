from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    # Year management
    path('years/', views.YearListView.as_view(), name='year_list'),
    path('years/add/', views.SchoolYearSetupView.as_view(), name='school_year_setup'),
    path('years/<int:pk>/edit/', views.YearUpdateView.as_view(), name='year_update'),
    path('years/<int:pk>/delete/', views.YearDeleteView.as_view(), name='year_delete'),
]
