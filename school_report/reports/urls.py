from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Test management
    path('tests/', views.test_list, name='test_list'),
    path('tests/create/', views.test_create, name='test_create'),
    path('tests/<int:test_id>/', views.test_detail, name='test_detail'),
    path('tests/<int:test_id>/edit/', views.test_edit, name='test_edit'),
    path('tests/<int:test_id>/delete/', views.test_delete, name='test_delete'),
    
    # Test subjects
    path('tests/<int:test_id>/subjects/add/', views.test_subject_add, name='test_subject_add'),
    path('tests/<int:test_id>/subjects/<int:subject_id>/edit/', views.test_subject_edit, name='test_subject_edit'),
    path('tests/<int:test_id>/subjects/<int:subject_id>/delete/', views.test_subject_delete, name='test_subject_delete'),
    
    # Test scores
    path('tests/<int:test_id>/scores/', views.test_scores, name='test_scores'),
    path('tests/<int:test_id>/scores/bulk/', views.test_scores_bulk, name='test_scores_bulk'),
    path('tests/<int:test_id>/subjects/<int:subject_id>/scores/', views.subject_scores, name='subject_scores'),
    
    # Test status
    path('tests/<int:test_id>/finalize/', views.test_finalize, name='test_finalize'),
    
    # Subject management
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/create/', views.subject_create, name='subject_create'),
    path('subjects/<int:subject_id>/edit/', views.subject_edit, name='subject_edit'),
    path('subjects/<int:subject_id>/delete/', views.subject_delete, name='subject_delete'),

    # Report management
    path('reports/', views.report_list, name='report_list'),
    path('reports/term/<int:term_id>/class/<int:class_id>/', views.term_class_report_list, name='term_class_report_list'),
    path('reports/<int:report_id>/', views.report_detail, name='report_detail'),
    path('reports/<int:report_id>/edit/', views.report_edit, name='report_edit'),
]
