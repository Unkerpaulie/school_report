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
from core.utils import get_current_year_and_term, unassign_teacher, get_current_teacher_assignment, unenroll_student, get_current_student_enrollment
from core.mixins import SchoolAccessRequiredMixin
from academics.models import SchoolYear, Term, StandardTeacher, SchoolEnrollment, StandardEnrollment, SchoolStaff
# Backward compatibility alias
Enrollment = StandardEnrollment
from .models import School, Standard, Student
import csv
from datetime import datetime, date


class StaffListView(LoginRequiredMixin, ListView):
    """
    View for listing all staff (teachers and administration) in a school
    """
    model = UserProfile
    template_name = 'schools/staff_list.html'
    context_object_name = 'staff_members'

    def dispatch(self, request, *args, **kwargs):
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

    def get_queryset(self):
        # Get all active staff from this school via SchoolStaff
        # No longer tied to academic year - staff employment persists across years
        school_staff = SchoolStaff.objects.filter(
            school=self.school,
            is_active=True
        ).select_related('staff__user')

        # Create a list to hold all staff members with their type
        staff_list = []

        # Get current teacher assignments for the current year using historical logic
        teacher_assignments = {}

        # Get current academic year for teacher assignments
        current_year, current_term, is_on_vacation = get_current_year_and_term(school=self.school)

        # Get all teachers in this school
        teacher_profiles = [staff.staff for staff in school_staff if staff.staff.user_type == 'teacher']

        if current_year:  # Only get assignments if we have a current year
            for teacher_profile in teacher_profiles:
                current_assignment = get_current_teacher_assignment(teacher_profile, current_year)
                if current_assignment:
                    teacher_assignments[teacher_profile.id] = {
                        'standard': current_assignment.standard,
                        'assignment_id': current_assignment.id
                    }

        # Process each staff member
        for staff_member in school_staff:
            user_profile = staff_member.staff

            # Check if this is a teacher with an assignment
            assignment_info = teacher_assignments.get(user_profile.id)
            assigned_standard = assignment_info['standard'] if assignment_info else None
            assignment_id = assignment_info['assignment_id'] if assignment_info else None

            # Determine staff type display
            if user_profile.user_type == 'teacher':
                type_display = 'Teacher'
                is_teacher = True
            elif user_profile.user_type == 'principal':
                type_display = f'Principal ({staff_member.position})' if staff_member.position else 'Principal'
                is_teacher = False
            else:  # administration
                type_display = f'Administration ({staff_member.position})' if staff_member.position else 'Administration'
                is_teacher = False

            staff_list.append({
                'id': user_profile.id,
                'name': user_profile.get_full_name(),
                'email': user_profile.user.email,
                'phone': user_profile.phone_number,
                'username': user_profile.user.username,
                'type': type_display,
                'is_teacher': is_teacher,
                'is_active': staff_member.is_active,
                'assigned_standard': assigned_standard,
                'assignment_id': assignment_id,
                'obj': user_profile,
                'staff_obj': staff_member
            })

        # Sort the combined list by name
        staff_list.sort(key=lambda x: x['name'])

        return staff_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        return context


class TeacherCreateForm(forms.Form):
    """
    Custom form for creating teachers
    """
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    username = forms.CharField(
        max_length=150,
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
    )
    contact_email = forms.EmailField(required=True)
    contact_phone = forms.CharField(max_length=20, required=False)
    title = forms.ChoiceField(choices=UserProfile.TITLE_CHOICES)
    position = forms.CharField(max_length=100, required=False, help_text="e.g., Mathematics Teacher, Class Teacher")


