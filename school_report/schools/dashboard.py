from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from .models import School

class SchoolDashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard view for a specific school
    """
    template_name = 'schools/dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug
        self.school = get_object_or_404(School, slug=kwargs.get('school_slug'))
        
        # Check if user has access to this school
        if request.user.profile.user_type == 'principal':
            # Principals should only access their own school
            if not hasattr(request.user, 'administered_schools') or not request.user.administered_schools.filter(pk=self.school.pk).exists():
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        elif request.user.profile.user_type == 'teacher':
            # Teachers should only access their assigned school
            if not hasattr(request.user, 'teacher_profile') or request.user.teacher_profile.school.pk != self.school.pk:
                messages.error(request, "You do not have access to this school.")
                return redirect('core:home')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        # Add the school slug to the context for URL generation
        context['school_slug'] = self.school.slug
        return context
