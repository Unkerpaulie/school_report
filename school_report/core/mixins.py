"""
Mixins for views in the School Report System
"""
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from schools.models import School

class SchoolAdminRequiredMixin:
    """
    Mixin that requires the user to be a principal or non-teaching staff of the school.

    This mixin should be used for views that should be accessible to school administrators
    (principals and non-teaching staff) but not to teachers or other users.

    The view using this mixin must have a `school_slug` URL parameter.
    """
    def dispatch(self, request, *args, **kwargs):
        # First check if the user is authenticated
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user is a principal of this school
        is_principal = (
            request.user.profile.user_type == 'principal' and
            hasattr(request.user, 'administered_schools') and
            request.user.administered_schools.filter(pk=self.school.pk).exists()
        )

        # Check if user is administration staff for this school
        is_admin = (
            request.user.profile.user_type == 'administration' and
            hasattr(request.user, 'admin_profile') and
            request.user.admin_profile.school.pk == self.school.pk
        )

        # Allow access if user is either a principal of this school or an administration member
        if is_principal or is_admin:
            return super().dispatch(request, *args, **kwargs)

        # If not, show an error message and redirect
        messages.warning(request, "You do not have permission to access this page.")
        return redirect('core:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        return context


class PrincipalRequiredMixin:
    """
    Mixin that requires the user to be the principal of the school.

    This mixin should be used for views that should only be accessible to the principal,
    such as registering a new school.

    For views that need a school_slug parameter, use SchoolPrincipalRequiredMixin instead.
    """
    def dispatch(self, request, *args, **kwargs):
        # First check if the user is authenticated
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Check if user is a principal
        if request.user.profile.user_type != 'principal':
            messages.warning(request, "Only principals can access this page.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)


class SchoolPrincipalRequiredMixin:
    """
    Mixin that requires the user to be the principal of the specific school.

    This mixin should be used for views that should only be accessible to the principal
    of the specific school, such as managing school settings.

    The view using this mixin must have a `school_slug` URL parameter.
    """
    def dispatch(self, request, *args, **kwargs):
        # First check if the user is authenticated
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user is the principal of this school
        is_principal = (
            request.user.profile.user_type == 'principal' and
            hasattr(request.user, 'administered_schools') and
            request.user.administered_schools.filter(pk=self.school.pk).exists()
        )

        if is_principal:
            return super().dispatch(request, *args, **kwargs)

        # If not, show an error message and redirect
        messages.warning(request, "Only the principal of this school can access this page.")
        return redirect('core:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        return context


class SchoolAccessRequiredMixin:
    """
    Mixin that requires the user to have access to the school.

    This mixin should be used for views that should be accessible to principals,
    non-teaching staff, and teachers of the specific school.

    The view using this mixin must have a `school_slug` URL parameter.
    """
    def dispatch(self, request, *args, **kwargs):
        # First check if the user is authenticated
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user is a principal of this school
        is_principal = (
            request.user.profile.user_type == 'principal' and
            hasattr(request.user, 'administered_schools') and
            request.user.administered_schools.filter(pk=self.school.pk).exists()
        )

        # Check if user is administration staff for this school
        is_admin = (
            request.user.profile.user_type == 'administration' and
            hasattr(request.user, 'admin_profile') and
            request.user.admin_profile.school.pk == self.school.pk
        )

        # Check if user is a teacher at this school
        is_teacher = (
            request.user.profile.user_type == 'teacher' and
            hasattr(request.user, 'teacher_profile') and
            request.user.teacher_profile.school.pk == self.school.pk
        )

        # Allow access if user is either a principal, administration member, or teacher at this school
        if is_principal or is_admin or is_teacher:
            return super().dispatch(request, *args, **kwargs)

        # If not, show an error message and redirect
        messages.warning(request, "You do not have permission to access this page.")
        return redirect('core:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        return context