class TeacherCreateView(LoginRequiredMixin, FormView):
    """
    View for creating a new teacher
    """
    template_name = 'schools/teacher_form.html'
    form_class = TeacherCreateForm

    def get_success_url(self):
        return reverse('schools:staff_list', kwargs={'school_slug': self.school_slug})

    def dispatch(self, request, *args, **kwargs):
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

        # Only principals and administration can create teachers
        if user_profile.user_type not in ['principal', 'administration']:
            messages.warning(request, "You do not have permission to add teachers.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        return context



    def form_valid(self, form):
        try:
            # Create user with the form data
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['contact_email'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                password='ChangeMe!'
            )
        except Exception as e:
            messages.error(self.request, f"Error creating user: {e}")
            return self.form_invalid(form)

        try:
            # Get the automatically created profile and update it
            profile = user.profile
            profile.user_type = 'teacher'
            profile.phone_number = form.cleaned_data.get('contact_phone', '')
            profile.title = form.cleaned_data['title']
            profile.must_change_password = True
            profile.save()
        except Exception as e:
            messages.error(self.request, f"Error updating profile: {e}")
            return self.form_invalid(form)

        try:
            # Create SchoolStaff entry for the teacher (no longer tied to academic year)
            school_staff = SchoolStaff.objects.create(
                school=self.school,
                staff=profile,
                position=form.cleaned_data.get('position', 'Teacher'),
                is_active=True
            )
        except Exception as e:
            messages.error(self.request, f"Error creating school staff: {e}")
            return self.form_invalid(form)

        messages.success(self.request, f"Teacher {profile.get_full_name()} has been added successfully!")
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

    def get_queryset(self):
        # Get current school year using the centralized function
        current_year, current_term, vacation_status = get_current_year_and_term(school=self.school)

        # Current year is guaranteed to exist now
        # For principals and administration, show all students currently enrolled in this school
        if self.request.user.profile.user_type in ['principal', 'administration']:
            # Get all students who have current class assignments (non-null standard) in this school
            students = Student.objects.filter(
                standard_enrollments__year=current_year,
                standard_enrollments__standard__school=self.school,
                standard_enrollments__standard__isnull=False  # Only current assignments
            ).distinct()

            # Filter to only students with current (latest) enrollment
            current_students = []
            for student in students:
                current_enrollment = get_current_student_enrollment(student, current_year)
                if current_enrollment and current_enrollment.standard.school == self.school:
                    current_students.append(student)

            return current_students

        # For teachers, show only students in their assigned classes
        elif self.request.user.profile.user_type == 'teacher':
            user_profile = self.request.user.profile
            teacher_assignment = get_current_teacher_assignment(user_profile, current_year)

            if teacher_assignment:
                # Get students currently assigned to teacher's class
                students = Student.objects.filter(
                    standard_enrollments__year=current_year,
                    standard_enrollments__standard=teacher_assignment.standard,
                    standard_enrollments__standard__isnull=False
                ).distinct()

                # Filter to only students with current enrollment in this class
                current_students = []
                for student in students:
                    current_enrollment = get_current_student_enrollment(student, current_year)
                    if current_enrollment and current_enrollment.standard == teacher_assignment.standard:
                        current_students.append(student)

                return current_students

        return Student.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add school and school_slug to context
        context['school'] = self.school
        context['school_slug'] = self.school_slug

        # Get current school year using the centralized function
        current_year, current_term, vacation_status = get_current_year_and_term(school=self.school)

        # Add standards for filtering
        if self.request.user.profile.user_type in ['principal', 'administration']:
            context['standards'] = Standard.objects.filter(school=self.school)
        elif self.request.user.profile.user_type == 'teacher':
            user_profile = self.request.user.profile
            if current_year:
                context['standards'] = Standard.objects.filter(
                    school=self.school,
                    teacher_assignments__teacher=user_profile,
                    teacher_assignments__year=current_year
                ).distinct()
            else:
                context['standards'] = Standard.objects.none()

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

    def get_queryset(self):
        # For principals and administration, show all standards in the school
        if self.request.user.profile.user_type in ['principal', 'administration']:
            return Standard.objects.filter(school=self.school).prefetch_related(
                'teacher_assignments__teacher',
                'student_assignments__student'
            )

        # For teachers, show only their assigned standard
        elif self.request.user.profile.user_type == 'teacher':
            user_profile = self.request.user.profile
            # Get current school year using the centralized function
            current_year, current_term, is_on_vacation = get_current_year_and_term(school=self.school)
            if current_year:
                return Standard.objects.filter(
                    school=self.school,
                    teacher_assignments__teacher=user_profile,
                    teacher_assignments__year=current_year
                ).prefetch_related(
                    'teacher_assignments__teacher',
                    'student_assignments__student'
                ).distinct()
            else:
                return Standard.objects.none()

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

        # Get current school year using the centralized function
        current_year, current_term, vacation_status = get_current_year_and_term(school=self.school)

        # Get current teacher assignments for this standard using historical logic
        if current_year:
            # Get all teachers who might be assigned to this standard
            all_assignments = StandardTeacher.objects.filter(
                standard=standard,
                year=current_year
            ).values_list('teacher', flat=True).distinct()

            current_assignments = []
            for teacher in all_assignments:
                # teacher = UserProfile.objects.get(id=teacher.id)
                current_assignment = get_current_teacher_assignment(teacher, current_year)
                if current_assignment and current_assignment.standard == standard:
                    current_assignments.append(current_assignment)

            context['teacher_assignments'] = current_assignments
        else:
            context['teacher_assignments'] = []

        # Get students currently enrolled in this standard using historical logic
        if current_year:
            # Get all students who might be enrolled in this standard
            all_enrollments = StandardEnrollment.objects.filter(
                standard=standard,
                year=current_year
            ).values_list('student', flat=True).distinct()

            current_students = []
            for student_id in all_enrollments:
                from schools.models import Student
                student = Student.objects.get(id=student_id)
                current_enrollment = get_current_student_enrollment(student, current_year)
                if current_enrollment and current_enrollment.standard == standard:
                    current_students.append(student)

            context['enrolled_students'] = current_students
        else:
            context['enrolled_students'] = []

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

        # Only principals and administration can assign teachers
        if user_profile.user_type not in ['principal', 'administration']:
            messages.warning(request, "Only principals and administration can assign teachers.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        teacher = get_object_or_404(UserProfile, pk=self.teacher_id, user_type='teacher')

        # Get the current academic year using the centralized function
        current_year, current_term, vacation_status = get_current_year_and_term(school=self.school)

        # Current year is guaranteed to exist now

        # Check if the teacher is already assigned to a class using historical logic
        existing_assignment = get_current_teacher_assignment(teacher, current_year)

        if existing_assignment:
            # If teacher is already assigned, show no standards
            form.fields['standard'].queryset = Standard.objects.none()
            messages.warning(self.request, f"This teacher is already assigned to {existing_assignment.standard}.")
            return form

        # Filter standards to only show those from the current school
        # and exclude standards that already have a teacher assigned
        # With bidirectional unassignment, we need to check the latest record for each standard
        from core.utils import get_current_standard_teacher

        all_standards = Standard.objects.filter(school=self.school)
        available_standards = []

        for standard in all_standards:
            current_teacher = get_current_standard_teacher(standard, current_year)
            if not current_teacher:  # No teacher currently assigned
                available_standards.append(standard.id)

        available_standards = Standard.objects.filter(
            school=self.school,
            id__in=available_standards
        )

        form.fields['standard'].queryset = available_standards

        if not available_standards.exists():
            messages.warning(self.request, "There are no available classes for assignment. All classes already have teachers assigned.")

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        context['teacher'] = get_object_or_404(UserProfile, pk=self.teacher_id, user_type='teacher')
        return context

    def form_valid(self, form):
        # Get the teacher from the URL parameter
        teacher = get_object_or_404(UserProfile, pk=self.teacher_id, user_type='teacher')

        # Verify teacher is associated with this school via SchoolStaff
        school_staff = SchoolStaff.objects.filter(
            staff=teacher,
            school=self.school,
            is_active=True
        ).first()

        if not school_staff:
            messages.warning(self.request, "This teacher is not associated with this school.")
            return self.form_invalid(form)

        # Get the current academic year using the centralized function
        current_year, current_term, vacation_status = get_current_year_and_term(school=self.school)

        # Current year is guaranteed to exist now

        # Get the selected standard
        standard = form.cleaned_data['standard']

        # Verify standard belongs to this school
        if standard.school != self.school:
            messages.warning(self.request, "This class does not belong to this school.")
            return self.form_invalid(form)

        # Check if the teacher is already assigned to a class using historical logic
        existing_teacher_assignment = get_current_teacher_assignment(teacher, current_year)

        if existing_teacher_assignment:
            messages.warning(self.request, f"This teacher is already assigned to {existing_teacher_assignment.standard}.")
            return self.form_invalid(form)

        # Check if the class already has a teacher assigned using the new bidirectional logic
        from core.utils import get_current_standard_teacher
        current_standard_teacher = get_current_standard_teacher(standard, current_year)

        if current_standard_teacher:
            messages.warning(self.request, f"This class already has {current_standard_teacher.teacher.get_full_name()} assigned to it.")
            return self.form_invalid(form)

        # Create the assignment
        assignment = form.save(commit=False)
        assignment.year = current_year
        assignment.teacher = teacher
        assignment.save()

        messages.success(self.request, f"Teacher {teacher.get_full_name()} has been assigned to {standard} successfully!")
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

        # Check if user has access to this school via SchoolStaff
        user_profile = request.user.profile
        school_staff = SchoolStaff.objects.filter(
            staff=user_profile,
            school=school,
            is_active=True
        ).first()

        if not school_staff:
            messages.warning(request, "You do not have access to this school.")
            return redirect('core:home')

        # Only principals and administration can unassign teachers
        if user_profile.user_type not in ['principal', 'administration']:
            messages.warning(request, "Only principals and administration can unassign teachers.")
            return redirect('core:home')

        # Get the assignment
        assignment = get_object_or_404(StandardTeacher, pk=assignment_id)

        # Verify the assignment belongs to a teacher in this school
        teacher_in_school = SchoolStaff.objects.filter(
            staff=assignment.teacher,
            school=school,
            is_active=True
        ).exists()

        if not teacher_in_school:
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

        # Check if user has access to this school via SchoolStaff
        user_profile = request.user.profile
        school_staff = SchoolStaff.objects.filter(
            staff=user_profile,
            school=school,
            is_active=True
        ).first()

        if not school_staff:
            messages.warning(request, "You do not have access to this school.")
            return redirect('core:home')

        # Only principals and administration can unassign teachers
        if user_profile.user_type not in ['principal', 'administration']:
            messages.warning(request, "Only principals and administration can unassign teachers.")
            return redirect('core:home')

        # Get the assignment
        assignment = get_object_or_404(StandardTeacher, pk=assignment_id)

        # Verify the assignment belongs to a teacher in this school
        teacher_in_school = SchoolStaff.objects.filter(
            staff=assignment.teacher,
            school=school,
            is_active=True
        ).exists()

        if not teacher_in_school:
            messages.warning(request, "This assignment does not belong to a teacher in this school.")
            return redirect('schools:staff_list', school_slug=school_slug)

        # Store teacher and standard for the success message
        teacher = assignment.teacher
        standard = assignment.standard

        # Create bidirectional unassignment records
        unassign_teacher(teacher, standard, assignment.year)

        messages.success(request, f"Teacher {teacher.get_full_name()} has been unassigned from {standard} successfully!")
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

        # Check permissions for adding students
        if user_profile.user_type not in ['principal', 'administration']:
            messages.warning(request, "Only principals and administration can add students.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Add standard field for enrollment
        # Add academic year field
        form.fields['academic_year'] = forms.ModelChoiceField(
            queryset=SchoolYear.objects.filter(school=self.school).order_by('-start_year'),
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
        student.is_active = True
        student.save()

        # Enroll the student if a standard was selected
        if 'standard' in form.cleaned_data and form.cleaned_data['standard'] and 'academic_year' in form.cleaned_data and form.cleaned_data['academic_year']:
            standard = form.cleaned_data['standard']
            academic_year = form.cleaned_data['academic_year']

            # First, enroll student in the school (persistent relationship)
            # Get the first term's start date or use a default date
            enrollment_date = academic_year.terms.first().start_date if academic_year.terms.exists() else date(academic_year.start_year, 9, 1)
            school_enrollment, created = SchoolEnrollment.objects.get_or_create(
                school=self.school,
                student=student,
                defaults={
                    'enrollment_date': enrollment_date,
                    'is_active': True
                }
            )

            # Then, assign student to the class for this year
            class_assignment = StandardEnrollment.objects.create(
                year=academic_year,
                standard=standard,
                student=student
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
        # Get the student by ID and ensure it's enrolled in this school
        student = super().get_object(queryset)

        # Check if student is enrolled in this school through any enrollment
        current_year = SchoolYear.objects.filter(school=self.school).order_by('-start_year').first()
        if current_year:
            enrollment_exists = StandardEnrollment.objects.filter(
                student=student,
                year=current_year,
                standard__school=self.school
            ).exists()
            if not enrollment_exists:
                raise Http404("Student not found in this school")
        else:
            raise Http404("Student not found in this school")

        return student

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        context['is_update'] = True

        # Get current academic year for this school
        current_year = SchoolYear.objects.filter(school=self.school).order_by('-start_year').first()

        if current_year:
            current_enrollment = StandardEnrollment.objects.filter(
                student=self.object,
                year=current_year,
                standard__school=self.school
            ).first()

            if current_enrollment:
                context['current_enrollment'] = current_enrollment

        return context

    def form_valid(self, form):
        # Update the student
        student = form.save()
        messages.success(self.request, f"Student {student} has been updated successfully!")
        return redirect(self.get_success_url())


class StudentDetailView(SchoolAccessRequiredMixin, DetailView):
    """
    View for showing details of a student
    """
    model = Student
    template_name = 'schools/student_detail.html'
    context_object_name = 'student'

    def get_object(self, queryset=None):
        # Get the student by ID and ensure it's enrolled in this school
        student = super().get_object(queryset)

        # Check if student has any enrollment in this school
        enrollment_exists = StandardEnrollment.objects.filter(
            student=student,
            standard__school=self.school
        ).exists()

        if not enrollment_exists:
            raise Http404("Student not found in this school")

        return student

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        current_year, current_term, vacation_status = get_current_year_and_term(school=self.school)

        # Get enrollment history
        enrollments = StandardEnrollment.objects.filter(
            student=self.object
        ).select_related('year', 'standard').order_by('-year__start_year')

        context['enrollments'] = enrollments

        # Get current enrollment
        current_enrollment = enrollments.filter(year=current_year).first()
        if current_enrollment:
            context['current_enrollment'] = current_enrollment

        # Get finalized reports for this student
        from reports.models import StudentTermReview
        finalized_reports = StudentTermReview.objects.filter(
            student=self.object,
            is_finalized=True
        ).select_related('term', 'term__year').order_by('-term__year__start_year', '-term__term_number')

        context['finalized_reports'] = finalized_reports

        return context


class EnrollmentCreateView(LoginRequiredMixin, CreateView):
    """
    View for enrolling a student in a class
    """
    model = StandardEnrollment
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
        self.student = get_object_or_404(Student, pk=self.student_id)

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
        form.fields['academic_year'] = forms.ModelChoiceField(
            queryset=SchoolYear.objects.filter(school=self.school).order_by('-start_year'),
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
        new_standard = form.cleaned_data['standard']

        # Check if student has a current enrollment in this year
        current_enrollment = get_current_student_enrollment(self.student, academic_year)

        if current_enrollment:
            # If changing to a different class, create unenrollment record first
            if current_enrollment.standard != new_standard:
                unenroll_student(self.student, academic_year)
                messages.info(self.request, f"Student {self.student} has been unenrolled from {current_enrollment.standard.get_name_display()}.")

        # Ensure student is enrolled in the school first
        # Get the first term's start date or use a default date
        enrollment_date = academic_year.terms.first().start_date if academic_year.terms.exists() else date(academic_year.start_year, 9, 1)
        school_enrollment, created = SchoolEnrollment.objects.get_or_create(
            school=self.school,
            student=self.student,
            defaults={
                'enrollment_date': enrollment_date,
                'is_active': True
            }
        )

        # Create the new class assignment (even if it's the same class, for history)
        class_assignment = StandardEnrollment.objects.create(
            year=academic_year,
            student=self.student,
            standard=new_standard
        )

        messages.success(self.request, f"Student {self.student} has been enrolled in {new_standard.get_name_display()} for the {academic_year} academic year.")
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
        queryset=SchoolYear.objects.all().order_by('-start_year'),
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
                    first_name__iexact=first_name,
                    last_name__iexact=last_name,
                    date_of_birth=date_of_birth,
                    parent_name__iexact=parent_name
                ).first()

                if existing_student:
                    # Check if the student is already registered in this school
                    school_registration = SchoolEnrollment.objects.filter(
                        student=existing_student,
                        school=self.school,
                        is_active=True
                    ).exists()

                    # Check if the student is already assigned to a class in this school for this academic year
                    existing_class_assignment = StandardEnrollment.objects.filter(
                        student=existing_student,
                        year=academic_year,
                        standard__school=self.school
                    ).exists()

                    # Add to duplicate records - store only necessary info, not the entire object
                    duplicate_records.append({
                        'row': row_num,
                        'data': row,
                        'existing_student_id': existing_student.id,
                        'existing_student_name': f"{existing_student.first_name} {existing_student.last_name}",
                        'already_enrolled': existing_class_assignment,
                        'same_school': school_registration,
                        'school_name': existing_student.school_registrations.filter(is_active=True).first().school.name if existing_student.school_registrations.filter(is_active=True).exists() else 'Unknown'
                    })
                    continue  # Skip to the next row

                # Create the student with transaction
                with transaction.atomic():
                    # Create the student
                    student = Student.objects.create(
                        first_name=first_name,
                        last_name=last_name,
                        date_of_birth=date_of_birth,
                        parent_name=parent_name,
                        contact_phone=row.get('contact_phone', '').strip(),
                        is_active=True
                    )

                    # First, enroll student in the school (persistent relationship)
                    # Get the first term's start date or use a default date
                    enrollment_date = academic_year.terms.first().start_date if academic_year.terms.exists() else date(academic_year.start_year, 9, 1)
                    SchoolEnrollment.objects.get_or_create(
                        school=self.school,
                        student=student,
                        defaults={
                            'enrollment_date': enrollment_date,
                            'is_active': True
                        }
                    )

                    # Then, assign student to the class for this year
                    StandardEnrollment.objects.create(
                        year=academic_year,
                        standard=standard,
                        student=student
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
                student_id = duplicate['existing_student_id']
                student_name = duplicate['existing_student_name']
                school_name = duplicate['school_name']
                same_school = duplicate['same_school']

                # Prepare the message based on whether the student is in the same school or a different one
                if same_school:
                    duplicate_message = f"Student already exists in this school (ID: {student_id}, {student_name})"
                else:
                    duplicate_message = f"Student already exists in another school: {school_name} (ID: {student_id}, {student_name})"

                dup_table += f"""
                <tr>
                    <td>{duplicate['data']['first_name']}</td>
                    <td>{duplicate['data']['last_name']}</td>
                    <td>{duplicate['data']['date_of_birth']}</td>
                    <td>{duplicate['data']['parent_name']}</td>
                    <td>{duplicate['data'].get('contact_phone', '')}</td>
                    <td class="text-warning">
                        {duplicate_message} -
                        <a href="{reverse('schools:student_detail', kwargs={'school_slug': self.school_slug if same_school else duplicate['school_slug'], 'pk': student_id})}">View</a>
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


class AdminStaffCreateForm(forms.Form):
    """
    Custom form for creating admin staff
    """
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    username = forms.CharField(
        max_length=150,
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
    )
    contact_email = forms.EmailField(required=True)
    contact_phone = forms.CharField(max_length=20, required=False)
    title = forms.ChoiceField(choices=UserProfile.TITLE_CHOICES)
    position = forms.CharField(max_length=100, required=True)


class AdminStaffCreateView(LoginRequiredMixin, FormView):
    """
    View for creating a new administration staff member
    """
    template_name = 'schools/admin_staff_form.html'
    form_class = AdminStaffCreateForm

    def get_success_url(self):
        return reverse('schools:staff_list', kwargs={'school_slug': self.school_slug})

    def dispatch(self, request, *args, **kwargs):
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

        # Only principals can add admin staff
        if user_profile.user_type not in ['principal']:
            messages.warning(request, "Only principals can add administration staff.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        return context

    def post(self, request, *args, **kwargs):
        print(f"DEBUG: AdminStaffCreateView POST called")
        print(f"DEBUG: POST data: {request.POST}")
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        print(f"DEBUG: AdminStaffCreateView form_invalid called")
        print(f"DEBUG: Form errors: {form.errors}")
        print(f"DEBUG: Form non_field_errors: {form.non_field_errors()}")
        return super().form_invalid(form)

    def form_valid(self, form):
        try:
            # Create user with the form data
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['contact_email'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                password='ChangeMe!'
            )
        except Exception as e:
            messages.error(self.request, f"Error creating user: {e}")
            return self.form_invalid(form)

        try:
            # Get the automatically created profile and update it
            profile = user.profile
            profile.user_type = 'administration'
            profile.phone_number = form.cleaned_data.get('contact_phone', '')
            profile.title = form.cleaned_data['title']
            profile.must_change_password = True
            profile.save()
        except Exception as e:
            messages.error(self.request, f"Error updating profile: {e}")
            return self.form_invalid(form)

        try:
            # Create SchoolStaff entry for the admin (no longer tied to academic year)
            school_staff = SchoolStaff.objects.create(
                school=self.school,
                staff=profile,
                position=form.cleaned_data.get('position', 'Administration'),
                is_active=True
            )
        except Exception as e:
            messages.error(self.request, f"Error creating school staff: {e}")
            return self.form_invalid(form)

        messages.success(self.request, f"Administration staff {profile.get_full_name()} has been added successfully!")
        return redirect(self.get_success_url())
