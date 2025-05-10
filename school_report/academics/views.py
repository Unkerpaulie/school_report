from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse_lazy
from django.db.models import Q
from django import forms
from django.core.exceptions import ValidationError
from .models import Year
from schools.models import School
from core.mixins import SchoolAdminRequiredMixin, SchoolAccessRequiredMixin


class YearForm(forms.ModelForm):
    """
    Custom form for Year model with additional validation
    """
    class Meta:
        model = Year
        fields = ['start_year', 'term1_start_date', 'term1_end_date', 'term1_school_days',
                  'term2_start_date', 'term2_end_date', 'term2_school_days',
                  'term3_start_date', 'term3_end_date', 'term3_school_days']

    def clean_start_year(self):
        """
        Validate that start_year is unique
        """
        start_year = self.cleaned_data.get('start_year')

        # Check if this is an update
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            # If this is an update, exclude the current instance from the check
            if Year.objects.filter(start_year=start_year).exclude(pk=instance.pk).exists():
                raise ValidationError("An academic year with this start year already exists.")
        else:
            # If this is a new instance, check if the start_year already exists
            if Year.objects.filter(start_year=start_year).exists():
                raise ValidationError("An academic year with this start year already exists.")

        return start_year

class YearListView(LoginRequiredMixin, SchoolAdminRequiredMixin, ListView):
    """
    View for listing academic years
    """
    model = Year
    template_name = 'academics/year_list.html'
    context_object_name = 'years'

    def get_queryset(self):
        # Get all years, ordered by start_year (descending)
        return Year.objects.all().order_by('-start_year')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the current year and term
        current_year_data = get_current_school_year_and_term(self.request)
        context['current_year'] = current_year_data.get('current_year')

        return context


class YearUpdateView(LoginRequiredMixin, SchoolAdminRequiredMixin, UpdateView):
    """
    View for updating an existing academic year
    """
    model = Year
    template_name = 'academics/year_form.html'
    form_class = YearForm

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


class YearDeleteView(LoginRequiredMixin, SchoolAdminRequiredMixin, DeleteView):
    """
    View for deleting an academic year
    """
    model = Year
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


class SchoolYearSetupView(LoginRequiredMixin, SchoolAdminRequiredMixin, CreateView):
    """
    View for setting up the school year
    """
    model = Year
    template_name = 'academics/school_year_setup.html'
    form_class = YearForm



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
            current_year = Year.objects.get(pk=request.session['current_year_id'])
            current_term = request.session['current_term']
            is_on_vacation = request.session.get('is_on_vacation', False)

            return {
                'current_year': current_year,
                'current_term': current_term,
                'is_on_vacation': is_on_vacation
            }
        except Year.DoesNotExist:
            # If the year no longer exists, clear the session data
            if 'current_year_id' in request.session:
                del request.session['current_year_id']
            if 'current_term' in request.session:
                del request.session['current_term']
            if 'is_on_vacation' in request.session:
                del request.session['is_on_vacation']

    # If not in session or session data is invalid, query the database
    current_date = timezone.now().date()

    try:
        # Get the current year
        current_year = Year.objects.get(
            term1_start_date__lte=current_date,
            term3_end_date__gte=current_date
        )

        # Determine the current term
        if current_date >= current_year.term1_start_date and current_date <= current_year.term1_end_date:
            current_term = 1
        elif current_date >= current_year.term2_start_date and current_date <= current_year.term2_end_date:
            current_term = 2
        elif current_date >= current_year.term3_start_date and current_date <= current_year.term3_end_date:
            current_term = 3
        else:
            current_term = None  # School is on vacation

        # Store in session for future requests
        request.session['current_year_id'] = current_year.id
        request.session['current_term'] = current_term
        request.session['is_on_vacation'] = current_term is None

        return {
            'current_year': current_year,
            'current_term': current_term,
            'is_on_vacation': current_term is None
        }
    except Year.DoesNotExist:
        # Clear any existing session data
        if 'current_year_id' in request.session:
            del request.session['current_year_id']
        if 'current_term' in request.session:
            del request.session['current_term']
        if 'is_on_vacation' in request.session:
            del request.session['is_on_vacation']

        return {
            'current_year': None,
            'current_term': None,
            'is_on_vacation': True
        }
