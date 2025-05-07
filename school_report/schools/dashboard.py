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

        # Add teacher and administration staff counts
        context['teacher_count'] = self.school.teachers.filter(is_active=True).count()
        context['admin_staff_count'] = self.school.admin_staff.filter(is_active=True).count()

        # Get current academic year
        from academics.models import Year, StandardTeacher
        import datetime

        current_year = Year.objects.filter(
            term1_start_date__lte=datetime.date.today(),
            term3_end_date__gte=datetime.date.today()
        ).first()

        # Get teacher assignments for standards
        if current_year:
            teacher_assignments = {}
            assignments = StandardTeacher.objects.filter(
                year=current_year,
                is_active=True,
                standard__school=self.school
            ).select_related('teacher', 'standard')

            # Create a dictionary of standard_id -> teacher for quick lookup
            for assignment in assignments:
                teacher_assignments[assignment.standard_id] = assignment.teacher

            context['teacher_assignments'] = teacher_assignments

        return context
