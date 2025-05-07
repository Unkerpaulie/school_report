from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django import forms
from django.http import Http404
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
from core.models import UserProfile
from academics.models import Year, StandardTeacher, Enrollment
from .models import School, Teacher, Standard, Student, AdministrationStaff


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
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'teacher':
            # Teachers should only access their assigned school
            if not hasattr(request.user, 'teacher_profile') or request.user.teacher_profile.school.pk != self.school.pk:
                messages.error(request, "You do not have access to this school.")
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
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        else:
            messages.error(request, "Only principals and administration can add staff.")
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
            messages.error(self.request, f"A user with the username '{username}' already exists.")
            return self.form_invalid(form)

        # Check if user with this email already exists
        if User.objects.filter(email=email).exists():
            messages.error(self.request, f"A user with the email '{email}' already exists.")
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
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'teacher':
            # Teachers should only access their assigned school
            if not hasattr(request.user, 'teacher_profile') or request.user.teacher_profile.school.pk != self.school.pk:
                messages.error(request, "You do not have access to this school.")
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
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'teacher':
            # Teachers should only access their assigned school
            if not hasattr(request.user, 'teacher_profile') or request.user.teacher_profile.school.pk != self.school.pk:
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # For principals and administration, show all standards in the school
        if self.request.user.profile.user_type in ['principal', 'administration']:
            return Standard.objects.filter(school=self.school)

        # For teachers, show only their assigned standard
        elif self.request.user.profile.user_type == 'teacher':
            teacher = self.request.user.teacher_profile
            return Standard.objects.filter(
                school=self.school,
                standardteacher__teacher=teacher,
                standardteacher__is_active=True
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
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'teacher':
            # Teachers should only access their assigned school
            if not hasattr(request.user, 'teacher_profile') or request.user.teacher_profile.school.pk != self.school.pk:
                messages.error(request, "You do not have access to this school.")
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
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        else:
            messages.error(request, "Only principals and administration can assign teachers.")
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
            messages.error(self.request, "No active academic year found. Please set up the academic year first.")
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
            messages.error(self.request, f"This teacher is already assigned to {existing_assignment.standard}.")
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
            messages.error(self.request, "This teacher does not belong to this school.")
            return self.form_invalid(form)

        # Set the current academic year
        current_year = Year.objects.filter(
            term1_start_date__lte=self.request.user.date_joined,
            term3_end_date__gte=self.request.user.date_joined
        ).first()

        if not current_year:
            messages.error(self.request, "No active academic year found.")
            return self.form_invalid(form)

        # Get the selected standard
        standard = form.cleaned_data['standard']

        # Verify standard belongs to this school
        if standard.school != self.school:
            messages.error(self.request, "This class does not belong to this school.")
            return self.form_invalid(form)

        # Check if the teacher is already assigned to a class
        existing_teacher_assignment = StandardTeacher.objects.filter(
            teacher=teacher,
            year=current_year,
            is_active=True
        ).first()

        if existing_teacher_assignment:
            messages.error(self.request, f"This teacher is already assigned to {existing_teacher_assignment.standard}.")
            return self.form_invalid(form)

        # Check if the class already has a teacher assigned
        existing_class_assignment = StandardTeacher.objects.filter(
            standard=standard,
            year=current_year,
            is_active=True
        ).first()

        if existing_class_assignment:
            messages.error(self.request, f"This class already has {existing_class_assignment.teacher} assigned to it.")
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
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != school.pk:
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        else:
            messages.error(request, "Only principals and administration can unassign teachers.")
            return redirect('core:home')

        # Get the assignment
        assignment = get_object_or_404(StandardTeacher, pk=assignment_id)

        # Verify the assignment belongs to a teacher in this school
        if assignment.teacher.school != school:
            messages.error(request, "This assignment does not belong to a teacher in this school.")
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
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != school.pk:
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        else:
            messages.error(request, "Only principals and administration can unassign teachers.")
            return redirect('core:home')

        # Get the assignment
        assignment = get_object_or_404(StandardTeacher, pk=assignment_id)

        # Verify the assignment belongs to a teacher in this school
        if assignment.teacher.school != school:
            messages.error(request, "This assignment does not belong to a teacher in this school.")
            return redirect('schools:staff_list', school_slug=school_slug)

        # Store teacher and standard for the success message
        teacher = assignment.teacher
        standard = assignment.standard

        # Deactivate the assignment (don't delete it to preserve history)
        assignment.is_active = False
        assignment.save()

        messages.success(request, f"Teacher {teacher} has been unassigned from {standard} successfully!")
        return redirect('schools:staff_list', school_slug=school_slug)


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
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'administration':
            # Administration users can only access their assigned school
            if not hasattr(request.user, 'admin_profile') or request.user.admin_profile.school.pk != self.school.pk:
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        else:
            messages.error(request, "Only principals and administration can add staff.")
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
            messages.error(self.request, f"A user with the username '{username}' already exists.")
            return self.form_invalid(form)

        # Check if user with this email already exists
        if User.objects.filter(email=email).exists():
            messages.error(self.request, f"A user with the email '{email}' already exists.")
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
