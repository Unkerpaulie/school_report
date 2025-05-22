from django.views.generic import TemplateView, CreateView, UpdateView, View, RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse_lazy, reverse
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpResponseRedirect, Http404
from .models import UserProfile
from schools.models import School
from academics.models import SchoolYear, Term
from academics.views import get_current_school_year_and_term

class HomeView(TemplateView):
    """Home page view"""
    template_name = 'core/home.html'

    def dispatch(self, request, *args, **kwargs):
        # If user is authenticated, redirect to their school dashboard
        if request.user.is_authenticated:
            # Check if user is a principal with a school
            if request.user.profile.user_type == 'principal' and hasattr(request.user, 'administered_schools'):
                school = request.user.administered_schools.first()
                if school:
                    return redirect('schools:dashboard', school_slug=school.slug)

            # Check if user is a teacher with a school
            elif request.user.profile.user_type == 'teacher' and hasattr(request.user, 'teacher_profile'):
                school = request.user.teacher_profile.school
                if school:
                    return redirect('schools:dashboard', school_slug=school.slug)

            # Check if user is administration staff with a school
            elif request.user.profile.user_type == 'administration' and hasattr(request.user, 'admin_profile'):
                school = request.user.admin_profile.school
                if school:
                    return redirect('schools:dashboard', school_slug=school.slug)

        return super().dispatch(request, *args, **kwargs)


class SchoolRegistrationView(LoginRequiredMixin, CreateView):
    """
    View for registering a new school by an authenticated principal
    """
    model = School
    template_name = 'core/school_registration.html'
    fields = ['name', 'address', 'contact_phone', 'contact_email', 'logo']
    success_url = reverse_lazy('core:home')

    def dispatch(self, request, *args, **kwargs):
        # Check if the user is a principal
        if not request.user.profile.user_type == 'principal':
            messages.warning(request, "Only principals can register schools.")
            return redirect('core:home')

        # Check if the principal already has a school
        if hasattr(request.user, 'administered_schools') and request.user.administered_schools.exists():
            messages.warning(request, "You already have a registered school.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Create the school
        school = form.save(commit=False)

        # Link the school to the principal
        school.principal_user = self.request.user

        # Set the principal_name from the user's profile
        principal_name = self.request.user.get_full_name()
        if principal_name:
            school.principal_name = principal_name

        school.save()

        messages.success(self.request, f"School '{school.name}' has been registered successfully!")
        return redirect(self.success_url)


class ProfileView(LoginRequiredMixin, UpdateView):
    """
    View for updating user profile
    """
    model = UserProfile
    template_name = 'core/profile.html'
    fields = ['phone_number']
    success_url = reverse_lazy('core:profile')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_slug = self.kwargs.get('school_slug')
        school = get_object_or_404(School, slug=school_slug)
        context['school'] = school

        # Get current school year and term
        current_year_term = get_current_school_year_and_term(self.request)
        context['current_year'] = current_year_term['current_year']
        context['current_term'] = current_year_term['current_term']
        context['is_on_vacation'] = current_year_term['is_on_vacation']

        return context
    def get_object(self):
        return self.request.user.profile

    def form_valid(self, form):
        # Update the user model fields
        user = self.request.user
        user.first_name = self.request.POST.get('first_name')
        user.last_name = self.request.POST.get('last_name')
        user.email = self.request.POST.get('email')
        user.save()

        messages.success(self.request, "Your profile has been updated successfully!")
        return super().form_valid(form)


class CustomPasswordChangeView(PasswordChangeView):
    """
    Custom password change view that updates the must_change_password flag
    """
    template_name = 'registration/password_change_form.html'
    form_class = PasswordChangeForm
    success_url = reverse_lazy('password_change_done')

    def form_valid(self, form):
        # Call the parent class's form_valid method
        response = super().form_valid(form)

        # Update the user profile to indicate password has been changed
        if hasattr(self.request.user, 'profile'):
            profile = self.request.user.profile
            if profile.must_change_password:
                profile.must_change_password = False
                profile.save()
                messages.success(self.request, "Your password has been changed successfully.")

        return response


class CustomLogoutView(View):
    """
    Custom logout view that uses POST method for security
    """
    def get(self, request):
        # For GET requests, show a confirmation page
        return redirect('core:home')

    def post(self, request):
        # For POST requests, log the user out
        logout(request)
        messages.success(request, "You have been logged out successfully.")
        # Redirect to the home page (not a school-specific URL)
        return redirect('core:home')





class SchoolRedirectView(LoginRequiredMixin, RedirectView):
    """
    Redirects users to their school dashboard
    """
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user

        # If user is a principal, redirect to their school
        if user.profile.user_type == 'principal' and hasattr(user, 'administered_schools'):
            school = user.administered_schools.first()
            if school:
                return reverse('schools:dashboard', kwargs={'school_slug': school.slug})

        # If user is a teacher, redirect to their assigned school
        elif user.profile.user_type == 'teacher' and hasattr(user, 'teacher_profile'):
            school = user.teacher_profile.school
            if school:
                return reverse('schools:dashboard', kwargs={'school_slug': school.slug})

        # If user is administration staff, redirect to their assigned school
        elif user.profile.user_type == 'administration' and hasattr(user, 'admin_profile'):
            school = user.admin_profile.school
            if school:
                return reverse('schools:dashboard', kwargs={'school_slug': school.slug})

        # If user doesn't have a school, redirect to home
        return reverse('core:home')
