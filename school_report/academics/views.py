from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Count
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.http import Http404, JsonResponse
from .models import SchoolYear, Term, AcademicTransition, StandardEnrollment
from schools.models import School, Standard, Student
from core.mixins import SchoolAdminRequiredMixin, SchoolAccessRequiredMixin
from core.utils import get_current_year_and_term

class YearForm(forms.ModelForm):
    """
    Custom form for Year model with additional validation
    """
    term1_start_date = forms.DateField()
    term1_end_date = forms.DateField()
    term1_school_days = forms.IntegerField()

    term2_start_date = forms.DateField()
    term2_end_date = forms.DateField()
    term2_school_days = forms.IntegerField()

    term3_start_date = forms.DateField()
    term3_end_date = forms.DateField()
    term3_school_days = forms.IntegerField()

    class Meta:
        model = SchoolYear
        fields = ['start_year', 'term1_start_date', 'term1_end_date', 'term1_school_days',
                  'term2_start_date', 'term2_end_date', 'term2_school_days',
                  'term3_start_date', 'term3_end_date', 'term3_school_days']

    def __init__(self, *args, **kwargs):
        """
        Initialize the form and populate term fields with existing data if editing
        """
        super().__init__(*args, **kwargs)

        # If this is an existing instance, populate the term fields
        if self.instance and self.instance.pk:
            terms = self.instance.terms.all().order_by('term_number')

            # Create a dictionary for easy lookup
            terms_dict = {term.term_number: term for term in terms}

            # Populate term 1 fields
            if 1 in terms_dict:
                term1 = terms_dict[1]
                self.fields['term1_start_date'].initial = term1.start_date
                self.fields['term1_end_date'].initial = term1.end_date
                self.fields['term1_school_days'].initial = term1.school_days

            # Populate term 2 fields
            if 2 in terms_dict:
                term2 = terms_dict[2]
                self.fields['term2_start_date'].initial = term2.start_date
                self.fields['term2_end_date'].initial = term2.end_date
                self.fields['term2_school_days'].initial = term2.school_days

            # Populate term 3 fields
            if 3 in terms_dict:
                term3 = terms_dict[3]
                self.fields['term3_start_date'].initial = term3.start_date
                self.fields['term3_end_date'].initial = term3.end_date
                self.fields['term3_school_days'].initial = term3.school_days
    
    def clean(self):
        """
        Validate that term dates are in the correct order and don't overlap
        """
        cleaned_data = super().clean()
        
        # Validate Term 1 dates
        if cleaned_data.get('term1_start_date') and cleaned_data.get('term1_end_date'):
            if cleaned_data['term1_start_date'] > cleaned_data['term1_end_date']:
                self.add_error('term1_start_date', 'Term 1 start date must be before end date')
        
        # Validate Term 2 dates
        if cleaned_data.get('term2_start_date') and cleaned_data.get('term2_end_date'):
            if cleaned_data['term2_start_date'] > cleaned_data['term2_end_date']:
                self.add_error('term2_start_date', 'Term 2 start date must be before end date')
        
        # Validate Term 3 dates
        if cleaned_data.get('term3_start_date') and cleaned_data.get('term3_end_date'):
            if cleaned_data['term3_start_date'] > cleaned_data['term3_end_date']:
                self.add_error('term3_start_date', 'Term 3 start date must be before end date')
        
        # Validate terms don't overlap
        terms = [
            (cleaned_data.get('term1_start_date'), cleaned_data.get('term1_end_date')),
            (cleaned_data.get('term2_start_date'), cleaned_data.get('term2_end_date')),
            (cleaned_data.get('term3_start_date'), cleaned_data.get('term3_end_date')),
        ]
        
        for i in range(3):
            for j in range(i + 1, 3):
                if terms[i][0] and terms[i][1] and terms[j][0] and terms[j][1]:
                    if (terms[i][0] <= terms[j][1] and terms[i][1] >= terms[j][0]):
                        self.add_error(None, f'Terms {i+1} and {j+1} cannot overlap')
    
    def save(self, commit=True):
        """
        Save the SchoolYear and create/update associated Terms
        """
        # Save the SchoolYear first
        year = super().save(commit=commit)
        
        if commit and year.pk:
            # Create or update all three terms
            terms_data = [
                {
                    'term_number': 1,
                    'start_date': self.cleaned_data['term1_start_date'],
                    'end_date': self.cleaned_data['term1_end_date'],
                    'school_days': self.cleaned_data['term1_school_days']
                },
                {
                    'term_number': 2,
                    'start_date': self.cleaned_data['term2_start_date'],
                    'end_date': self.cleaned_data['term2_end_date'],
                    'school_days': self.cleaned_data['term2_school_days']
                },
                {
                    'term_number': 3,
                    'start_date': self.cleaned_data['term3_start_date'],
                    'end_date': self.cleaned_data['term3_end_date'],
                    'school_days': self.cleaned_data['term3_school_days']
                }
            ]
            
            # Create or update each term
            for term_data in terms_data:
                term, created = Term.objects.update_or_create(
                    year=year,
                    term_number=term_data['term_number'],
                    defaults={
                        'start_date': term_data['start_date'],
                        'end_date': term_data['end_date'],
                        'school_days': term_data['school_days']
                    }
                )
        
        return year

    def clean_start_year(self):
        """
        Validate that start_year is unique per school
        """
        start_year = self.cleaned_data.get('start_year')

        # We need the school to validate uniqueness
        # This will be set by the view when the form is used
        school = getattr(self, 'school', None)
        if not school:
            return start_year

        # Check if this is an update
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            # If this is an update, exclude the current instance from the check
            if SchoolYear.objects.filter(school=school, start_year=start_year).exclude(pk=instance.pk).exists():
                raise ValidationError(f"An academic year with start year {start_year} already exists for this school.")
        else:
            # If this is a new instance, check if the start_year already exists for this school
            if SchoolYear.objects.filter(school=school, start_year=start_year).exists():
                raise ValidationError(f"An academic year with start year {start_year} already exists for this school.")

        return start_year

