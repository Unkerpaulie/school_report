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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['school'] = self.school
        # Add the school slug to the context for URL generation
        context['school_slug'] = self.school.slug

        # Add user role to context
        user_type = self.request.user.profile.user_type
        context['user_type'] = user_type

        # Add role-specific data
        if user_type in ['principal', 'administration']:
            # For principals and administration, show school-wide stats
            from .models import Teacher, Student, Standard
            context['teacher_count'] = Teacher.objects.filter(school=self.school, is_active=True).count()
            context['student_count'] = Student.objects.filter(school=self.school, is_active=True).count()
            context['class_count'] = Standard.objects.filter(school=self.school).count()
            context['show_school_stats'] = True
        elif user_type == 'teacher':
            # For teachers, show class-specific stats
            teacher = self.request.user.teacher_profile
            from academics.models import StandardTeacher, Enrollment
            from .models import Student

            # Get teacher's assigned classes
            assigned_classes = StandardTeacher.objects.filter(
                teacher=teacher,
                is_active=True
            ).select_related('standard')

            context['assigned_classes'] = assigned_classes

            # Get students in teacher's classes
            if assigned_classes.exists():
                student_ids = Enrollment.objects.filter(
                    standard__in=[st.standard for st in assigned_classes],
                    is_active=True
                ).values_list('student_id', flat=True)

                context['student_count'] = Student.objects.filter(id__in=student_ids).count()
            else:
                context['student_count'] = 0

            context['show_teacher_stats'] = True

        return context
