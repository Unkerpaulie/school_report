"""
Mixins for views in the School Report System
"""
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from schools.models import School
from core.utils import user_has_school_access, set_user_school_session, clear_user_school_session

class SchoolAccessMixin(LoginRequiredMixin):
    """
    Base mixin to handle school access control for views.

    This mixin:
    1. Gets the school from the URL slug
    2. Checks if the user has access to the school
    3. Sets session variables for easy access
    4. Provides the school object to the view

    Usage:
        class MyView(SchoolAccessMixin, TemplateView):
            # The view will automatically have:
            # - self.school (School object)
            # - self.school_slug (string)
            # - Access control enforced
            # - Session variables set
    """

    # Override these in subclasses if needed
    access_denied_message = "You do not have access to this school."
    access_denied_redirect = 'core:home'

    # Set to specific user types to restrict access (e.g., ['principal', 'administration'])
    allowed_user_types = None

    def dispatch(self, request, *args, **kwargs):
        # Get the school from URL
        self.school_slug = kwargs.get('school_slug')
        if not self.school_slug:
            messages.error(request, "School not specified.")
            return redirect(self.access_denied_redirect)

        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check user access to this school
        has_access, user_role, access_details = user_has_school_access(request.user, self.school)

        if not has_access:
            reason = access_details.get('reason', 'Unknown reason')
            messages.warning(request, f"{self.access_denied_message} ({reason})")
            clear_user_school_session(request)
            return redirect(self.access_denied_redirect)

        # Check if user type is allowed (if restriction is set)
        if self.allowed_user_types and user_role not in self.allowed_user_types:
            messages.warning(request, f"This page is restricted to {', '.join(self.allowed_user_types)} only.")
            return redirect(self.access_denied_redirect)

        # Set session variables for easy access
        set_user_school_session(request, self.school, access_details)

        # Store access information for use in the view
        self.user_role = user_role
        self.access_details = access_details

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add school information to context"""
        context = super().get_context_data(**kwargs)
        context.update({
            'school': self.school,
            'school_slug': self.school_slug,
            'user_role': self.user_role,
            'access_details': self.access_details,
        })
        return context


class SchoolAdminRequiredMixin(SchoolAccessMixin):
    """
    Mixin that requires the user to be a principal or administration staff of the school.
    """
    allowed_user_types = ['principal', 'administration']
    access_denied_message = "Only principals and administrators can access this page."


class PrincipalRequiredMixin(LoginRequiredMixin):
    """
    Mixin that requires the user to be a principal (for views without school_slug).

    This mixin should be used for views that should only be accessible to principals,
    such as registering a new school.

    For views that need a school_slug parameter, use SchoolPrincipalRequiredMixin instead.
    """
    def dispatch(self, request, *args, **kwargs):
        # Check if user is a principal
        if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'principal':
            messages.warning(request, "Only principals can access this page.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)


class SchoolPrincipalRequiredMixin(SchoolAccessMixin):
    """
    Mixin that requires the user to be the principal of the specific school.
    """
    allowed_user_types = ['principal']
    access_denied_message = "Only the principal can access this page."


class SchoolAccessRequiredMixin(SchoolAccessMixin):
    """
    Mixin that requires the user to have access to the school.

    This allows principals, administration staff, and teachers of the specific school.
    """
    # No user type restriction - allows all staff types
    access_denied_message = "You do not have access to this school."


class TeacherOnlyMixin(SchoolAccessMixin):
    """
    Mixin that restricts access to teachers only.
    """
    allowed_user_types = ['teacher']
    access_denied_message = "Only teachers can access this page."
