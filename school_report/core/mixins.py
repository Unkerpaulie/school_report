"""
Mixins for views in the School Report System
"""
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from schools.models import School
from academics.models import SchoolStaff

class SchoolAdminRequiredMixin:
    """
    Mixin that requires the user to be a principal or administration staff of the school.

    This mixin should be used for views that should be accessible to school administrators
    (principals and administration staff) but not to teachers or other users.

    The view using this mixin must have a `school_slug` URL parameter.
    """
    def dispatch(self, request, *args, **kwargs):
        # First check if the user is authenticated
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user has access to this school via SchoolStaff and is principal or admin
        user_profile = request.user.profile
        if user_profile.user_type not in ['principal', 'administration']:
            messages.warning(request, "You do not have permission to access this page.")
            return redirect('core:home')

        school_staff = SchoolStaff.objects.filter(
            staff=user_profile,
            school=self.school,
            is_active=True
        ).first()

        if not school_staff:
            messages.warning(request, "You do not have access to this school.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

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

        # Check if user is the principal of this school via SchoolStaff
        user_profile = request.user.profile
        if user_profile.user_type != 'principal':
            messages.warning(request, "Only principals can access this page.")
            return redirect('core:home')

        school_staff = SchoolStaff.objects.filter(
            staff=user_profile,
            school=self.school,
            is_active=True
        ).first()

        if not school_staff:
            messages.warning(request, "You do not have access to this school.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        return context


class SchoolAccessRequiredMixin:
    """
    Mixin that requires the user to have access to the school.

    This mixin should be used for views that should be accessible to principals,
    administration staff, and teachers of the specific school.

    The view using this mixin must have a `school_slug` URL parameter.
    """
    def dispatch(self, request, *args, **kwargs):
        # First check if the user is authenticated
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user has access to this school via SchoolStaff
        user_profile = request.user.profile
        school_staff = SchoolStaff.objects.filter(
            staff=user_profile,
            school=self.school,
            is_active=True
        ).first()

        if not school_staff:
            messages.warning(request, "You do not have access to this school.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        return context
