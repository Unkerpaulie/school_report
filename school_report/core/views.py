from django.views.generic import TemplateView, CreateView, UpdateView, View, RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse_lazy, reverse
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import PasswordChangeView, LoginView
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm
from django.http import HttpResponseRedirect, Http404
from .models import UserProfile
from schools.models import School
from academics.models import SchoolYear, Term, SchoolStaff, StandardTeacher
from core.utils import get_user_session_info, user_can_access_view, clear_teacher_session, get_current_year_and_term
from core.mixins import SchoolAdminRequiredMixin

class HomeView(TemplateView):
    """Home page view"""
    template_name = 'core/home.html'

    def dispatch(self, request, *args, **kwargs):
        # If user is authenticated, use session data for routing
        if request.user.is_authenticated:
            session_info = get_user_session_info(request)

            # Check if user has a school association
            if session_info['user_school_id']:
                # User is associated with a school
                school_slug = session_info['user_school_slug']
                user_role = session_info['user_role']

                # Check if school year is set up
                if not session_info['current_year_id']:
                    # School exists but no academic year - redirect to setup
                    if user_role == 'principal':
                        return redirect('academics:school_year_setup', school_slug=school_slug)
                    else:
                        # Non-principals wait for principal to set up year
                        self.year_setup_required = True
                        self.school_slug = school_slug
                        return super().dispatch(request, *args, **kwargs)

                # School and year are set up - route to appropriate dashboard
                if user_role in ['principal', 'administration']:
                    # Principals and administration go to admin dashboard
                    return redirect('schools:dashboard', school_slug=school_slug)

                elif user_role == 'teacher':
                    # Teachers go to their assigned class detail page
                    teacher_class_id = session_info['teacher_class_id']
                    if teacher_class_id:
                        # Redirect to their class detail page (teacher dashboard)
                        return redirect('schools:standard_detail',
                                      school_slug=school_slug,
                                      pk=teacher_class_id)
                    else:
                        # Teacher not assigned to a class - show message
                        self.teacher_not_assigned = True
                        self.school_slug = school_slug
                        return super().dispatch(request, *args, **kwargs)

            else:
                # User NOT associated with a school
                user_role = session_info['user_role']

                if user_role == 'principal':
                    # Principal NOT associated with a school - redirect to school registration
                    return redirect('core:register_school')
                elif user_role in ['administration', 'teacher']:
                    # Teacher/admin NOT associated with a school - show message to contact principal
                    self.school_registration_required = True
                    self.user_type = user_role
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
            context['school_slug'] = self.school_slug

        if hasattr(self, 'year_setup_required'):
            context['year_setup_required'] = True
            context['school_slug'] = self.school_slug

        return context


