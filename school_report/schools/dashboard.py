from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from .models import School, Standard, Student
from academics.models import SchoolStaff
from core.utils import get_current_year_and_term

class SchoolDashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard view for a specific school
    """
    template_name = 'schools/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        # Get the school by slug
        self.school = get_object_or_404(School, slug=kwargs.get('school_slug'))

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        # Add the school slug to the context for URL generation
        context['school_slug'] = self.school.slug

        # Get current school year
        current_year, current_term, is_on_vacation = get_current_year_and_term(school=self.school)

        # Count teachers and admin staff through SchoolStaff
        teacher_count = SchoolStaff.objects.filter(
            school=self.school,
            staff__user_type='teacher',
            is_active=True
        ).count()

        admin_staff_count = SchoolStaff.objects.filter(
            school=self.school,
            staff__user_type__in=['principal', 'administration'],
            is_active=True
        ).count()
        # Count students through StudentEnrollment
        student_count = Student.objects.filter(
            standard_enrollments__year=current_year,
            standard_enrollments__standard__school=self.school
        ).distinct().count()


        context['teacher_count'] = teacher_count
        context['admin_staff_count'] = admin_staff_count
        context['student_count'] = student_count
        context['current_year'] = current_year

        return context
