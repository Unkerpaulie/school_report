"""
Mixins for views in the School Report System
"""
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from schools.models import School
from core.utils import user_can_access_view, get_user_session_info

class SessionAccessMixin(LoginRequiredMixin):
    """
    Base mixin for session-based access control.

    This mixin uses session data to validate access, eliminating the need for
    repeated database queries. All access control is based on session state
    set up during login.
    """

    # Override these in subclasses
    required_role = None  # Single role or list of roles
    require_school = True  # Whether this view requires school access

    def dispatch(self, request, *args, **kwargs):
        # Get school slug if this view requires school access
        school_slug = kwargs.get('school_slug') if self.require_school else None

        # Use centralized access control
        can_access, redirect_url, message = user_can_access_view(
            request,
            required_role=self.required_role,
            required_school_slug=school_slug
        )

        if not can_access:
            if message:
                messages.warning(request, message)
            return redirect(redirect_url)

        # Store session info for easy access in views
        self.session_info = get_user_session_info(request)

        # If school is required, get the school object
        if self.require_school and school_slug:
            self.school_slug = school_slug
            self.school = get_object_or_404(School, slug=school_slug)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add session information to context"""
        context = super().get_context_data(**kwargs)
        context.update(self.session_info)

        # Add school info if available
        if hasattr(self, 'school'):
            context['school'] = self.school
            context['school_slug'] = self.school_slug

        return context


# Specific mixins using the session-based approach

class SchoolAdminRequiredMixin(SessionAccessMixin):
    """
    Mixin that requires the user to be a principal or administration staff of the school.
    """
    required_role = ['principal', 'administration']


class PrincipalRequiredMixin(SessionAccessMixin):
    """
    Mixin that requires the user to be a principal (for views without school_slug).
    """
    required_role = 'principal'
    require_school = False


class SchoolPrincipalRequiredMixin(SessionAccessMixin):
    """
    Mixin that requires the user to be the principal of the specific school.
    """
    required_role = 'principal'


class SchoolAccessRequiredMixin(SessionAccessMixin):
    """
    Mixin that requires the user to have access to the school.
    Allows all staff types (principal, administration, teacher).
    """
    # No role restriction - just requires school access


class TeacherOnlyMixin(SessionAccessMixin):
    """
    Mixin that restricts access to teachers only.
    """
    required_role = 'teacher'


# Legacy aliases for backward compatibility
SchoolAccessMixin = SchoolAccessRequiredMixin