class SchoolRegistrationView(LoginRequiredMixin, CreateView):
    """
    View for registering a new school by an authenticated principal
    """
    model = School
    template_name = 'core/school_registration.html'
    fields = ['name', 'address', 'contact_phone', 'contact_email', 'groups_per_standard', 'logo']
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

        # Create a SchoolStaff entry for the principal (no longer tied to academic year)
        SchoolStaff.objects.create(
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
        current_year, current_term, vacation_status = get_current_year_and_term(school=self.school)
        context['current_year'] = current_year
        context['current_term'] = current_term
        context['vacation_status'] = vacation_status
        context['is_on_vacation'] = vacation_status is not None
        context['title_choices'] = UserProfile.TITLE_CHOICES

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
        # Clear teacher session data before logout
        clear_teacher_session(request)

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


class SchoolUpdateView(SchoolAdminRequiredMixin, UpdateView):
    """
    View for updating school information by principals and admin staff
    """
    model = School
    template_name = 'core/school_update.html'
    fields = ['name', 'address', 'contact_phone', 'contact_email', 'logo']  # Removed groups_per_standard
    context_object_name = 'school'

    def get_object(self, queryset=None):
        return self.school

    def get_success_url(self):
        return reverse_lazy('schools:dashboard', kwargs={'school_slug': self.school.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school_slug'] = self.school.slug
        return context

    def form_valid(self, form):
        messages.success(self.request, f"School information for '{self.school.name}' has been updated successfully!")
        return super().form_valid(form)


class CustomLoginView(LoginView):
    """
    Custom login view that handles the "Remember me" checkbox
    and sets appropriate session expiry behavior
    """
    template_name = 'registration/login.html'
    form_class = AuthenticationForm

    def form_valid(self, form):
        """Handle successful login with remember me functionality"""
        # Get the remember me checkbox value
        remember_me = self.request.POST.get('remember', False)

        # Call the parent form_valid method to handle authentication and login
        response = super().form_valid(form)

        # Now configure session expiry based on "Remember me" checkbox
        # This must be done AFTER login is complete
        if remember_me:
            # Remember me is checked: Keep session alive for 30 days
            self.request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days in seconds
        else:
            # Remember me is NOT checked: Session expires when browser closes
            self.request.session.set_expiry(0)  # Expire when browser closes

        # Initialize session activity timestamp for idle timeout
        import time
        self.request.session['last_activity'] = time.time()

        # Force session to be saved with new expiry settings
        self.request.session.modified = True

        return response


class SessionDebugView(View):
    """
    Debug view to check session information
    """
    def get(self, request):
        from django.http import JsonResponse

        session_info = {
            'is_authenticated': request.user.is_authenticated,
            'username': request.user.username if request.user.is_authenticated else None,
            'session_key': request.session.session_key,
            'session_expiry_age': request.session.get_expiry_age(),
            'session_expiry_date': str(request.session.get_expiry_date()),
            'session_data': dict(request.session),
        }

        return JsonResponse(session_info)


def idle_timeout_context(request):
    """
    Context processor to add idle timeout settings to templates
    """
    from django.conf import settings
    return {
        'IDLE_TIMEOUT_MINUTES': getattr(settings, 'IDLE_TIMEOUT_MINUTES', 30),
        'IDLE_TIMEOUT_SECONDS': getattr(settings, 'IDLE_TIMEOUT_SECONDS', 1800),
    }


class GroupManagementView(SchoolAdminRequiredMixin, TemplateView):
    """
    View for managing groups per standard with impact analysis
    """
    template_name = 'core/group_management.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        context['current_groups'] = self.school.groups_per_standard

        # Get impact analysis for different group numbers
        context['impact_analysis'] = self._get_impact_analysis()

        return context

    def _get_impact_analysis(self):
        """
        Analyze the impact of changing groups per standard
        """
        from schools.models import Standard
        from academics.models import StandardEnrollment
        from academics.models import StandardTeacher
        from core.utils import get_current_year_and_term

        current_year, _, _ = get_current_year_and_term(school=self.school)
        current_groups = self.school.groups_per_standard

        analysis = {}

        # Analyze impact for different group numbers (1-5)
        for new_groups in range(1, 6):
            if new_groups == current_groups:
                continue

            impact = {
                'new_groups': new_groups,
                'change_type': 'increase' if new_groups > current_groups else 'decrease',
                'affected_classes': [],
                'affected_teachers': [],
                'affected_students': 0
            }

            if new_groups < current_groups:
                # Decreasing groups - find classes that will be removed
                for standard_code, standard_name in Standard.STANDARD_CHOICES:
                    for group_num in range(new_groups + 1, current_groups + 1):
                        try:
                            standard = Standard.objects.get(
                                school=self.school,
                                name=standard_code,
                                group_number=group_num
                            )

                            # Count students in this class
                            if current_year:
                                student_count = StandardEnrollment.objects.filter(
                                    standard=standard,
                                    year=current_year
                                ).count()
                            else:
                                student_count = 0

                            # Find assigned teacher
                            teacher_assignment = None
                            if current_year:
                                teacher_assignment = StandardTeacher.objects.filter(
                                    standard=standard,
                                    year=current_year,
                                    teacher__isnull=False
                                ).first()

                            impact['affected_classes'].append({
                                'standard': standard,
                                'student_count': student_count,
                                'teacher': teacher_assignment.teacher if teacher_assignment else None
                            })

                            if teacher_assignment and teacher_assignment.teacher:
                                if teacher_assignment.teacher not in impact['affected_teachers']:
                                    impact['affected_teachers'].append(teacher_assignment.teacher)

                            impact['affected_students'] += student_count

                        except Standard.DoesNotExist:
                            continue

            elif new_groups > current_groups:
                # Increasing groups - show new classes that will be created
                for standard_code, standard_name in Standard.STANDARD_CHOICES:
                    for group_num in range(current_groups + 1, new_groups + 1):
                        impact['affected_classes'].append({
                            'standard_name': standard_name,
                            'group_number': group_num,
                            'is_new': True
                        })

            analysis[new_groups] = impact

        return analysis


class GroupChangeConfirmationView(SchoolAdminRequiredMixin, TemplateView):
    """
    View for confirming group changes with detailed impact analysis
    """
    template_name = 'core/group_change_confirmation.html'

    def dispatch(self, request, *args, **kwargs):
        # Call parent dispatch first for permission checking
        response = super().dispatch(request, *args, **kwargs)
        if response:  # If parent returned a redirect, return it
            return response

        # Get the new group count from URL
        self.new_groups = int(kwargs.get('new_groups'))

        # Validate new_groups
        if self.new_groups < 1 or self.new_groups > 5:
            messages.error(request, "Invalid number of groups. Must be between 1 and 5.")
            return redirect('core:group_management', school_slug=self.school_slug)

        return None  # Continue with normal processing

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        context['current_groups'] = self.school.groups_per_standard
        context['new_groups'] = self.new_groups
        context['change_type'] = 'increase' if self.new_groups > self.school.groups_per_standard else 'decrease'

        # Get detailed impact analysis for this specific change
        context['impact'] = self._get_detailed_impact()

        return context

    def _get_detailed_impact(self):
        """
        Get detailed impact analysis for the specific group change
        """
        from schools.models import Standard, StandardEnrollment
        from academics.models import StandardTeacher
        from core.utils import get_current_year_and_term

        current_year, _, _ = get_current_year_and_term(school=self.school)
        current_groups = self.school.groups_per_standard

        impact = {
            'change_type': 'increase' if self.new_groups > current_groups else 'decrease',
            'classes_to_remove': [],
            'classes_to_create': [],
            'teachers_to_unassign': [],
            'total_students_affected': 0
        }

        if self.new_groups < current_groups:
            # Decreasing groups - find classes that will be removed
            for standard_code, standard_name in Standard.STANDARD_CHOICES:
                for group_num in range(self.new_groups + 1, current_groups + 1):
                    try:
                        standard = Standard.objects.get(
                            school=self.school,
                            name=standard_code,
                            group_number=group_num
                        )

                        # Count students in this class
                        student_count = 0
                        if current_year:
                            student_count = StandardEnrollment.objects.filter(
                                standard=standard,
                                year=current_year
                            ).count()

                        # Find assigned teacher
                        teacher_assignment = None
                        if current_year:
                            teacher_assignment = StandardTeacher.objects.filter(
                                standard=standard,
                                year=current_year,
                                teacher__isnull=False
                            ).first()

                        class_info = {
                            'standard': standard,
                            'student_count': student_count,
                            'teacher': teacher_assignment.teacher if teacher_assignment else None
                        }

                        impact['classes_to_remove'].append(class_info)
                        impact['total_students_affected'] += student_count

                        if teacher_assignment and teacher_assignment.teacher:
                            teacher_info = {
                                'teacher': teacher_assignment.teacher,
                                'class_name': standard.get_display_name()
                            }
                            if teacher_info not in impact['teachers_to_unassign']:
                                impact['teachers_to_unassign'].append(teacher_info)

                    except Standard.DoesNotExist:
                        continue

        elif self.new_groups > current_groups:
            # Increasing groups - show new classes that will be created
            for standard_code, standard_name in Standard.STANDARD_CHOICES:
                for group_num in range(current_groups + 1, self.new_groups + 1):
                    impact['classes_to_create'].append({
                        'standard_name': standard_name,
                        'group_number': group_num,
                        'display_name': f"{standard_name} - {group_num}"
                    })

        return impact


class GroupChangeExecuteView(SchoolAdminRequiredMixin, View):
    """
    View for executing group changes
    """

    def dispatch(self, request, *args, **kwargs):
        # Call parent dispatch first for permission checking
        response = super().dispatch(request, *args, **kwargs)
        if response:  # If parent returned a redirect, return it
            return response

        # Get the new group count from URL
        self.new_groups = int(kwargs.get('new_groups'))

        # Validate new_groups
        if self.new_groups < 1 or self.new_groups > 5:
            messages.error(request, "Invalid number of groups. Must be between 1 and 5.")
            return redirect('core:group_management', school_slug=self.school_slug)

        return None  # Continue with normal processing

    def post(self, request, *args, **kwargs):
        """
        Execute the group change
        """
        current_groups = self.school.groups_per_standard

        if self.new_groups == current_groups:
            messages.info(request, "No changes needed - group count is already set to this value.")
            return redirect('core:group_management', school_slug=self.school_slug)

        try:
            if self.new_groups < current_groups:
                # Decreasing groups
                self._decrease_groups(current_groups, self.new_groups)
                messages.success(
                    request,
                    f"Successfully reduced groups from {current_groups} to {self.new_groups}. "
                    f"Affected teachers have been unassigned and students are now unenrolled from removed classes."
                )
            else:
                # Increasing groups
                self._increase_groups(current_groups, self.new_groups)
                messages.success(
                    request,
                    f"Successfully increased groups from {current_groups} to {self.new_groups}. "
                    f"New classes have been created and are ready for teacher assignment."
                )

            # Update the school's groups_per_standard
            self.school.groups_per_standard = self.new_groups
            self.school.save()

        except Exception as e:
            messages.error(request, f"Error updating groups: {str(e)}")

        return redirect('core:group_management', school_slug=self.school_slug)

    def _decrease_groups(self, current_groups, new_groups):
        """
        Handle decreasing the number of groups
        """
        from schools.models import Standard
        from academics.models import StandardTeacher
        from core.utils import get_current_year_and_term
        from django.utils import timezone

        current_year, _, _ = get_current_year_and_term(school=self.school)

        # Remove classes for groups that exceed the new limit
        for standard_code, _ in Standard.STANDARD_CHOICES:
            for group_num in range(new_groups + 1, current_groups + 1):
                try:
                    standard = Standard.objects.get(
                        school=self.school,
                        name=standard_code,
                        group_number=group_num
                    )

                    # Unassign teacher if assigned
                    if current_year:
                        teacher_assignments = StandardTeacher.objects.filter(
                            standard=standard,
                            year=current_year,
                            teacher__isnull=False
                        )

                        for assignment in teacher_assignments:
                            # Create unassignment record (teacher=None)
                            StandardTeacher.objects.create(
                                teacher=None,
                                standard=assignment.standard,
                                year=assignment.year,
                                assigned_date=timezone.now().date(),
                                assigned_by=self.request.user.profile
                            )

                    # Delete the standard (this will cascade to enrollments)
                    standard.delete()

                except Standard.DoesNotExist:
                    continue

    def _increase_groups(self, current_groups, new_groups):
        """
        Handle increasing the number of groups
        """
        from schools.models import Standard

        # Create new classes for additional groups
        for standard_code, _ in Standard.STANDARD_CHOICES:
            for group_num in range(current_groups + 1, new_groups + 1):
                # Check if standard already exists (shouldn't happen, but safety check)
                if not Standard.objects.filter(
                    school=self.school,
                    name=standard_code,
                    group_number=group_num
                ).exists():
                    Standard.objects.create(
                        school=self.school,
                        name=standard_code,
                        group_number=group_num
                    )