class YearListView(SchoolAdminRequiredMixin, ListView):
    """
    View for listing academic years
    """
    model = SchoolYear
    template_name = 'academics/year_list.html'
    context_object_name = 'years'

    def get_queryset(self):
        # Get years for this school only, ordered by start_year (descending)
        return SchoolYear.objects.filter(school=self.school).order_by('-start_year')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the current year and term for this school
        current_year, current_term, vacation_status = get_current_year_and_term(school=self.school)
        context['current_year'] = current_year

        return context


class YearUpdateView(SchoolAdminRequiredMixin, UpdateView):
    """
    View for updating an existing academic year
    """
    model = SchoolYear
    template_name = 'academics/year_form.html'
    form_class = YearForm

    def get_form(self, form_class=None):
        """
        Set the school on the form for validation
        """
        form = super().get_form(form_class)
        form.school = self.school
        return form

    def get_success_url(self):
        return reverse_lazy('academics:year_list', kwargs={'school_slug': self.school_slug})

    def form_valid(self, form):
        response = super().form_valid(form)

        # Clear any existing session data to force recalculation
        if 'current_year_id' in self.request.session:
            del self.request.session['current_year_id']
        if 'current_term' in self.request.session:
            del self.request.session['current_term']
        if 'is_on_vacation' in self.request.session:
            del self.request.session['is_on_vacation']

        messages.success(self.request, "School year has been updated successfully!")
        return response


class YearDeleteView(SchoolAdminRequiredMixin, DeleteView):
    """
    View for deleting an academic year
    """
    model = SchoolYear
    template_name = 'academics/year_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('academics:year_list', kwargs={'school_slug': self.school_slug})

    def delete(self, request, *args, **kwargs):
        year = self.get_object()

        # Check if this year has any related records
        if (year.standard_teachers.exists() or
            year.enrollments.exists() or
            year.standard_subjects.exists() or
            year.term_tests.exists()):
            messages.warning(request, "Cannot delete this academic year because it has related records.")
            return redirect(self.get_success_url())

        # If no related records, proceed with deletion
        messages.success(request, "Academic year has been deleted successfully!")
        return super().delete(request, *args, **kwargs)


