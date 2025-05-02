from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from .models import Year
from schools.models import School

class SchoolYearSetupView(LoginRequiredMixin, CreateView):
    """
    View for setting up the school year
    """
    model = Year
    template_name = 'academics/school_year_setup.html'
    fields = ['start_year', 'term1_start_date', 'term1_end_date', 'term1_school_days',
              'term2_start_date', 'term2_end_date', 'term2_school_days',
              'term3_start_date', 'term3_end_date', 'term3_school_days']

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
        else:
            messages.error(request, "Only principals can set up school year.")
            return redirect('core:home')

        return super().dispatch(request, *args, **kwargs)

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
        response = super().form_valid(form)
        messages.success(self.request, "School year has been set up successfully!")
        return response

    def get_success_url(self):
        """
        Redirect to the dashboard after successful setup
        """
        return reverse_lazy('core:dashboard')

def get_current_school_year_and_term(request):
    """
    Helper function to determine the current school year and term
    """
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
            
        return {
            'current_year': current_year,
            'current_term': current_term,
            'is_on_vacation': current_term is None
        }
    except Year.DoesNotExist:
        return {
            'current_year': None,
            'current_term': None,
            'is_on_vacation': True
        }
