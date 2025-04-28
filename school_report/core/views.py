from django.views.generic import TemplateView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpResponseRedirect
from .models import UserProfile
from schools.models import School


class HomeView(TemplateView):
    """Home page view"""
    template_name = 'core/home.html'


class SchoolRegistrationView(LoginRequiredMixin, CreateView):
    """
    View for registering a new school by an authenticated principal
    """
    model = School
    template_name = 'core/school_registration.html'
    fields = ['name', 'address', 'contact_phone', 'contact_email', 'principal_name', 'logo']
    success_url = reverse_lazy('core:home')

    def dispatch(self, request, *args, **kwargs):
        # Check if the user is a principal
        if not request.user.profile.user_type == 'principal':
            messages.error(request, "Only principals can register schools.")
            return redirect('core:home')

        # Check if the principal already has a school
        if hasattr(request.user, 'administered_schools') and request.user.administered_schools.exists():
            messages.error(request, "You already have a registered school.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Create the school
        school = form.save(commit=False)

        # Link the school to the principal
        school.principal_user = self.request.user
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
        return redirect('core:home')
