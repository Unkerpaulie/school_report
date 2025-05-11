from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse_lazy, reverse
from django import forms
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
from django.core.validators import FileExtensionValidator
from core.models import UserProfile
from academics.models import Year, StandardTeacher, Enrollment
from .models import School, Teacher, Standard, Student, AdministrationStaff
import csv
from datetime import datetime


class StaffListView(LoginRequiredMixin, ListView):
    """
    View for listing all staff (teachers and administration) in a school
    """
    model = Teacher
    template_name = 'schools/staff_list.html'
    context_object_name = 'staff_members'

    def get_queryset(self):
        # This method is overridden below
        pass

    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=self.school.pk).exists():
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'teacher':
            # Teachers should only access their assigned school
            if not hasattr(request.user, 'teacher_profile') or request.user.teacher_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Get teachers from this school
        teachers = Teacher.objects.filter(school=self.school)

        # Get administration staff from this school
        admin_staff = AdministrationStaff.objects.filter(school=self.school)

        # Create a list to hold all staff members with their type
        staff_list = []

        # Get the current academic year
        current_year = Year.objects.filter(
            term1_start_date__lte=self.request.user.date_joined,
            term3_end_date__gte=self.request.user.date_joined
        ).first()

        # Get all active teacher assignments for the current year
        teacher_assignments = {}
        if current_year:
            assignments = StandardTeacher.objects.filter(
                year=current_year,
                is_active=True,
                teacher__school=self.school
            ).select_related('standard', 'teacher')

            # Create a dictionary of teacher_id -> standard for quick lookup
            for assignment in assignments:
                teacher_assignments[assignment.teacher_id] = {
                    'standard': assignment.standard,
                    'assignment_id': assignment.id
                }

        # Add teachers with their type and assignment info
        for teacher in teachers:
            # Check if this teacher has an assignment
            assignment_info = teacher_assignments.get(teacher.id)
            assigned_standard = assignment_info['standard'] if assignment_info else None
            assignment_id = assignment_info['assignment_id'] if assignment_info else None

            staff_list.append({
                'id': teacher.id,
                'name': str(teacher),
                'email': teacher.contact_email,
                'phone': teacher.contact_phone,
                'type': 'Teacher',
                'is_teacher': True,
                'is_active': teacher.is_active,
                'assigned_standard': assigned_standard,
                'assignment_id': assignment_id,
                'obj': teacher
            })

        # Add administration staff with their type
        for admin in admin_staff:
            staff_list.append({
                'id': admin.id,
                'name': str(admin),
                'email': admin.contact_email,
                'phone': admin.contact_phone,
                'type': f'Administration ({admin.position})',
                'is_teacher': False,
                'is_active': admin.is_active,
                'assigned_standard': None,
                'obj': admin
            })

        # Sort the combined list by name
        staff_list.sort(key=lambda x: x['name'])

        return staff_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        return context


class TeacherCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating a new teacher
    """
    model = Teacher
    template_name = 'schools/teacher_form.html'
    fields = ['title', 'first_name', 'last_name', 'contact_phone', 'contact_email']

    # Add username field to the form
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Add username field
        form.fields['username'] = forms.CharField(
            max_length=150,
            help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        )
        return form

    def get_success_url(self):
        return reverse_lazy('schools:staff_list', kwargs={'school_slug': self.school_slug})

    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=self.school.pk).exists():
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        else:
            messages.warning(request, "Only principals and administration can add staff.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        return context

    def form_valid(self, form):
        # Create the teacher
        teacher = form.save(commit=False)
        teacher.school = self.school

        # Get username and email from form
        username = form.cleaned_data['username']
        email = form.cleaned_data['contact_email']
        password = "ChangeMe!"  # Default password that must be changed

        # Check if user with this username already exists
        if User.objects.filter(username=username).exists():
            messages.warning(self.request, f"A user with the username '{username}' already exists.")
            return self.form_invalid(form)

        # Check if user with this email already exists
        if User.objects.filter(email=email).exists():
            messages.warning(self.request, f"A user with the email '{email}' already exists.")
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
        return redirect(self.get_success_url())


class StudentListView(LoginRequiredMixin, ListView):
    """
    View for listing students in a school or class
    """
    model = Student
    template_name = 'schools/student_list.html'
    context_object_name = 'students'

    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=self.school.pk).exists():
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'teacher':
            # Teachers should only access their assigned school
            if not hasattr(request.user, 'teacher_profile') or request.user.teacher_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # For principals and administration, show all students in the school
        if self.request.user.profile.user_type in ['principal', 'administration']:
            return Student.objects.filter(school=self.school)

        # For teachers, show only students in their class
        elif self.request.user.profile.user_type == 'teacher':
            teacher = self.request.user.teacher_profile
            # Get current year and standard assignments
            # This would need to be expanded with actual enrollment logic
            return Student.objects.filter(
                school=self.school,
                enrollment__standard__standardteacher__teacher=teacher,
                enrollment__standard__standardteacher__is_active=True
            ).distinct()

        return Student.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add school and school_slug to context
        context['school'] = self.school
        context['school_slug'] = self.school_slug

        # Add standards for filtering
        if self.request.user.profile.user_type in ['principal', 'administration']:
            context['standards'] = Standard.objects.filter(school=self.school)
        elif self.request.user.profile.user_type == 'teacher':
            teacher = self.request.user.teacher_profile
            context['standards'] = Standard.objects.filter(
                school=self.school,
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

    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=self.school.pk).exists():
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'teacher':
            # Teachers should only access their assigned school
            if not hasattr(request.user, 'teacher_profile') or request.user.teacher_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # For principals and administration, show all standards in the school
        if self.request.user.profile.user_type in ['principal', 'administration']:
            return Standard.objects.filter(school=self.school).prefetch_related(
                'teacher_assignments__teacher',
                'student_enrollments__student'
            )

        # For teachers, show only their assigned standard
        elif self.request.user.profile.user_type == 'teacher':
            teacher = self.request.user.teacher_profile
            return Standard.objects.filter(
                school=self.school,
                teacher_assignments__teacher=teacher,
                teacher_assignments__is_active=True
            ).prefetch_related(
                'teacher_assignments__teacher',
                'student_enrollments__student'
            ).distinct()

        return Standard.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        return context


class StandardDetailView(LoginRequiredMixin, DetailView):
    """
    View for showing details of a standard/class
    """
    model = Standard
    template_name = 'schools/standard_detail.html'
    context_object_name = 'standard'

    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=self.school.pk).exists():
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'teacher':
            # Teachers should only access their assigned school
            if not hasattr(request.user, 'teacher_profile') or request.user.teacher_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        # Get the standard by ID and ensure it belongs to the correct school
        standard = super().get_object(queryset)
        if standard.school != self.school:
            raise Http404("Standard not found in this school")
        return standard

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        standard = self.get_object()

        # Add school and school_slug to context
        context['school'] = self.school
        context['school_slug'] = self.school_slug

        # Get teacher assignments for this standard
        context['teacher_assignments'] = StandardTeacher.objects.filter(
            standard=standard,
            is_active=True
        )

        # Get students enrolled in this standard
        context['enrolled_students'] = Student.objects.filter(
            school=standard.school,
            standard_enrollments__standard=standard,
            standard_enrollments__is_active=True
        ).distinct()

        return context


class TeacherAssignmentCreateView(LoginRequiredMixin, CreateView):
    """
    View for assigning a teacher to a standard/class
    """
    model = StandardTeacher
    template_name = 'schools/teacher_assignment_form.html'
    fields = ['standard']  # Only need to select the standard

    def get_success_url(self):
        return reverse_lazy('schools:staff_list', kwargs={'school_slug': self.school_slug})

    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)
        self.teacher_id = kwargs.get('pk')

        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=self.school.pk).exists():
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        else:
            messages.warning(request, "Only principals and administration can assign teachers.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        teacher = get_object_or_404(Teacher, pk=self.teacher_id)

        # Get the current academic year
        current_year = Year.objects.filter(
            term1_start_date__lte=self.request.user.date_joined,
            term3_end_date__gte=self.request.user.date_joined
        ).first()

        if not current_year:
            # If no current year, show no standards
            form.fields['standard'].queryset = Standard.objects.none()
            messages.warning(self.request, "No active academic year found. Please set up the academic year first.")
            return form

        # Check if the teacher is already assigned to a class
        existing_assignment = StandardTeacher.objects.filter(
            teacher=teacher,
            year=current_year,
            is_active=True
        ).first()

        if existing_assignment:
            # If teacher is already assigned, show no standards
            form.fields['standard'].queryset = Standard.objects.none()
            messages.warning(self.request, f"This teacher is already assigned to {existing_assignment.standard}.")
            return form

        # Filter standards to only show those from the current school
        # and exclude standards that already have a teacher assigned
        assigned_standards = StandardTeacher.objects.filter(
            year=current_year,
            is_active=True
        ).values_list('standard_id', flat=True)

        available_standards = Standard.objects.filter(
            school=self.school
        ).exclude(
            id__in=assigned_standards
        )

        form.fields['standard'].queryset = available_standards

        if not available_standards.exists():
            messages.warning(self.request, "There are no available classes for assignment. All classes already have teachers assigned.")

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        context['teacher'] = get_object_or_404(Teacher, pk=self.teacher_id)
        return context

    def form_valid(self, form):
        # Get the teacher from the URL parameter
        teacher = get_object_or_404(Teacher, pk=self.teacher_id)

        # Verify teacher belongs to this school
        if teacher.school != self.school:
            messages.warning(self.request, "This teacher does not belong to this school.")
            return self.form_invalid(form)

        # Set the current academic year
        current_year = Year.objects.filter(
            term1_start_date__lte=self.request.user.date_joined,
            term3_end_date__gte=self.request.user.date_joined
        ).first()

        if not current_year:
            messages.warning(self.request, "No active academic year found.")
            return self.form_invalid(form)

        # Get the selected standard
        standard = form.cleaned_data['standard']

        # Verify standard belongs to this school
        if standard.school != self.school:
            messages.warning(self.request, "This class does not belong to this school.")
            return self.form_invalid(form)

        # Check if the teacher is already assigned to a class
        existing_teacher_assignment = StandardTeacher.objects.filter(
            teacher=teacher,
            year=current_year,
            is_active=True
        ).first()

        if existing_teacher_assignment:
            messages.warning(self.request, f"This teacher is already assigned to {existing_teacher_assignment.standard}.")
            return self.form_invalid(form)

        # Check if the class already has a teacher assigned
        existing_class_assignment = StandardTeacher.objects.filter(
            standard=standard,
            year=current_year,
            is_active=True
        ).first()

        if existing_class_assignment:
            messages.warning(self.request, f"This class already has {existing_class_assignment.teacher} assigned to it.")
            return self.form_invalid(form)

        # Create the assignment
        assignment = form.save(commit=False)
        assignment.year = current_year
        assignment.teacher = teacher
        assignment.is_active = True
        assignment.save()

        messages.success(self.request, f"Teacher {teacher} has been assigned to {standard} successfully!")
        return redirect(self.get_success_url())


class TeacherUnassignView(LoginRequiredMixin, View):
    """
    View for unassigning a teacher from a standard/class
    """
    def get(self, request, *args, **kwargs):
        # Get the school by slug
        school_slug = kwargs.get('school_slug')
        school = get_object_or_404(School, slug=school_slug)
        assignment_id = kwargs.get('assignment_id')

        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=school.pk).exists():
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        else:
            messages.warning(request, "Only principals and administration can unassign teachers.")
            return redirect('core:home')

        # Get the assignment
        assignment = get_object_or_404(StandardTeacher, pk=assignment_id)

        # Verify the assignment belongs to a teacher in this school
        if assignment.teacher.school != school:
            messages.warning(request, "This assignment does not belong to a teacher in this school.")
            return redirect('schools:staff_list', school_slug=school_slug)

        # Show confirmation page
        return render(request, 'schools/teacher_unassign_confirm.html', {
            'school': school,
            'school_slug': school_slug,
            'assignment': assignment,
            'teacher': assignment.teacher,
            'standard': assignment.standard
        })

    def post(self, request, *args, **kwargs):
        # Get the school by slug
        school_slug = kwargs.get('school_slug')
        school = get_object_or_404(School, slug=school_slug)
        assignment_id = kwargs.get('assignment_id')

        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=school.pk).exists():
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        else:
            messages.warning(request, "Only principals and administration can unassign teachers.")
            return redirect('core:home')

        # Get the assignment
        assignment = get_object_or_404(StandardTeacher, pk=assignment_id)

        # Verify the assignment belongs to a teacher in this school
        if assignment.teacher.school != school:
            messages.warning(request, "This assignment does not belong to a teacher in this school.")
            return redirect('schools:staff_list', school_slug=school_slug)

        # Store teacher and standard for the success message
        teacher = assignment.teacher
        standard = assignment.standard

        # Deactivate the assignment (don't delete it to preserve history)
        assignment.is_active = False
        assignment.save()

        messages.success(request, f"Teacher {teacher} has been unassigned from {standard} successfully!")
        return redirect('schools:staff_list', school_slug=school_slug)


class StudentCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating a new student
    """
    model = Student
    template_name = 'schools/student_form.html'
    fields = ['first_name', 'last_name', 'date_of_birth', 'parent_name', 'contact_phone']

    def get_success_url(self):
        return reverse_lazy('schools:student_list', kwargs={'school_slug': self.school_slug})

    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=self.school.pk).exists():
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'teacher':
            # Teachers should only access their assigned school
            if not hasattr(request.user, 'teacher_profile') or request.user.teacher_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        else:
            messages.warning(request, "You do not have permission to add students.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Add standard field for enrollment
        from academics.models import Year, Standard

        # Add academic year field
        form.fields['academic_year'] = forms.ModelChoiceField(
            queryset=Year.objects.all().order_by('-start_year'),
            required=True,
            label="Academic Year",
            help_text="Select the academic year for enrollment"
        )

        # Add standard field
        form.fields['standard'] = forms.ModelChoiceField(
            queryset=Standard.objects.filter(school=self.school),
            required=True,
            label="Class",
            help_text="Select the class to enroll the student in"
        )

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        return context

    def form_valid(self, form):
        # Create the student
        student = form.save(commit=False)
        student.school = self.school
        student.is_active = True
        student.save()

        # Enroll the student if a standard was selected
        if 'standard' in form.cleaned_data and form.cleaned_data['standard'] and 'academic_year' in form.cleaned_data and form.cleaned_data['academic_year']:
            from academics.models import Enrollment
            standard = form.cleaned_data['standard']
            academic_year = form.cleaned_data['academic_year']

            # Create enrollment
            enrollment = Enrollment.objects.create(
                year=academic_year,
                standard=standard,
                student=student,
                is_active=True
            )

            messages.success(self.request, f"Student {student} has been added and enrolled in {standard.get_name_display()} for the {academic_year} academic year.")
        else:
            messages.success(self.request, f"Student {student} has been added successfully!")

        return redirect(self.get_success_url())


class StudentUpdateView(LoginRequiredMixin, UpdateView):
    """
    View for updating an existing student
    """
    model = Student
    template_name = 'schools/student_form.html'
    fields = ['first_name', 'last_name', 'date_of_birth', 'parent_name', 'contact_phone', 'is_active']
    context_object_name = 'student'

    def get_success_url(self):
        return reverse_lazy('schools:student_list', kwargs={'school_slug': self.school_slug})

    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=self.school.pk).exists():
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'teacher':
            # Teachers should only access their assigned school
            if not hasattr(request.user, 'teacher_profile') or request.user.teacher_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        else:
            messages.warning(request, "You do not have permission to edit students.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        # Get the student by ID and ensure it belongs to the correct school
        student = super().get_object(queryset)
        if student.school != self.school:
            raise Http404("Student not found in this school")
        return student

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        context['is_update'] = True

        # Get current enrollment
        from academics.models import Enrollment, Year

        # Get current academic year
        current_year = Year.objects.filter(
            term1_start_date__lte=self.request.user.date_joined,
            term3_end_date__gte=self.request.user.date_joined
        ).first()

        if current_year:
            current_enrollment = Enrollment.objects.filter(
                student=self.object,
                year=current_year,
                is_active=True
            ).first()

            if current_enrollment:
                context['current_enrollment'] = current_enrollment

        return context

    def form_valid(self, form):
        # Update the student
        student = form.save()
        messages.success(self.request, f"Student {student} has been updated successfully!")
        return redirect(self.get_success_url())


class StudentDetailView(LoginRequiredMixin, DetailView):
    """
    View for showing details of a student
    """
    model = Student
    template_name = 'schools/student_detail.html'
    context_object_name = 'student'

    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=self.school.pk).exists():
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'teacher':
            # Teachers should only access their assigned school
            if not hasattr(request.user, 'teacher_profile') or request.user.teacher_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        # Get the student by ID and ensure it belongs to the correct school
        student = super().get_object(queryset)
        if student.school != self.school:
            raise Http404("Student not found in this school")
        return student

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug

        # Get enrollment history
        from academics.models import Enrollment

        enrollments = Enrollment.objects.filter(
            student=self.object
        ).select_related('year', 'standard').order_by('-year__start_year')

        context['enrollments'] = enrollments

        # Get current enrollment
        current_enrollment = enrollments.filter(is_active=True).first()
        if current_enrollment:
            context['current_enrollment'] = current_enrollment

        return context


