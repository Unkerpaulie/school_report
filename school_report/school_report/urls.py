"""
URL configuration for school_report project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from core.views import CustomPasswordChangeView

urlpatterns = [
    # School-specific URLs are now included in core.urls under the school slug

    # Authentication URLs
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    # Using custom logout view in core.urls.py instead for better security (POST method)
    # path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('accounts/password_change/', CustomPasswordChangeView.as_view(), name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Admin URLs
    path('admin/', admin.site.urls),

    # Core URLs - these should be last as they handle the root paths
    path('', include(('core.urls', 'core'), namespace='core')),

    # Include app URLs in order of specificity
    # Schools app URLs must come first since they handle the main school dashboard
    path('<slug:school_slug>/', include('schools.urls', namespace='schools')),

    # Academics app URLs - these will be matched only if the URL doesn't match any schools URLs
    path('<slug:school_slug>/academics/', include('academics.urls', namespace='academics')),

]

# Development settings
if settings.DEBUG:
    # Serve media files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Debug toolbar
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]
