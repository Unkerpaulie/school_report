from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from django.utils import timezone
from .models import SchoolYear, Term
from schools.models import School
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

        # Get the current year and term
        current_year, current_term, is_on_vacation = get_current_year_and_term()
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
            is_on_vacation = request.session.get('is_on_vacation', False)

            return {
                'current_year': current_year,
                'current_term': current_term,
                'is_on_vacation': is_on_vacation
            }
        except SchoolYear.DoesNotExist:
            # If the year no longer exists, clear the session data
            if 'current_year_id' in request.session:
                del request.session['current_year_id']
            if 'current_term' in request.session:
                del request.session['current_term']
            if 'is_on_vacation' in request.session:
                del request.session['is_on_vacation']

    # If not in session or session data is invalid, query the database
    current_year, current_term, is_on_vacation = get_current_year_and_term()
    return {
        'current_year': current_year,
        'current_term': current_term,
        'is_on_vacation': is_on_vacation
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