class SchoolYearSetupView(SchoolAdminRequiredMixin, CreateView):
    """
    View for setting up the school year
    """
    model = SchoolYear
    template_name = 'academics/school_year_setup.html'
    form_class = YearForm

    def get_form(self, form_class=None):
        """
        Set the school on the form for validation
        """
        form = super().get_form(form_class)
        form.school = self.school
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        context['school_slug'] = self.school_slug
        return context

    def get_initial(self):
        """
        Set default values for the form fields
        """
        initial = super().get_initial()
        current_year = timezone.now().year
        initial['start_year'] = current_year
        return initial

    def form_valid(self, form):
        """
        Save the school year and set it as the current year
        """
        # Set the school before saving
        form.instance.school = self.school

        # Save the form
        year = form.save()

        # Clear any existing session data to force recalculation
        if 'current_year_id' in self.request.session:
            del self.request.session['current_year_id']
        if 'current_term' in self.request.session:
            del self.request.session['current_term']
        if 'is_on_vacation' in self.request.session:
            del self.request.session['is_on_vacation']

        messages.success(self.request, "School year has been set up successfully!")
        return redirect(self.get_success_url())

    def get_success_url(self):
        """
        Redirect to the year list after successful setup
        """
        return reverse_lazy('academics:year_list', kwargs={'school_slug': self.school_slug})

def get_current_school_year_and_term(request):
    """
    Helper function to determine the current school year and term
    Uses session for caching to avoid repeated database queries
    """
    # Check if we have cached data in the session
    if 'current_year_id' in request.session and 'current_term' in request.session:
        try:
            current_year = SchoolYear.objects.get(pk=request.session['current_year_id'])
            current_term = request.session['current_term']
            vacation_status = request.session.get('vacation_status')
            is_on_vacation = request.session.get('is_on_vacation', False)

            return {
                'current_year': current_year,
                'current_term': current_term,
                'vacation_status': vacation_status,
                'is_on_vacation': is_on_vacation
            }
        except SchoolYear.DoesNotExist:
            # If the year no longer exists, clear the session data
            if 'current_year_id' in request.session:
                del request.session['current_year_id']
            if 'current_term' in request.session:
                del request.session['current_term']
            if 'vacation_status' in request.session:
                del request.session['vacation_status']
            if 'is_on_vacation' in request.session:
                del request.session['is_on_vacation']

    # If not in session or session data is invalid, return None values
    # This function should only be called when user has a school association
    return {
        'current_year': None,
        'current_term': None,
        'vacation_status': None,
        'is_on_vacation': True
    }
    
    # Store in session for future requests
    request.session['current_year_id'] = current_year.id if current_year else None
    request.session['current_term'] = current_term
    request.session['is_on_vacation'] = is_on_vacation
    
    return {
        'current_year': current_year,
        'current_term': current_term,
        'is_on_vacation': is_on_vacation
    }


# ============================================================================
# ACADEMIC TRANSITION VIEWS
# ============================================================================

class TransitionDashboardView(SchoolAdminRequiredMixin, TemplateView):
    """
    Main dashboard for academic year transition process.
    Only accessible to admin/principal users during summer vacation.
    """
    template_name = 'academics/transitions/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        # Check if we're in summer vacation period
        current_year, current_term, vacation_status = get_current_year_and_term(school=self.school)

        if vacation_status != 'summer':
            messages.error(request,
                "Academic transition is only available during summer vacation period.")
            return redirect('academics:year_list')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current and next academic years
        current_year, current_term, vacation_status = get_current_year_and_term(school=self.school)

        # Find the previous year (the one we're transitioning from)
        from_year = SchoolYear.objects.filter(
            school=self.school,
            start_year=current_year.start_year - 1
        ).first()

        # Get or create transition record
        transition, created = AcademicTransition.objects.get_or_create(
            school=self.school,
            from_year=from_year,
            to_year=current_year,
            defaults={'created_by': self.request.user.profile}
        )

        if created:
            messages.info(self.request, "Academic transition process initialized.")

        # Get standards with student counts for the transition table
        standards_data = self._get_standards_with_counts(from_year)

        context.update({
            'transition': transition,
            'from_year': from_year,
            'to_year': current_year,
            'standards_data': standards_data,
            'vacation_status': vacation_status,
        })

        return context

    def _get_standards_with_counts(self, from_year):
        """Get standards with student counts in reverse order (Std 5 to Inf 1)"""
        if not from_year:
            return []

        # Define standard order (highest to lowest)
        standard_order = ['std5', 'std4', 'std3', 'std2', 'std1', 'inf2', 'inf1']

        standards_data = []
        for std_code in standard_order:
            try:
                standard = Standard.objects.get(school=self.school, standard_code=std_code)

                # Count current students in this standard
                student_count = StandardEnrollment.objects.filter(
                    year=from_year,
                    standard=standard,
                    student__school_registrations__school=self.school,
                    student__school_registrations__is_active=True
                ).count()

                standards_data.append({
                    'standard': standard,
                    'student_count': student_count,
                    'code': std_code,
                })
            except Standard.DoesNotExist:
                # Standard doesn't exist in this school, skip it
                continue

        return standards_data


