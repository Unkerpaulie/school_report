from django.views.generic import TemplateView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import login
from .models import UserProfile
from schools.models import School


class HomeView(TemplateView):
    """Home page view"""
    template_name = 'core/home.html'


class SchoolRegistrationView(CreateView):
    """
    View for registering a new school and principal user
    """
    model = School
    template_name = 'core/school_registration.html'
    fields = ['name', 'address', 'contact_phone', 'contact_email', 'principal_name', 'logo']
    success_url = reverse_lazy('core:home')

    def form_valid(self, form):
        # Create the school
        school = form.save(commit=False)

        # Get user data from the form
        email = self.request.POST.get('email')
        password = self.request.POST.get('password')

        # Create the user
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=self.request.POST.get('first_name', ''),
            last_name=self.request.POST.get('last_name', '')
        )

        # Update the user profile to be a principal
        profile = user.profile
        profile.user_type = 'principal'
        profile.phone_number = school.contact_phone
        profile.save()

        # Link the school to the principal
        school.principal_user = user
        school.save()

        # Log the user in
        login(self.request, user)

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
