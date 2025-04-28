from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from core.models import UserProfile
from academics.models import Year, StandardTeacher, Enrollment
from .models import School, Teacher, Standard, Student


class TeacherListView(LoginRequiredMixin, ListView):
    """
    View for listing teachers in a school
    """
    model = Teacher
    template_name = 'schools/teacher_list.html'
    context_object_name = 'teachers'

    def get_queryset(self):
        # Only show teachers from the principal's school
        if self.request.user.profile.user_type == 'principal' and hasattr(self.request.user, 'administered_schools'):
            school = self.request.user.administered_schools.first()
            if school:
                return Teacher.objects.filter(school=school)
        return Teacher.objects.none()


class TeacherCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating a new teacher
    """
    model = Teacher
    template_name = 'schools/teacher_form.html'
    fields = ['title', 'first_name', 'last_name', 'contact_phone', 'contact_email']
    success_url = reverse_lazy('schools:teacher_list')

    def dispatch(self, request, *args, **kwargs):
        # Check if the user is a principal
        if not request.user.profile.user_type == 'principal':
            messages.error(request, "Only principals can add teachers.")
            return redirect('core:home')

        # Check if the principal has a school
        if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.exists():
            messages.error(request, "You need to register a school first.")
            return redirect('core:register_school')

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Get the principal's school
        school = self.request.user.administered_schools.first()

        # Create the teacher
        teacher = form.save(commit=False)
        teacher.school = school

        # Generate a username from email
        email = form.cleaned_data['contact_email']

        # Create a user account for the teacher
        username = email
        password = "ChangeMe!"  # Default password that must be changed

        # Check if user with this email already exists
        if User.objects.filter(email=email).exists():
            messages.error(self.request, f"A user with the email {email} already exists.")
            return self.form_invalid(form)

        # Create the user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=form.cleaned_data['first_name'],
            last_name=form.cleaned_data['last_name']
        )

        # Update the user profile to be a teacher
        profile = user.profile
        profile.user_type = 'teacher'
        profile.phone_number = form.cleaned_data['contact_phone']
        profile.must_change_password = True  # Force password change on first login
        profile.save()

        # Link the teacher to the user
        teacher.user = user
        teacher.save()

        messages.success(self.request, f"Teacher {teacher} has been added successfully!")
        return redirect(self.success_url)


class StudentListView(LoginRequiredMixin, ListView):
    """
    View for listing students in a school or class
    """
    model = Student
    template_name = 'schools/student_list.html'
    context_object_name = 'students'

    def get_queryset(self):
        # For principals, show all students in their school
        if self.request.user.profile.user_type == 'principal' and hasattr(self.request.user, 'administered_schools'):
            school = self.request.user.administered_schools.first()
            if school:
                return Student.objects.filter(school=school)

        # For teachers, show only students in their class
        elif self.request.user.profile.user_type == 'teacher' and hasattr(self.request.user, 'teacher_profile'):
            teacher = self.request.user.teacher_profile
            # Get current year and standard assignments
            # This would need to be expanded with actual enrollment logic
            return Student.objects.filter(school=teacher.school)

        return Student.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add standards for filtering
        if self.request.user.profile.user_type == 'principal' and hasattr(self.request.user, 'administered_schools'):
            school = self.request.user.administered_schools.first()
            if school:
                context['standards'] = Standard.objects.filter(school=school)
        elif self.request.user.profile.user_type == 'teacher' and hasattr(self.request.user, 'teacher_profile'):
            teacher = self.request.user.teacher_profile
            context['standards'] = Standard.objects.filter(
                standardteacher__teacher=teacher,
                standardteacher__is_active=True
            ).distinct()

        return context


class StandardListView(LoginRequiredMixin, ListView):
    """
    View for listing standards/classes in a school
    """
    model = Standard
    template_name = 'schools/standard_list.html'
    context_object_name = 'standards'

    def get_queryset(self):
        # For principals, show all standards in their school
        if self.request.user.profile.user_type == 'principal' and hasattr(self.request.user, 'administered_schools'):
            school = self.request.user.administered_schools.first()
            if school:
                return Standard.objects.filter(school=school)

        # For teachers, show only their assigned standard
        elif self.request.user.profile.user_type == 'teacher' and hasattr(self.request.user, 'teacher_profile'):
            teacher = self.request.user.teacher_profile
            # Get current year and standard assignments
            # This would need to be expanded with actual enrollment logic
            return Standard.objects.filter(school=teacher.school)

        return Standard.objects.none()


class StandardDetailView(LoginRequiredMixin, DetailView):
    """
    View for showing details of a standard/class
    """
    model = Standard
    template_name = 'schools/standard_detail.html'
    context_object_name = 'standard'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        standard = self.get_object()

        # Get teacher assignments for this standard
        context['teacher_assignments'] = StandardTeacher.objects.filter(
            standard=standard,
            is_active=True
        )

        # Get students enrolled in this standard
        context['enrolled_students'] = Student.objects.filter(
            school=standard.school,
            enrollment__standard=standard,
            enrollment__is_active=True
        ).distinct()

        return context


class TeacherAssignmentCreateView(LoginRequiredMixin, CreateView):
    """
    View for assigning a teacher to a standard/class
    """
    model = StandardTeacher
    template_name = 'schools/teacher_assignment_form.html'
    fields = ['teacher', 'standard']

    def get_success_url(self):
        return reverse_lazy('schools:standard_detail', kwargs={'pk': self.object.standard.pk})

    def dispatch(self, request, *args, **kwargs):
        # Check if the user is a principal
        if not request.user.profile.user_type == 'principal':
            messages.error(request, "Only principals can assign teachers to classes.")
            return redirect('core:home')

        # Check if the principal has a school
        if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.exists():
            messages.error(request, "You need to register a school first.")
            return redirect('core:register_school')

        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # Filter teachers and standards to only those in the principal's school
        school = self.request.user.administered_schools.first()
        if school:
            form.fields['teacher'].queryset = Teacher.objects.filter(school=school, is_active=True)
            form.fields['standard'].queryset = Standard.objects.filter(school=school)

        return form

    def form_valid(self, form):
        assignment = form.save(commit=False)

        # Get the current academic year (or create one if it doesn't exist)
        current_year = Year.objects.filter().order_by('-start_year').first()
        if not current_year:
            # Create a default year if none exists
            from datetime import date
            today = date.today()
            current_year = Year.objects.create(
                start_year=today.year,
                term1_start_date=date(today.year, 1, 1),
                term1_end_date=date(today.year, 4, 30),
                term1_school_days=80,
                term2_start_date=date(today.year, 5, 1),
                term2_end_date=date(today.year, 8, 31),
                term2_school_days=80,
                term3_start_date=date(today.year, 9, 1),
                term3_end_date=date(today.year, 12, 31),
                term3_school_days=80
            )

        assignment.year = current_year
        assignment.save()

        messages.success(self.request, f"{assignment.teacher} has been assigned to {assignment.standard}.")
        return redirect(self.get_success_url())