class GraduateStudentsView(SchoolAdminRequiredMixin, TemplateView):
    """
    View for processing student graduation/advancement for a specific standard.
    Handles the sequential processing requirement.
    """
    template_name = 'academics/transitions/graduate_students.html'

    def dispatch(self, request, *args, **kwargs):
        # Check if we're in summer vacation period
        current_year, current_term, vacation_status = get_current_year_and_term(school=self.school)

        if vacation_status != 'summer':
            messages.error(request,
                "Academic transition is only available during summer vacation period.")
            return redirect('academics:year_list')

        # Get the standard code from URL
        self.standard_code = kwargs.get('standard_code')

        # Validate that this standard can be processed (sequential requirement)
        if not self._can_process_standard():
            messages.error(request,
                f"Cannot process {self.standard_code.upper()} yet. Please complete previous standards first.")
            return redirect('academics:transition_dashboard')

        return super().dispatch(request, *args, **kwargs)

    def _can_process_standard(self):
        """Check if this standard can be processed based on sequential requirements"""
        # Get current transition record
        current_year, _, _ = get_current_year_and_term(school=self.school)
        from_year = SchoolYear.objects.filter(
            school=self.school,
            start_year=current_year.start_year - 1
        ).first()

        if not from_year:
            return False

        try:
            transition = AcademicTransition.objects.get(
                school=self.school,
                from_year=from_year,
                to_year=current_year
            )
        except AcademicTransition.DoesNotExist:
            return False

        # Check sequential requirements
        next_available = transition.get_next_available_standard()
        return next_available == self.standard_code

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current and previous years
        current_year, _, _ = get_current_year_and_term(school=self.school)
        from_year = SchoolYear.objects.filter(
            school=self.school,
            start_year=current_year.start_year - 1
        ).first()

        # Get the standard
        try:
            standard = Standard.objects.get(school=self.school, standard_code=self.standard_code)
        except Standard.DoesNotExist:
            raise Http404("Standard not found")

        # Get students in this standard with their academic data
        students_data = self._get_students_with_academic_data(from_year, standard)

        context.update({
            'standard': standard,
            'standard_code': self.standard_code,
            'from_year': from_year,
            'to_year': current_year,
            'students_data': students_data,
            'is_final_standard': self.standard_code == 'std5',  # Standard 5 graduates, others advance
        })

        return context

    def _get_students_with_academic_data(self, from_year, standard):
        """Get students with their academic performance and recommendations"""
        if not from_year:
            return []

        # Get students currently enrolled in this standard
        enrollments = StandardEnrollment.objects.filter(
            year=from_year,
            standard=standard,
            student__school_registrations__school=self.school,
            student__school_registrations__is_active=True
        ).select_related('student').order_by('student__last_name', 'student__first_name')

        students_data = []
        for enrollment in enrollments:
            student = enrollment.student

            # Get the student's final term review (Term 3) for academic data
            final_review = None
            try:
                final_term = from_year.terms.get(term_number=3)
                final_review = student.term_reviews.get(term=final_term)
            except:
                pass  # No final review available

            students_data.append({
                'student': student,
                'enrollment': enrollment,
                'final_review': final_review,
                'overall_percentage': final_review.overall_average_percentage if final_review else 0,
                'recommend_advancement': final_review.recommend_for_advancement if final_review else True,
            })

        return students_data

    def post(self, request, *args, **kwargs):
        """Process the graduation/advancement decisions"""
        # Get current and previous years
        current_year, _, _ = get_current_year_and_term(school=self.school)
        from_year = SchoolYear.objects.filter(
            school=self.school,
            start_year=current_year.start_year - 1
        ).first()

        # Get the standard
        try:
            standard = Standard.objects.get(school=self.school, standard_code=self.standard_code)
        except Standard.DoesNotExist:
            messages.error(request, "Standard not found.")
            return redirect('academics:transition_dashboard')

        # Process student decisions
        advancing_students = []
        repeating_students = []

        # Get all students in this standard
        enrollments = StandardEnrollment.objects.filter(
            year=from_year,
            standard=standard,
            student__school_registrations__school=self.school,
            student__school_registrations__is_active=True
        )

        for enrollment in enrollments:
            student_id = str(enrollment.student.id)
            decision = request.POST.get(f'student_{student_id}')

            if decision == 'advance':
                advancing_students.append(enrollment.student)
            else:  # 'repeat' or no decision defaults to repeat
                repeating_students.append(enrollment.student)

        # Process the decisions
        if self.standard_code == 'std5':
            # Standard 5 students graduate (set inactive)
            self._graduate_students(advancing_students)
        else:
            # Other standards advance to next level
            self._advance_students(advancing_students, current_year)

        # Students who repeat stay in their current standard for the new year
        self._repeat_students(repeating_students, current_year, standard)

        # Update transition status
        self._update_transition_status(from_year, current_year)

        # Success message
        messages.success(request,
            f"Processed {len(advancing_students)} advancing and {len(repeating_students)} repeating students for {standard.name}.")

        return redirect('academics:transition_dashboard')

    def _graduate_students(self, students):
        """Graduate Standard 5 students (set them as inactive)"""
        for student in students:
            # Set school enrollment as inactive (graduated)
            school_enrollment = student.school_registrations.get(school=self.school)
            school_enrollment.is_active = False
            school_enrollment.graduation_date = timezone.now().date()
            school_enrollment.save()

    def _advance_students(self, students, to_year):
        """Advance students to the next standard"""
        # Define advancement mapping
        advancement_map = {
            'std4': 'std5',
            'std3': 'std4',
            'std2': 'std3',
            'std1': 'std2',
            'inf2': 'std1',
            'inf1': 'inf2',
        }

        next_standard_code = advancement_map.get(self.standard_code)
        if not next_standard_code:
            return

        try:
            next_standard = Standard.objects.get(school=self.school, standard_code=next_standard_code)

            for student in students:
                # Create new enrollment in next standard for new year
                StandardEnrollment.objects.create(
                    year=to_year,
                    standard=next_standard,
                    student=student
                )
        except Standard.DoesNotExist:
            messages.error(self.request, f"Next standard {next_standard_code} not found.")

    def _repeat_students(self, students, to_year, current_standard):
        """Keep students in the same standard for the new year"""
        for student in students:
            StandardEnrollment.objects.create(
                year=to_year,
                standard=current_standard,
                student=student
            )

    def _update_transition_status(self, from_year, to_year):
        """Update the transition status for this standard"""
        try:
            transition = AcademicTransition.objects.get(
                school=self.school,
                from_year=from_year,
                to_year=to_year
            )

            # Update the appropriate field based on standard
            field_map = {
                'std5': 'std5_processed',
                'std4': 'std4_processed',
                'std3': 'std3_processed',
                'std2': 'std2_processed',
                'std1': 'std1_processed',
                'inf2': 'inf2_processed',
                'inf1': 'inf1_processed',
            }

            field_name = field_map.get(self.standard_code)
            if field_name:
                setattr(transition, field_name, True)
                setattr(transition, f'{field_name}_at', timezone.now())
                transition.save()

        except AcademicTransition.DoesNotExist:
            messages.error(self.request, "Transition record not found.")
