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
from academics.models import SchoolYear, Term, SchoolStaff, StandardTeacher
from academics.views import get_current_school_year_and_term
from core.utils import get_current_year_and_term

class HomeView(TemplateView):
    """Home page view"""
    template_name = 'core/home.html'

    def dispatch(self, request, *args, **kwargs):
        # If user is authenticated, redirect to their appropriate dashboard
        if request.user.is_authenticated:
            user_profile = request.user.profile

            # Check if user is associated with any school via SchoolStaff
            school_staff = SchoolStaff.objects.filter(
                staff=user_profile,
                is_active=True
            ).first()

            if school_staff:
                # User is associated with a school
                school = school_staff.school

                if user_profile.user_type in ['principal', 'administration']:
                    # Principals and administration go to admin dashboard
                    return redirect('schools:dashboard', school_slug=school.slug)

                elif user_profile.user_type == 'teacher':
                    # Teachers should go to their assigned class detail page
                    current_year, current_term, is_on_vacation = get_current_year_and_term(school=school)

                    if current_year:
                        # Check if teacher is assigned to a class
                        teacher_assignment = StandardTeacher.objects.filter(
                            teacher=user_profile,
                            year=current_year
                        ).first()

                        if teacher_assignment:
                            # Redirect to their class detail page (teacher dashboard)
                            return redirect('schools:standard_detail',
                                          school_slug=school.slug,
                                          pk=teacher_assignment.standard.pk)
                        else:
                            # Teacher not assigned to a class - show message
                            self.teacher_not_assigned = True
                            self.school = school
                            return super().dispatch(request, *args, **kwargs)
                    else:
                        # No current year - show message
                        self.no_current_year = True
                        self.school = school
                        return super().dispatch(request, *args, **kwargs)
                else:
                    # User type not recognized - show message to assign role
                    self.assign_role_required = True
                    self.school = school
                    return super().dispatch(request, *args, **kwargs)

            # User is NOT associated with a school
            if user_profile.user_type == 'principal':
                # Principal NOT associated with a school - redirect to school registration
                return redirect('core:register_school')
            elif user_profile.user_type in ['administration', 'teacher']:
                # Teacher/admin NOT associated with a school - show message to contact principal
                self.school_registration_required = True
                self.user_type = user_profile.user_type
                return super().dispatch(request, *args, **kwargs)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Handle different message scenarios
        if hasattr(self, 'school_registration_required'):
            context['school_registration_required'] = True
            context['user_type'] = self.user_type

        if hasattr(self, 'teacher_not_assigned'):
            context['teacher_not_assigned'] = True
            context['school'] = self.school

        if hasattr(self, 'no_current_year'):
            context['no_current_year'] = True
            context['school'] = self.school

        if hasattr(self, 'assign_role_required'):
            context['assign_role_required'] = True
            context['school'] = self.school

        return context


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

        # Check if the principal already has a school via SchoolStaff
        existing_school_staff = SchoolStaff.objects.filter(
            staff=request.user.profile,
            is_active=True
        ).first()

        if existing_school_staff:
            messages.warning(request, "You are already associated with a school.")
            return redirect('schools:dashboard', school_slug=existing_school_staff.school.slug)

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Create the school
        school = form.save(commit=False)

        # Link the school to the principal
        school.principal_user = self.request.user

        school.save()

        # Create a SchoolStaff entry for the principal
        # First, we need to get or create the current school year
        from academics.models import SchoolYear, Term
        current_year = SchoolYear.objects.filter(school=school).first()
        if not current_year:
            # Create a default school year with terms if none exists
            import datetime
            current_date = datetime.date.today()
            current_year_num = current_date.year

            # Create the school year
            current_year = SchoolYear.objects.create(
                school=school,
                start_year=current_year_num
            )

            # Create default terms (Caribbean school year typically runs Sept-July)
            # Term 1: September - December
            # Term 2: January - April
            # Term 3: May - July
            terms_data = [
                {
                    'term_number': 1,
                    'start_date': datetime.date(current_year_num, 9, 1),
                    'end_date': datetime.date(current_year_num, 12, 15),
                    'school_days': 70
                },
                {
                    'term_number': 2,
                    'start_date': datetime.date(current_year_num + 1, 1, 8),
                    'end_date': datetime.date(current_year_num + 1, 4, 12),
                    'school_days': 65
                },
                {
                    'term_number': 3,
                    'start_date': datetime.date(current_year_num + 1, 4, 22),
                    'end_date': datetime.date(current_year_num + 1, 7, 5),
                    'school_days': 55
                }
            ]

            # Create the terms
            for term_data in terms_data:
                Term.objects.create(
                    year=current_year,
                    term_number=term_data['term_number'],
                    start_date=term_data['start_date'],
                    end_date=term_data['end_date'],
                    school_days=term_data['school_days']
                )

        # Create SchoolStaff entry for the principal
        SchoolStaff.objects.create(
            year=current_year,
            school=school,
            staff=self.request.user.profile,
            position='Principal',
            is_active=True
        )

        messages.success(self.request, f"School '{school.name}' has been registered successfully!")
        return redirect(self.success_url)


class ProfileView(LoginRequiredMixin, UpdateView):
    """
    View for updating user profile
    """
    model = UserProfile
    template_name = 'core/profile.html'
    fields = ['phone_number']

    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug and check access
        school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=school_slug)

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

    def get_success_url(self):
        return reverse('schools:profile', kwargs={'school_slug': self.school.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school.slug

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
        user_profile = user.profile

        # Check if user is associated with any school via SchoolStaff
        school_staff = SchoolStaff.objects.filter(
            staff=user_profile,
            is_active=True
        ).first()

        if school_staff:
            # User is associated with a school - redirect to school dashboard
            school = school_staff.school
            return reverse('schools:dashboard', kwargs={'school_slug': school.slug})

        # If user doesn't have a school, redirect to home
        return reverse('core:home')