class EnrollmentCreateView(LoginRequiredMixin, CreateView):
    """
    View for enrolling a student in a class
    """
    model = Enrollment
    template_name = 'schools/enrollment_form.html'
    fields = ['standard']

    def get_success_url(self):
        return reverse_lazy('schools:student_detail', kwargs={
            'school_slug': self.school_slug,
            'pk': self.student.pk
        })

    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Get the student
        self.student_id = kwargs.get('student_id')
        self.student = get_object_or_404(Student, pk=self.student_id, school=self.school)

        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=self.school.pk).exists():
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        else:
            messages.warning(request, "Only principals and administration can enroll students.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # Add academic year field
        from academics.models import Year

        form.fields['academic_year'] = forms.ModelChoiceField(
            queryset=Year.objects.all().order_by('-start_year'),
            required=True,
            label="Academic Year",
            help_text="Select the academic year for enrollment"
        )

        # Filter standards to only show those from the current school
        form.fields['standard'].queryset = Standard.objects.filter(school=self.school)

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        context['student'] = self.student
        return context

    def form_valid(self, form):
        academic_year = form.cleaned_data['academic_year']

        # Deactivate any existing enrollments for this student in the selected year
        existing_enrollments = Enrollment.objects.filter(
            student=self.student,
            year=academic_year,
            is_active=True
        )

        for enrollment in existing_enrollments:
            enrollment.is_active = False
            enrollment.save()

        # Create the new enrollment
        enrollment = form.save(commit=False)
        enrollment.year = academic_year
        enrollment.student = self.student
        enrollment.is_active = True
        enrollment.save()

        messages.success(self.request, f"Student {self.student} has been enrolled in {enrollment.standard.get_name_display()} for the {academic_year} academic year.")
        return redirect(self.get_success_url())


class StudentBulkUploadForm(forms.Form):
    """
    Form for uploading a CSV file of students
    """
    file = forms.FileField(
        label='Select a CSV file',
        help_text='Max. 5 megabytes',
        validators=[FileExtensionValidator(allowed_extensions=['csv'])]
    )
    standard = forms.ModelChoiceField(
        queryset=Standard.objects.none(),  # Will be populated in the view
        label='Class',
        help_text='Select the class to enroll these students in'
    )
    academic_year = forms.ModelChoiceField(
        queryset=Year.objects.all().order_by('-start_year'),
        label='Academic Year',
        help_text='Select the academic year for enrollment'
    )


class StudentBulkUploadView(LoginRequiredMixin, FormView):
    """
    View for bulk uploading students from a CSV file
    """
    template_name = 'schools/student_bulk_upload.html'
    form_class = StudentBulkUploadForm
    success_url = None  # Will be set dynamically

    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=self.school.pk).exists():
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        else:
            messages.warning(request, "Only principals and administration can upload students.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Populate the standard choices with classes from this school
        form.fields['standard'].queryset = Standard.objects.filter(school=self.school)
        return form

    def get_success_url(self):
        return reverse_lazy('schools:student_list', kwargs={'school_slug': self.school_slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug

        # Clear any previous import errors and duplicates when displaying the form
        if 'import_errors' in self.request.session:
            del self.request.session['import_errors']

        if 'duplicate_records' in self.request.session:
            del self.request.session['duplicate_records']

        return context

    def form_valid(self, form):
        # Get the uploaded file, selected class and academic year
        csv_file = form.cleaned_data['file']
        standard = form.cleaned_data['standard']
        academic_year = form.cleaned_data['academic_year']

        # Check if it's a CSV file
        if not csv_file.name.endswith('.csv'):
            messages.warning(self.request, "Please upload a CSV file.")
            return self.form_invalid(form)

        # Process the file
        decoded_file = csv_file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)

        # Convert to list to ensure we can iterate multiple times if needed
        rows = list(reader)

        # Check if file is empty or has no data rows
        if not rows or len(rows) == 1:
            messages.warning(self.request, "The uploaded CSV file is empty or has no data rows.")
            return self.form_invalid(form)

        # Track results
        success_count = 0
        error_records = []
        duplicate_records = []

        # Process each row
        from django.db import transaction
        for row_num, row in enumerate(rows, start=2):  # Start at 2 to account for header row
            try:
                # Validate required fields
                required_fields = ['first_name', 'last_name', 'date_of_birth', 'parent_name']
                for field in required_fields:
                    if not row.get(field) or row.get(field).strip() == '':
                        raise ValueError(f"Missing required field: {field}")

                # Validate date format - try multiple formats
                date_str = row['date_of_birth'].strip()
                date_of_birth = None

                # Try different date formats
                date_formats = ['%Y-%m-%d', '%d/%m/%Y']
                for date_format in date_formats:
                    try:
                        date_of_birth = datetime.strptime(date_str, date_format).date()
                        break  # Exit the loop if successful
                    except ValueError:
                        continue  # Try the next format

                # If all formats failed
                if date_of_birth is None:
                    raise ValueError("Invalid date format. Accepted formats: YYYY-MM-DD or DD/MM/YYYY.")

                # Check for duplicate students
                first_name = row['first_name'].strip()
                last_name = row['last_name'].strip()
                parent_name = row['parent_name'].strip()

                # Check if a student with the same details already exists
                existing_student = Student.objects.filter(
                    school=self.school,
                    first_name__iexact=first_name,
                    last_name__iexact=last_name,
                    date_of_birth=date_of_birth,
                    parent_name__iexact=parent_name
                ).first()

                if existing_student:
                    # Add to duplicate records
                    duplicate_records.append({
                        'row': row_num,
                        'data': row,
                        'existing_student': existing_student
                    })
                    continue  # Skip to the next row

                # Create the student with transaction
                with transaction.atomic():
                    # Create the student
                    student = Student.objects.create(
                        school=self.school,
                        first_name=first_name,
                        last_name=last_name,
                        date_of_birth=date_of_birth,
                        parent_name=parent_name,
                        contact_phone=row.get('contact_phone', '').strip(),
                        is_active=True
                    )

                    # Enroll the student in the selected class for the selected academic year
                    Enrollment.objects.create(
                        year=academic_year,
                        standard=standard,
                        student=student,
                        is_active=True
                    )

                # Increment success count
                success_count += 1

            except Exception as e:
                # Add to error records
                error_records.append({
                    'row': row_num,
                    'data': row,
                    'error': str(e)
                })
                # Continue processing the next row

        # Display results
        if success_count > 0:
            messages.success(
                self.request,
                f"Successfully imported {success_count} students into {standard.get_name_display()} for the {academic_year} academic year."
            )

        # Handle error records
        if error_records:
            # Store error records in session for display
            self.request.session['import_errors'] = error_records
            err_table = """
                <table class="table"><thead><tr>
                    <th scope="col">first_name</th>
                    <th scope="col">last_name</th>
                    <th scope="col">date_of_birth</th>
                    <th scope="col">parent_name</th>
                    <th scope="col">contact_phone</th>
                    <th scope="col"><i class="bi bi-exclamation-circle text-danger"></i><span class="text-danger">Error</span></th>
                </tr></thead><tbody>"""
            for error in error_records:
                err_table += f"""
                <tr>
                    <td>{error['data']['first_name']}</td>
                    <td>{error['data']['last_name']}</td>
                    <td>{error['data']['date_of_birth']}</td>
                    <td>{error['data']['parent_name']}</td>
                    <td>{error['data'].get('contact_phone', '')}</td>
                    <td class="text-danger">{error['error']}</td>
                </tr>"""
            err_table += "</tbody></table>"
            from django.utils.safestring import mark_safe
            messages.warning(
                self.request,
                mark_safe(f"Encountered {len(error_records)} errors during import. "
                f"<button type='button' class='btn btn-link p-0 m-0 align-baseline' "
                f"data-bs-toggle='collapse' data-bs-target='#csv-errors' aria-expanded='false'>View details</button>"
                f'<div class="collapse" id="csv-errors">'
                f'<div class="card card-body">'
                f'{err_table}'
                f'</div></div>'
                )
            )

        # Handle duplicate records
        if duplicate_records:
            # Store duplicate records in session for display
            self.request.session['duplicate_records'] = duplicate_records
            dup_table = """
                <table class="table"><thead><tr>
                    <th scope="col">first_name</th>
                    <th scope="col">last_name</th>
                    <th scope="col">date_of_birth</th>
                    <th scope="col">parent_name</th>
                    <th scope="col">contact_phone</th>
                    <th scope="col"><i class="bi bi-exclamation-triangle text-warning"></i><span class="text-warning">Existing Student</span></th>
                </tr></thead><tbody>"""
            for duplicate in duplicate_records:
                existing = duplicate['existing_student']
                dup_table += f"""
                <tr>
                    <td>{duplicate['data']['first_name']}</td>
                    <td>{duplicate['data']['last_name']}</td>
                    <td>{duplicate['data']['date_of_birth']}</td>
                    <td>{duplicate['data']['parent_name']}</td>
                    <td>{duplicate['data'].get('contact_phone', '')}</td>
                    <td class="text-warning">
                        Student already exists (ID: {existing.id}) -
                        <a href="{reverse('schools:student_detail', kwargs={'school_slug': self.school_slug, 'pk': existing.id})}">View</a>
                    </td>
                </tr>"""
            dup_table += "</tbody></table>"
            from django.utils.safestring import mark_safe
            messages.warning(
                self.request,
                mark_safe(f"Found {len(duplicate_records)} duplicate students during import. These records were not imported. "
                f"<button type='button' class='btn btn-link p-0 m-0 align-baseline' "
                f"data-bs-toggle='collapse' data-bs-target='#csv-duplicates' aria-expanded='false'>View details</button>"
                f'<div class="collapse" id="csv-duplicates">'
                f'<div class="card card-body">'
                f'{dup_table}'
                f'</div></div>'
                )
            )

        return super().form_valid(form)

    def form_invalid(self, form):
        # Check for file validation errors (example)
        if 'file' in form.errors:
            for error in form.errors['file']:
                messages.warning(self.request, error)

        # Alternatively, show a generic error
        # messages.error(self.request, "Please correct the errors below.")

        return super().form_invalid(form)


def student_csv_template(request, school_slug=None):
    """
    View for downloading a CSV template for student bulk upload
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_template.csv"'

    writer = csv.writer(response)
    writer.writerow(['first_name', 'last_name', 'date_of_birth', 'parent_name', 'contact_phone'])

    # Add a sample row
    writer.writerow(['John', 'Doe', '2015-05-12', 'Jane Doe', '555-1234'])

    return response


class AdminStaffCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating a new administration staff member
    """
    model = AdministrationStaff
    template_name = 'schools/admin_staff_form.html'
    fields = ['title', 'first_name', 'last_name', 'contact_phone', 'contact_email', 'position']

    # Add username field to the form
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Add username field
        form.fields['username'] = forms.CharField(
            max_length=150,
            help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        )
        return form

    def get_success_url(self):
        return reverse_lazy('schools:staff_list', kwargs={'school_slug': self.school_slug})

    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug
        self.school_slug = kwargs.get('school_slug')
        self.school = get_object_or_404(School, slug=self.school_slug)

        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=self.school.pk).exists():
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.warning(request, "You do not have access to this school.")
                return redirect('core:home')
        else:
            messages.warning(request, "Only principals and administration can add staff.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        return context

    def form_valid(self, form):
        # Create the administration staff
        admin_staff = form.save(commit=False)
        admin_staff.school = self.school

        # Get username and email from form
        username = form.cleaned_data['username']
        email = form.cleaned_data['contact_email']
        password = "ChangeMe!"  # Default password that must be changed

        # Check if user with this username already exists
        if User.objects.filter(username=username).exists():
            messages.warning(self.request, f"A user with the username '{username}' already exists.")
            return self.form_invalid(form)

        # Check if user with this email already exists
        if User.objects.filter(email=email).exists():
            messages.warning(self.request, f"A user with the email '{email}' already exists.")
            return self.form_invalid(form)

        # Create the user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=form.cleaned_data['first_name'],
            last_name=form.cleaned_data['last_name']
        )

        # Update the user profile to be administration
        profile = user.profile
        profile.user_type = 'administration'
        profile.phone_number = form.cleaned_data['contact_phone']
        profile.must_change_password = True  # Force password change on first login
        profile.save()

        # Link the administration staff to the user
        admin_staff.user = user
        admin_staff.save()

        messages.success(self.request, f"Administration staff {admin_staff} has been added successfully!")
        return redirect(self.get_success_url())
