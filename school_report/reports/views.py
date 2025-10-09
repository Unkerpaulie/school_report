from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.utils import timezone
from django.db import transaction
from django.forms import modelformset_factory
from django.template.loader import render_to_string
from django.conf import settings
from academics.models import StandardSubject, StandardTeacher, SchoolStaff, SchoolYear, Term, StandardEnrollment
from schools.models import Student, School, Standard
from core.models import UserProfile
from core.utils import get_current_year_and_term, get_teacher_class_from_session, get_current_teacher_assignment, cleanup_old_pdf_files
import json
import os
import zipfile
from io import BytesIO
try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    WEASYPRINT_AVAILABLE = False
    print(f"WeasyPrint not available: {e}")
from .models import Test, TestSubject, TestScore, StudentTermReview, StudentSubjectScore


def generate_report_pdf(report, school, school_slug, request, subject_scores=None, current_enrollment=None):
    """
    Generate a PDF for a single student report.

    Args:
        report: StudentTermReview instance
        school: School instance
        school_slug: School slug string
        request: HTTP request object
        subject_scores: Optional pre-fetched subject scores (for bulk operations)
        current_enrollment: Optional pre-fetched enrollment (for bulk operations)

    Returns:
        tuple: (success: bool, pdf_content: bytes or None, error_message: str or None)
    """
    if not WEASYPRINT_AVAILABLE:
        return False, None, "PDF generation is not available. WeasyPrint library is not installed."

    try:
        # Get subject scores if not provided
        if subject_scores is None:
            subject_scores = StudentSubjectScore.objects.filter(
                term_review=report
            ).select_related('standard_subject').order_by('standard_subject__subject_name')

        # Get current enrollment if not provided
        if current_enrollment is None:
            current_enrollment = StandardEnrollment.objects.filter(
                student=report.student,
                year=report.term.year,
                standard__isnull=False
            ).select_related('standard').order_by('-created_at').first()

        # Render the report HTML
        html_content = render_to_string('reports/report_detail.html', {
            'report': report,
            'subject_scores': subject_scores,
            'school': school,
            'school_slug': school_slug,
            'current_enrollment': current_enrollment,
            'is_pdf_generation': True,  # Flag to modify template for PDF
        })

        # Generate PDF using WeasyPrint with optimized settings
        pdf_content = weasyprint.HTML(
            string=html_content,
            base_url=request.build_absolute_uri()
        ).write_pdf(
            optimize_images=True,  # Optimize images for smaller file size
            presentational_hints=True  # Use CSS presentational hints for faster rendering
        )

        return True, pdf_content, None

    except Exception as e:
        return False, None, str(e)


# Create your forms here
from django import forms

class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = ['test_type', 'test_date', 'term', 'description']
        widgets = {
            'test_date': forms.DateInput(attrs={'type': 'date', 'id': 'id_test_date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        current_year = kwargs.pop('current_year', None)
        super().__init__(*args, **kwargs)

        # Filter terms to only show those for the current school and year
        if school and current_year:
            from academics.models import Term
            terms_queryset = Term.objects.filter(
                year=current_year
            ).order_by('term_number')

            self.fields['term'].queryset = terms_queryset

            # Create custom widget with data attributes for each option
            choices = [('', '---------')]  # Empty choice
            for term in terms_queryset:
                choices.append((term.id, str(term)))

            # Custom widget that adds data attributes
            self.fields['term'].widget = forms.Select(attrs={
                'id': 'id_term',
                'class': 'form-control'
            })
            self.fields['term'].choices = choices

            # Store term data for the template to access
            self.term_data = {}
            for term in terms_queryset:
                self.term_data[term.id] = {
                    'start_date': term.start_date.strftime('%Y-%m-%d'),
                    'end_date': term.end_date.strftime('%Y-%m-%d'),
                    'name': str(term)
                }

            # Add help text to show the filtering
            self.fields['term'].help_text = f"Terms for {school.name} - {current_year}"
        else:
            # If no school/year provided, show empty queryset
            from academics.models import Term
            self.fields['term'].queryset = Term.objects.none()
            self.term_data = {}

class TestSubjectForm(forms.ModelForm):
    class Meta:
        model = TestSubject
        fields = ['standard_subject', 'max_score']

class SubjectForm(forms.ModelForm):
    class Meta:
        model = StandardSubject
        fields = ['subject_name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class BulkTestSubjectForm(forms.Form):
    """
    Form for managing multiple test subjects at once with checkboxes and max scores
    """
    def __init__(self, *args, **kwargs):
        test = kwargs.pop('test', None)
        super().__init__(*args, **kwargs)

        if test:
            # Get all test subjects for this test
            test_subjects = TestSubject.objects.filter(test=test).select_related('standard_subject')

            for test_subject in test_subjects:
                # Create checkbox field for enabled status
                self.fields[f'enabled_{test_subject.id}'] = forms.BooleanField(
                    required=False,
                    initial=test_subject.enabled,
                    widget=forms.CheckboxInput(attrs={
                        'class': 'subject-checkbox',
                        'data-subject-id': test_subject.id
                    })
                )

                # Create max score field
                self.fields[f'max_score_{test_subject.id}'] = forms.IntegerField(
                    min_value=1,
                    max_value=1000,
                    initial=test_subject.max_score,
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control max-score-input',
                        'data-subject-id': test_subject.id,
                        'disabled': not test_subject.enabled  # Disabled if not enabled
                    })
                )

class StudentTermReviewForm(forms.ModelForm):
    """
    Form for editing student term review data (attendance, behavioral ratings, remarks)
    """
    class Meta:
        model = StudentTermReview
        fields = [
            'days_present', 'days_late', 'attitude', 'respect', 'parental_support',
            'attendance', 'assignment_completion', 'class_participation',
            'time_management', 'remarks'
        ]
        widgets = {
            'days_present': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'days_late': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'attitude': forms.Select(attrs={'class': 'form-control'}),
            'respect': forms.Select(attrs={'class': 'form-control'}),
            'parental_support': forms.Select(attrs={'class': 'form-control'}),
            'attendance': forms.Select(attrs={'class': 'form-control'}),
            'assignment_completion': forms.Select(attrs={'class': 'form-control'}),
            'class_participation': forms.Select(attrs={'class': 'form-control'}),
            'time_management': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add help text and labels
        self.fields['days_present'].help_text = "Number of days the student was present"
        self.fields['days_late'].help_text = "Number of days the student was late"
        self.fields['remarks'].help_text = "Teacher's comments and observations about the student"

        # Set max value for attendance fields based on term days
        if self.instance and self.instance.term:
            term_days = self.instance.get_term_days()
            self.fields['days_present'].widget.attrs['max'] = term_days
            self.fields['days_late'].widget.attrs['max'] = term_days

@login_required
def test_list(request, school_slug):
    """
    View to list all tests created by the teacher
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    teacher = request.user.profile

    # Verify teacher belongs to this school using SchoolStaff
    from academics.models import SchoolStaff
    school_staff = SchoolStaff.objects.filter(
        staff=teacher,
        school=school,
        is_active=True
    ).first()

    if not school_staff:
        messages.error(request, "You don't have permission to view tests for this school.")
        return redirect('core:home')

    # Get the teacher's assigned standard using the new historical system
    from core.utils import get_current_year_and_term, get_current_teacher_assignment
    current_year, current_term, vacation_status = get_current_year_and_term(school=school)

    teacher_assignment = None
    teacher_standard = None
    if current_year:
        teacher_assignment = get_current_teacher_assignment(teacher, current_year)
        if teacher_assignment:
            teacher_standard = teacher_assignment.standard

    if not teacher_standard:
        messages.warning(request, "You are not assigned to any class. Please contact the administrator.")
        return redirect('core:home')

    # Get all tests created by this teacher
    tests = Test.objects.filter(created_by=teacher).order_by('-test_date')

    # Use the current_year we already got above (with school parameter)
    return render(request, 'reports/test_list.html', {
        'tests': tests,
        'school': school,
        'school_slug': school_slug,
        'teacher_standard': teacher_standard,
        'current_year': current_year
    })

@login_required
def test_create(request, school_slug):
    """
    View to create a new test
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    teacher = request.user.profile

    # Verify teacher belongs to this school using SchoolStaff
    school_staff = SchoolStaff.objects.filter(
        staff=teacher,
        school=school,
        is_active=True
    ).first()

    if not school_staff:
        messages.error(request, "You don't have permission to create tests for this school.")
        return redirect('core:home')

    # Get the teacher's assigned standard using the new historical system
    current_year, current_term, vacation_status = get_current_year_and_term(school=school)

    teacher_assignment = None
    teacher_standard = None
    if current_year:
        teacher_assignment = get_current_teacher_assignment(teacher, current_year)
        if teacher_assignment:
            teacher_standard = teacher_assignment.standard

    if not teacher_standard:
        messages.warning(request, "You are not assigned to any class. Please contact the administrator.")
        return redirect('reports:test_list', school_slug=school_slug)

    if not current_year:
        messages.warning(request, "No active academic year found. Please contact the administrator.")
        return redirect('reports:test_list', school_slug=school_slug)

    if request.method == 'POST':
        form = TestForm(request.POST, school=school, current_year=current_year)
        if form.is_valid():
            test = form.save(commit=False)
            test.created_by = teacher
            test.standard = teacher_standard
            test.save()

            messages.success(request, f"Test has been created successfully. Now add subjects to this test.")
            return redirect('reports:test_subject_add', school_slug=school_slug, test_id=test.id)
    else:
        form = TestForm(
            initial={'term': current_term, 'test_date': timezone.now().date()},
            school=school,
            current_year=current_year
        )

    import json
    return render(request, 'reports/test_form.html', {
        'form': form,
        'teacher_standard': teacher_standard,
        'current_year': current_year,
        'school': school,
        'school_slug': school_slug,
        'term_data_json': json.dumps(getattr(form, 'term_data', {}))
    })

@login_required
def test_detail(request, school_slug, test_id):
    """
    View to show test details
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    teacher = request.user.profile

    # Verify teacher belongs to this school using SchoolStaff
    school_staff = SchoolStaff.objects.filter(
        staff=teacher,
        school=school,
        is_active=True
    ).first()

    if not school_staff:
        messages.error(request, "You don't have permission to view tests for this school.")
        return redirect('core:home')

    test = get_object_or_404(Test, id=test_id)

    # Check if the teacher created this test
    if test.created_by != teacher:
        return HttpResponseForbidden("You don't have permission to view this test.")

    # Get all enabled subjects in this test
    test_subjects = TestSubject.objects.filter(test=test, enabled=True).select_related('standard_subject')

    # Get all scores for this test
    test_scores = TestScore.objects.filter(
        test_subject__test=test
    ).select_related('student', 'test_subject__standard_subject')

    # check if test has been finalized
    finalized = test.is_finalized

    # Organize scores by student and subject
    # Get students currently enrolled in the test's standard for the test's year
    from core.utils import get_current_student_enrollment

    # Get all students who have class assignments for this standard and year
    from academics.models import StandardEnrollment
    enrolled_student_ids = []

    # Get all students who have class assignment records for this standard and year
    potential_students = Student.objects.filter(
        standard_enrollments__standard=test.standard,
        standard_enrollments__year=test.term.year
    ).distinct()

    # Filter to only currently enrolled students
    for student in potential_students:
        current_enrollment = get_current_student_enrollment(student, test.term.year)
        if current_enrollment and current_enrollment.standard == test.standard:
            enrolled_student_ids.append(student.id)

    students = Student.objects.filter(id__in=enrolled_student_ids).order_by('last_name', 'first_name')

    student_scores = {}
    for student in students:
        student_scores[student.id] = {
            'student': student,
            'subjects': {}
        }

    for score in test_scores:
        student_id = score.student.id
        subject_id = score.test_subject.standard_subject.id  # Use StandardSubject ID instead

        if student_id in student_scores:
            student_scores[student_id]['subjects'][subject_id] = score

    # Prepare scores for JavaScript
    scores_data = {}
    for score in test_scores:
        key = f"{score.student_id}_{score.test_subject.standard_subject_id}"
        scores_data[key] = {
            'score': score.score,
            'max_score': score.test_subject.max_score,
            'percentage': round((score.score / score.test_subject.max_score) * 100, 1) if score.test_subject.max_score > 0 else 0
        }

    return render(request, 'reports/test_detail.html', {
        'test': test,
        'test_subjects': test_subjects,
        'finalized': finalized,
        'student_scores': student_scores.values(),
        'scores_data_json': json.dumps(scores_data),
        'school': school,
        'school_slug': school_slug
    })

@login_required
def test_edit(request, school_slug, test_id):
    """
    View to edit a test
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    teacher = request.user.profile

    # Verify teacher belongs to this school using SchoolStaff
    school_staff = SchoolStaff.objects.filter(
        staff=teacher,
        school=school,
        is_active=True
    ).first()

    if not school_staff:
        messages.error(request, "You don't have permission to edit tests for this school.")
        return redirect('core:home')

    test = get_object_or_404(Test, id=test_id)

    # Check if the teacher created this test
    if test.created_by != teacher:
        return HttpResponseForbidden("You don't have permission to edit this test.")

    # Check if test is finalized
    if test.is_finalized:
        messages.warning(request, "You cannot edit a test that has been finalized.")
        return redirect('reports:test_detail', school_slug=school_slug, test_id=test_id)

    # Get the teacher's assigned standard using the new historical system
    current_year, current_term, is_on_vacation = get_current_year_and_term(school=school)
    teacher_assignment = None
    teacher_standard = None
    if current_year:
        teacher_assignment = get_current_teacher_assignment(teacher, current_year)
        if teacher_assignment:
            teacher_standard = teacher_assignment.standard

    if request.method == 'POST':
        form = TestForm(request.POST, instance=test, school=school, current_year=current_year)
        if form.is_valid():
            form.save()
            messages.success(request, f"Test has been updated successfully.")
            return redirect('reports:test_detail', school_slug=school_slug, test_id=test.id)
    else:
        form = TestForm(instance=test, school=school, current_year=current_year)

    return render(request, 'reports/test_form.html', {
        'form': form,
        'test': test,
        'is_edit': True,
        'teacher_standard': teacher_standard,
        'school': school,
        'school_slug': school_slug,
        'term_data_json': json.dumps(getattr(form, 'term_data', {}))
    })

@login_required
def test_delete(request, school_slug, test_id):
    """
    View to delete a test
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    teacher = request.user.profile

    # Verify teacher belongs to this school using SchoolStaff
    school_staff = SchoolStaff.objects.filter(
        staff=teacher,
        school=school,
        is_active=True
    ).first()

    if not school_staff:
        messages.error(request, "You don't have permission to delete tests for this school.")
        return redirect('core:home')

    test = get_object_or_404(Test, id=test_id)

    # Check if the teacher created this test
    if test.created_by != teacher:
        return HttpResponseForbidden("You don't have permission to delete this test.")

    # Check if test is finalized
    if test.is_finalized:
        messages.warning(request, "You cannot delete a test that has been finalized.")
        return redirect('reports:test_detail', school_slug=school_slug, test_id=test_id)

    if request.method == 'POST':
        test.delete()
        messages.success(request, f"Test has been deleted successfully.")
        return redirect('reports:test_list', school_slug=school_slug)

    return render(request, 'reports/test_delete.html', {
        'test': test,
        'school': school,
        'school_slug': school_slug
    })

@login_required
def test_subject_add(request, school_slug, test_id):
    """
    View to manage subjects for a test (bulk enable/disable with max scores)
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    teacher = request.user.profile

    # Verify teacher belongs to this school using SchoolStaff
    school_staff = SchoolStaff.objects.filter(
        staff=teacher,
        school=school,
        is_active=True
    ).first()

    if not school_staff:
        messages.error(request, "You don't have permission to edit tests for this school.")
        return redirect('core:home')

    test = get_object_or_404(Test, id=test_id)

    # Check if the teacher created this test
    if test.created_by != teacher:
        return HttpResponseForbidden("You don't have permission to edit this test.")

    # Check if test is finalized
    if test.is_finalized:
        messages.warning(request, "You cannot modify subjects for a test that has been finalized.")
        return redirect('reports:test_detail', school_slug=school_slug, test_id=test_id)

    # Get all test subjects for this test (should already exist from auto-creation)
    test_subjects = TestSubject.objects.filter(test=test).select_related('standard_subject').order_by('standard_subject__subject_name')

    if request.method == 'POST':
        # Process form data directly from request.POST since we're using custom form fields
        updated_count = 0

        # Update each test subject based on form data
        for test_subject in test_subjects:
            enabled_field = f'enabled_{test_subject.id}'
            max_score_field = f'max_score_{test_subject.id}'

            # Get values from POST data
            new_enabled = enabled_field in request.POST
            new_max_score = request.POST.get(max_score_field, test_subject.max_score)

            try:
                new_max_score = int(new_max_score)
                if new_max_score < 1:
                    new_max_score = 100
            except (ValueError, TypeError):
                new_max_score = 100

            # Update if values changed
            if test_subject.enabled != new_enabled or test_subject.max_score != new_max_score:
                test_subject.enabled = new_enabled
                test_subject.max_score = new_max_score
                test_subject.save()
                updated_count += 1

        if updated_count > 0:
            messages.success(request, f"Updated {updated_count} subject(s) successfully.")
        else:
            messages.info(request, "No changes were made.")

        return redirect('reports:test_detail', school_slug=school_slug, test_id=test.id)
    else:
        form = BulkTestSubjectForm(test=test)

    return render(request, 'reports/test_subjects_bulk.html', {
        'form': form,
        'test': test,
        'test_subjects': test_subjects,
        'school': school,
        'school_slug': school_slug
    })

@login_required
def test_subject_edit(request, school_slug, test_id, subject_id):
    """
    View to edit a subject in a test
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    teacher = request.user.profile

    # Verify teacher belongs to this school using SchoolStaff
    school_staff = SchoolStaff.objects.filter(
        staff=teacher,
        school=school,
        is_active=True
    ).first()

    if not school_staff:
        messages.error(request, "You don't have permission to edit tests for this school.")
        return redirect('core:home')

    test = get_object_or_404(Test, id=test_id)
    test_subject = get_object_or_404(TestSubject, id=subject_id, test=test)

    # Check if the teacher created this test
    if test.created_by != teacher:
        return HttpResponseForbidden("You don't have permission to edit this test.")



    if request.method == 'POST':
        form = TestSubjectForm(request.POST, instance=test_subject)
        # Keep the same subject, only allow changing max_score
        form.fields['standard_subject'].disabled = True

        if form.is_valid():
            form.save()
            messages.success(request, f"Subject '{test_subject.standard_subject.subject_name}' has been updated.")
            return redirect('reports:test_detail', school_slug=school_slug, test_id=test.id)
    else:
        form = TestSubjectForm(instance=test_subject)
        # Keep the same subject, only allow changing max_score
        form.fields['standard_subject'].disabled = True

    return render(request, 'reports/test_subject_form.html', {
        'form': form,
        'test': test,
        'test_subject': test_subject,
        'is_edit': True,
        'school': school,
        'school_slug': school_slug
    })

@login_required
def test_subject_delete(request, school_slug, test_id, subject_id):
    """
    View to delete a subject from a test
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    teacher = request.user.profile

    # Verify teacher belongs to this school using SchoolStaff
    school_staff = SchoolStaff.objects.filter(
        staff=teacher,
        school=school,
        is_active=True
    ).first()

    if not school_staff:
        messages.error(request, "You don't have permission to edit tests for this school.")
        return redirect('core:home')

    test = get_object_or_404(Test, id=test_id)
    test_subject = get_object_or_404(TestSubject, id=subject_id, test=test)

    # Check if the teacher created this test
    if test.created_by != teacher:
        return HttpResponseForbidden("You don't have permission to edit this test.")



    if request.method == 'POST':
        subject_name = test_subject.standard_subject.subject_name
        test_subject.delete()
        messages.success(request, f"Subject '{subject_name}' has been removed from the test.")
        return redirect('reports:test_detail', school_slug=school_slug, test_id=test.id)

    return render(request, 'reports/test_subject_delete.html', {
        'test': test,
        'test_subject': test_subject,
        'school': school,
        'school_slug': school_slug
    })

@login_required
def test_scores(request, school_slug, test_id):
    """
    View to manage scores for a test - redirects to test detail page
    """
    # We don't need to use the request parameter, but it's required by the decorator
    return redirect('reports:test_detail', school_slug=school_slug, test_id=test_id)

@login_required
def test_scores_bulk(request, school_slug, test_id):
    """
    View to manage all scores for a test in a matrix format
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    teacher = request.user.profile

    # Verify teacher belongs to this school using SchoolStaff
    school_staff = SchoolStaff.objects.filter(
        staff=teacher,
        school=school,
        is_active=True
    ).first()

    if not school_staff:
        messages.error(request, "You don't have permission to manage scores for this school.")
        return redirect('core:home')

    test = get_object_or_404(Test, id=test_id)

    # check if test was already finalized
    if test.is_finalized:
        # redirect to test detail page
        messages.warning(request, "You cannot edit the scores for a test that has been finalized.")
        return redirect('reports:test_detail', school_slug=school_slug, test_id=test_id)
        

    # Check if the teacher created this test
    if test.created_by != teacher:
        return HttpResponseForbidden("You don't have permission to manage scores for this test.")

    # Get all enabled subjects for this test
    test_subjects = TestSubject.objects.filter(test=test, enabled=True).select_related('standard_subject').order_by('standard_subject__subject_name')

    if not test_subjects.exists():
        messages.warning(request, "Please enable subjects for this test before entering scores.")
        return redirect('reports:test_subject_add', school_slug=school_slug, test_id=test.id)

    # Get all students currently enrolled in this standard for the test's year
    from core.utils import get_current_student_enrollment

    # Get all students who have class assignment records for this standard and year
    potential_students = Student.objects.filter(
        standard_enrollments__standard=test.standard,
        standard_enrollments__year=test.term.year
    ).distinct()

    # Filter to only currently enrolled students using historical tracking
    enrolled_student_ids = []
    for student in potential_students:
        current_enrollment = get_current_student_enrollment(student, test.term.year)
        if current_enrollment and current_enrollment.standard == test.standard:
            enrolled_student_ids.append(student.id)

    students = Student.objects.filter(id__in=enrolled_student_ids).order_by('last_name', 'first_name')

    # Process form submission
    if request.method == 'POST':
        with transaction.atomic():
            updated_count = 0

            for student in students:
                for test_subject in test_subjects:
                    score_field = f'score_{student.id}_{test_subject.id}'
                    score_value = request.POST.get(score_field, 0)

                    try:
                        score_value = int(score_value) if score_value else 0
                        if score_value < 0:
                            score_value = 0
                        elif score_value > test_subject.max_score:
                            score_value = test_subject.max_score
                    except ValueError:
                        score_value = 0

                    # Get or create score for this student and subject
                    score, created = TestScore.objects.get_or_create(
                        test_subject=test_subject,
                        student=student,
                        defaults={'score': score_value}
                    )

                    if not created and score.score != score_value:
                        score.score = score_value
                        score.save()
                        updated_count += 1
                    elif created:
                        updated_count += 1

            messages.success(request, f"Updated scores for {updated_count} student-subject combinations.")
            return redirect('reports:test_detail', school_slug=school_slug, test_id=test.id)

    # Get existing scores organized by student and subject
    existing_scores = {}
    for score in TestScore.objects.filter(test_subject__in=test_subjects):
        key = f"{score.student_id}_{score.test_subject_id}"
        existing_scores[key] = score.score

    return render(request, 'reports/test_scores_bulk.html', {
        'test': test,
        'test_subjects': test_subjects,
        'students': students,
        'existing_scores_json': json.dumps(existing_scores),
        'school': school,
        'school_slug': school_slug
    })

@login_required
def subject_scores(request, school_slug, test_id, subject_id):
    """
    View to add/edit scores for a specific subject in a test
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    teacher = request.user.profile

    # Verify teacher belongs to this school using SchoolStaff
    school_staff = SchoolStaff.objects.filter(
        staff=teacher,
        school=school,
        is_active=True
    ).first()

    if not school_staff:
        messages.error(request, "You don't have permission to manage scores for this school.")
        return redirect('core:home')

    test = get_object_or_404(Test, id=test_id)
    test_subject = get_object_or_404(TestSubject, id=subject_id, test=test)

    # Check if the teacher created this test
    if test.created_by != teacher:
        return HttpResponseForbidden("You don't have permission to manage scores for this test.")



    # Get all students currently enrolled in this standard for the test's year
    from core.utils import get_current_student_enrollment

    # Get all students who have enrollment records for this standard and year
    potential_students = Student.objects.filter(
        standard_enrollments__standard=test.standard,
        standard_enrollments__year=test.term.year
    ).distinct()

    # Filter to only currently enrolled students using historical tracking
    enrolled_student_ids = []
    for student in potential_students:
        current_enrollment = get_current_student_enrollment(student, test.term.year)
        if current_enrollment and current_enrollment.standard == test.standard:
            enrolled_student_ids.append(student.id)

    students = Student.objects.filter(id__in=enrolled_student_ids).order_by('last_name', 'first_name')

    # Create or update scores for each student
    if request.method == 'POST':
        with transaction.atomic():
            for student in students:
                score_value = request.POST.get(f'score_{student.id}', 0)
                if not score_value:
                    score_value = 0

                try:
                    score_value = int(score_value)
                    if score_value < 0:
                        score_value = 0
                    elif score_value > test_subject.max_score:
                        score_value = test_subject.max_score
                except ValueError:
                    score_value = 0

                # Get or create score for this student
                score, created = TestScore.objects.get_or_create(
                    test_subject=test_subject,
                    student=student,
                    defaults={'score': score_value}
                )

                if not created:
                    score.score = score_value
                    score.save()



            messages.success(request, f"Scores for {test_subject.standard_subject.subject_name} have been saved successfully.")
            return redirect('reports:test_detail', school_slug=school_slug, test_id=test.id)

    # Get existing scores
    existing_scores = {}
    for score in TestScore.objects.filter(test_subject=test_subject):
        existing_scores[score.student_id] = score.score

    return render(request, 'reports/subject_scores.html', {
        'test': test,
        'test_subject': test_subject,
        'students': students,
        'existing_scores': existing_scores,
        'school': school,
        'school_slug': school_slug
    })

@login_required
def test_finalize(request, school_slug, test_id):
    """
    View to finalize a test
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    teacher = request.user.profile

    # Verify teacher belongs to this school using SchoolStaff
    school_staff = SchoolStaff.objects.filter(
        staff=teacher,
        school=school,
        is_active=True
    ).first()

    if not school_staff:
        messages.error(request, "You don't have permission to finalize tests for this school.")
        return redirect('core:home')

    test = get_object_or_404(Test, id=test_id)

    # Check if the teacher created this test
    if test.created_by != teacher:
        return HttpResponseForbidden("You don't have permission to finalize this test.")



    # Get all enabled subjects in this test
    test_subjects = TestSubject.objects.filter(test=test, enabled=True)

    if not test_subjects.exists():
        messages.warning(request, "Please add subjects to this test before finalizing.")
        return redirect('reports:test_subject_add', school_slug=school_slug, test_id=test.id)

    # Get all students currently enrolled in this standard for the test's year
    from core.utils import get_current_student_enrollment

    # Get all students who have enrollment records for this standard and year
    potential_students = Student.objects.filter(
        standard_enrollments__standard=test.standard,
        standard_enrollments__year=test.term.year
    ).distinct()

    # Filter to only currently enrolled students using historical tracking
    enrolled_student_ids = []
    for student in potential_students:
        current_enrollment = get_current_student_enrollment(student, test.term.year)
        if current_enrollment and current_enrollment.standard == test.standard:
            enrolled_student_ids.append(student.id)

    students = Student.objects.filter(id__in=enrolled_student_ids)

    # Check if scores have been entered for all students and subjects
    missing_scores = False
    for test_subject in test_subjects:
        for student in students:
            if not TestScore.objects.filter(test_subject=test_subject, student=student).exists():
                missing_scores = True
                break
        if missing_scores:
            break

    if missing_scores and request.method != 'POST':
        messages.warning(request, "Some students don't have scores for all subjects. Please complete all scores before finalizing.")
        return redirect('reports:test_scores', school_slug=school_slug, test_id=test.id)

    if request.method == 'POST':
        success, message = test.finalize_test(teacher)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect('reports:test_detail', school_slug=school_slug, test_id=test.id)

    return render(request, 'reports/test_finalize.html', {
        'test': test,
        'school': school,
        'school_slug': school_slug
    })

@login_required
def subject_list(request, school_slug):
    """
    View to list all subjects
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    # Get teacher's class from session (much faster than database queries)
    class_id, class_name, year_id = get_teacher_class_from_session(request)

    if not class_id:
        # Enhanced debugging: Check if teacher actually has an assignment
        teacher = request.user.profile
        from core.utils import get_current_year_and_term, get_current_teacher_assignment
        current_year, current_term, vacation_status = get_current_year_and_term(school=school)

        if current_year:
            teacher_assignment = get_current_teacher_assignment(teacher, current_year)
            if teacher_assignment:
                # Teacher has assignment but session is missing - this is a session bug
                messages.error(request, f"Session error detected. You are assigned to {teacher_assignment.standard} but session data is missing. Please log out and log back in.")
            else:
                # Teacher genuinely has no assignment
                messages.warning(request, "You are not assigned to any class. Please contact the administrator.")
        else:
            messages.error(request, "No academic year set up for this school. Please contact the administrator.")
        return redirect('core:home')

    # Get the teacher's standard and current year from session data
    try:
        from schools.models import Standard
        from academics.models import SchoolYear
        teacher_standard = Standard.objects.get(id=class_id)
        current_year = SchoolYear.objects.get(id=year_id)
    except (Standard.DoesNotExist, SchoolYear.DoesNotExist):
        messages.error(request, f"Invalid class assignment data (Class ID: {class_id}, Year ID: {year_id}). Please log out and log back in, or contact the administrator.")
        return redirect('core:home')

    # Verify the standard belongs to the current school
    if teacher_standard.school != school:
        messages.error(request, "You don't have permission to view subjects for this school.")
        return redirect('core:home')

    # Get subjects assigned to teacher's class for the current year
    assigned_subjects = StandardSubject.objects.filter(
        standard=teacher_standard,
        year=current_year
    )

    return render(request, 'reports/subject_list.html', {
        'assigned_subjects': assigned_subjects,
        'teacher_standard': teacher_standard,
        'current_year': current_year,
        'school': school,
        'school_slug': school_slug
    })

@login_required
def subject_create(request, school_slug):
    """
    View to create a new subject
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    teacher = request.user.profile

    # Get teacher's class from session (much faster than database queries)
    class_id, class_name, year_id = get_teacher_class_from_session(request)

    if not class_id:
        messages.warning(request, "You are not assigned to any class. Please contact the administrator.")
        return redirect('reports:subject_list', school_slug=school_slug)

    # Get the teacher's standard and current year from session data
    try:
        from schools.models import Standard
        from academics.models import SchoolYear
        teacher_standard = Standard.objects.get(id=class_id)
        current_year = SchoolYear.objects.get(id=year_id)
    except (Standard.DoesNotExist, SchoolYear.DoesNotExist):
        messages.error(request, "Invalid class assignment. Please contact the administrator.")
        return redirect('reports:subject_list', school_slug=school_slug)

    # Verify the standard belongs to the current school
    if teacher_standard.school != school:
        messages.error(request, "You don't have permission to create subjects for this school.")
        return redirect('core:home')

    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            # Create the StandardSubject directly (no separate Subject model)
            standard_subject = StandardSubject.objects.create(
                year=current_year,
                standard=teacher_standard,
                subject_name=form.cleaned_data['subject_name'],
                description=form.cleaned_data.get('description', ''),
                created_by=teacher
            )

            messages.success(request, f"Subject '{standard_subject.subject_name}' has been created and assigned to {teacher_standard}.")
            return redirect('reports:subject_list', school_slug=school_slug)
    else:
        form = SubjectForm()

    return render(request, 'reports/subject_form.html', {
        'form': form,
        'teacher_standard': teacher_standard,
        'current_year': current_year,
        'school': school,
        'school_slug': school_slug
    })

@login_required
def subject_edit(request, school_slug, subject_id):
    """
    View to edit a subject
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    teacher = request.user.profile

    # Get teacher's class from session (much faster than database queries)
    class_id, class_name, year_id = get_teacher_class_from_session(request)

    if not class_id:
        messages.warning(request, "You are not assigned to any class. Please contact the administrator.")
        return redirect('reports:subject_list', school_slug=school_slug)

    # Get the StandardSubject (not Subject)
    standard_subject = get_object_or_404(StandardSubject, id=subject_id)

    # Verify this subject belongs to the teacher's class (using session data)
    if standard_subject.standard.id != class_id or standard_subject.year.id != year_id:
        messages.error(request, "You can only edit subjects for your assigned class.")
        return redirect('reports:subject_list', school_slug=school_slug)

    # Verify the standard belongs to the current school
    if standard_subject.standard.school != school:
        messages.error(request, "You don't have permission to edit subjects for this school.")
        return redirect('core:home')

    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            standard_subject.subject_name = form.cleaned_data['subject_name']
            standard_subject.description = form.cleaned_data.get('description', '')
            standard_subject.save()
            messages.success(request, f"Subject '{standard_subject.subject_name}' has been updated successfully.")
            return redirect('reports:subject_list', school_slug=school_slug)
    else:
        # Pre-populate form with existing data
        form = SubjectForm(initial={
            'subject_name': standard_subject.subject_name,
            'description': standard_subject.description
        })

    return render(request, 'reports/subject_form.html', {
        'form': form,
        'subject': standard_subject,
        'is_edit': True,
        'school': school,
        'school_slug': school_slug
    })

@login_required
def subject_delete(request, school_slug, subject_id):
    """
    View to delete a subject
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can access this page.")
        return redirect('core:home')

    teacher = request.user.profile

    # Get teacher's class from session (much faster than database queries)
    class_id, class_name, year_id = get_teacher_class_from_session(request)

    if not class_id:
        messages.warning(request, "You are not assigned to any class. Please contact the administrator.")
        return redirect('reports:subject_list', school_slug=school_slug)

    # Get the StandardSubject (not Subject)
    standard_subject = get_object_or_404(StandardSubject, id=subject_id)

    # Verify this subject belongs to the teacher's class (using session data)
    if standard_subject.standard.id != class_id or standard_subject.year.id != year_id:
        messages.error(request, "You can only delete subjects for your assigned class.")
        return redirect('reports:subject_list', school_slug=school_slug)

    # Verify the standard belongs to the current school
    if standard_subject.standard.school != school:
        messages.error(request, "You don't have permission to delete subjects for this school.")
        return redirect('core:home')

    # Check if the subject is used in any tests
    if TestSubject.objects.filter(standard_subject=standard_subject).exists():
        messages.error(request, f"Cannot delete subject '{standard_subject.subject_name}' because it is used in one or more tests.")
        return redirect('reports:subject_list', school_slug=school_slug)

    if request.method == 'POST':
        subject_name = standard_subject.subject_name
        standard_subject.delete()
        messages.success(request, f"Subject '{subject_name}' has been deleted successfully.")
        return redirect('reports:subject_list', school_slug=school_slug)

    return render(request, 'reports/subject_delete.html', {
        'subject': standard_subject,
        'school': school,
        'school_slug': school_slug
    })

@login_required
def report_list(request, school_slug):
    """
    View to show available terms with reports (term selection page)
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check user permissions
    if not hasattr(request.user, 'profile'):
        messages.error(request, "Access denied.")
        return redirect('core:home')

    user_profile = request.user.profile

    # Check permissions based on user type
    if user_profile.user_type == 'teacher':
        # Teachers can only see reports for their assigned class
        class_id, class_name, year_id = get_teacher_class_from_session(request)

        if not class_id:
            messages.error(request, "You are not assigned to any class.")
            return redirect('core:home')

        # Get terms that have reports for students in teacher's class
        from core.utils import get_current_student_enrollment
        from schools.models import Standard

        teacher_standard = get_object_or_404(Standard, id=class_id)

        # Get terms that have reports for this standard
        available_terms = Term.objects.filter(
            year__school=school,
            student_reviews__student__standard_enrollments__standard=teacher_standard,
            student_reviews__student__standard_enrollments__year__id=year_id
        ).distinct().order_by('year__start_year', 'term_number')

    elif user_profile.user_type in ['principal', 'administration']:
        # Principals and admins see all terms with reports
        available_terms = Term.objects.filter(
            year__school=school,
            student_reviews__isnull=False
        ).distinct().order_by('year__start_year', 'term_number')
    else:
        messages.error(request, "Access denied.")
        return redirect('core:home')

    # Build data for table display
    terms_with_data = []

    if user_profile.user_type == 'teacher':
        # For teachers: show only their class data
        for term in available_terms:
            # Count reports for teacher's class only
            report_count = StudentTermReview.objects.filter(
                term=term,
                student__standard_enrollments__standard=teacher_standard,
                student__standard_enrollments__year=term.year
            ).count()

            # Count total students in teacher's class for this term
            student_count = StandardEnrollment.objects.filter(
                year=term.year,
                standard=teacher_standard,
                student__isnull=False
            ).count()

            if report_count > 0 or student_count > 0:  # Show terms with students even if no reports yet
                # Check finalization status
                finalized_reports = StudentTermReview.objects.filter(
                    term=term,
                    student__standard_enrollments__standard=teacher_standard,
                    student__standard_enrollments__year=term.year,
                    is_finalized=True
                ).count()
                all_finalized = finalized_reports == report_count and report_count > 0

                terms_with_data.append({
                    'term': term,
                    'class_name': teacher_standard.get_name_display(),
                    'class_id': teacher_standard.id,
                    'student_count': student_count,
                    'report_count': report_count,
                    'finalized_reports': finalized_reports,
                    'all_finalized': all_finalized,
                    'has_reports': report_count > 0
                })

    else:
        # For admins/principals: show all classes with reports
        from schools.models import Standard

        # Get all standards that have enrollments in terms with reports
        standards_with_reports = Standard.objects.filter(
            school=school,
            student_assignments__year__terms__student_reviews__isnull=False
        ).distinct()

        for term in available_terms:
            for standard in standards_with_reports:
                # Count reports for this standard and term
                report_count = StudentTermReview.objects.filter(
                    term=term,
                    student__standard_enrollments__standard=standard,
                    student__standard_enrollments__year=term.year
                ).count()

                # Count total students in this standard for this term
                student_count = StandardEnrollment.objects.filter(
                    year=term.year,
                    standard=standard,
                    student__isnull=False
                ).count()

                if report_count > 0 or student_count > 0:  # Show classes with students even if no reports yet
                    # Check finalization status
                    finalized_reports = StudentTermReview.objects.filter(
                        term=term,
                        student__standard_enrollments__standard=standard,
                        student__standard_enrollments__year=term.year,
                        is_finalized=True
                    ).count()
                    all_finalized = finalized_reports == report_count and report_count > 0

                    terms_with_data.append({
                        'term': term,
                        'class_name': standard.get_name_display(),
                        'class_id': standard.id,
                        'student_count': student_count,
                        'report_count': report_count,
                        'finalized_reports': finalized_reports,
                        'all_finalized': all_finalized,
                        'has_reports': report_count > 0
                    })

    return render(request, 'reports/report_list.html', {
        'terms_with_data': terms_with_data,
        'school': school,
        'school_slug': school_slug,
        'user_type': user_profile.user_type
    })

@login_required
def term_class_report_list(request, school_slug, term_id, class_id):
    """
    View to list all reports for a specific term and class
    """
    # Get the school, term, and class
    school = get_object_or_404(School, slug=school_slug)
    term = get_object_or_404(Term, id=term_id, year__school=school)
    from schools.models import Standard
    standard = get_object_or_404(Standard, id=class_id, school=school)

    # Check user permissions
    if not hasattr(request.user, 'profile'):
        messages.error(request, "Access denied.")
        return redirect('core:home')

    user_profile = request.user.profile

    # Base queryset
    reports = StudentTermReview.objects.filter(term=term).select_related('student').order_by('student__last_name', 'student__first_name')

    # Check permissions based on user type
    if user_profile.user_type == 'teacher':
        # Teachers can only see reports for their assigned class
        teacher_class_id, _, _ = get_teacher_class_from_session(request)

        if not teacher_class_id:
            messages.error(request, "You are not assigned to any class.")
            return redirect('core:home')

        # Verify teacher is accessing their own class
        if teacher_class_id != class_id:
            messages.error(request, "You can only view reports for your assigned class.")
            return redirect('core:home')

    elif user_profile.user_type not in ['principal', 'administration']:
        messages.error(request, "Access denied.")
        return redirect('core:home')

    # Filter reports to only students in the specified class for this term
    reports = StudentTermReview.objects.filter(
        term=term,
        student__standard_enrollments__standard=standard,
        student__standard_enrollments__year=term.year
    ).select_related('student').order_by('student__last_name', 'student__first_name')

    # Check finalization status
    total_reports = reports.count()
    finalized_reports = reports.filter(is_finalized=True).count()
    all_finalized = finalized_reports == total_reports and total_reports > 0

    return render(request, 'reports/term_class_report_list.html', {
        'reports': reports,
        'term': term,
        'standard': standard,
        'school': school,
        'school_slug': school_slug,
        'total_reports': total_reports,
        'finalized_reports': finalized_reports,
        'all_finalized': all_finalized,
        'user_profile': user_profile,
    })

@login_required
def report_detail(request, school_slug, report_id):
    """
    View to show detailed term report for a student
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check user permissions
    if not hasattr(request.user, 'profile'):
        messages.error(request, "Access denied.")
        return redirect('core:home')

    user_profile = request.user.profile

    # Get the report
    report = get_object_or_404(StudentTermReview, id=report_id)

    # Verify school access
    if report.term.year.school != school:
        messages.error(request, "Report not found in this school.")
        return redirect('core:home')

    # Check permissions based on user type
    if user_profile.user_type == 'teacher':
        # Teachers can only view reports for their assigned class
        class_id, class_name, year_id = get_teacher_class_from_session(request)

        if not class_id:
            messages.error(request, "You are not assigned to any class.")
            return redirect('core:home')

        # Check if this student is in teacher's class
        from core.utils import get_current_student_enrollment
        current_enrollment = get_current_student_enrollment(report.student, report.term.year)

        if not current_enrollment or current_enrollment.standard.id != class_id:
            messages.error(request, "You can only view reports for students in your assigned class.")
            return redirect('reports:report_list', school_slug=school_slug)

    elif user_profile.user_type not in ['principal', 'administration']:
        messages.error(request, "Access denied.")
        return redirect('core:home')

    # Get subject scores for this report
    subject_scores = report.subject_scores.all().select_related('standard_subject').order_by('standard_subject__subject_name')

    # Get previous and next students for navigation
    # Get the student's current enrollment to determine their class
    from core.utils import get_current_student_enrollment
    current_enrollment = get_current_student_enrollment(report.student, report.term.year)

    if current_enrollment:
        # Get all reports for the same term and class, ordered by student last name, first name
        all_reports = StudentTermReview.objects.filter(
            term=report.term,
            student__standard_enrollments__standard=current_enrollment.standard,
            student__standard_enrollments__year=report.term.year
        ).select_related('student').order_by('student__last_name', 'student__first_name')
    else:
        # Fallback to just this report if enrollment not found
        all_reports = [report]

    # Find current report position and get previous/next
    report_list = list(all_reports)
    current_index = None
    for i, r in enumerate(report_list):
        if r.id == report.id:
            current_index = i
            break

    previous_report = None
    next_report = None
    if current_index is not None:
        if current_index > 0:
            previous_report = report_list[current_index - 1]
        if current_index < len(report_list) - 1:
            next_report = report_list[current_index + 1]

    # Get teacher and principal information for signatures
    class_teacher = None
    school_principal = None

    if current_enrollment:
        # Get the teacher assigned to this student's class for this term
        from core.utils import get_current_standard_teacher
        teacher_assignment = get_current_standard_teacher(current_enrollment.standard, report.term.year)
        if teacher_assignment and teacher_assignment.teacher:
            class_teacher = teacher_assignment.teacher

    # Get the school principal
    if school.principal_user and hasattr(school.principal_user, 'profile'):
        school_principal = school.principal_user.profile

    return render(request, 'reports/report_detail.html', {
        'report': report,
        'subject_scores': subject_scores,
        'previous_report': previous_report,
        'next_report': next_report,
        'school': school,
        'school_slug': school_slug,
        'current_enrollment': current_enrollment,
        'user_profile': user_profile,
        'class_teacher': class_teacher,
        'school_principal': school_principal,
    })

@login_required
def generate_blank_reports(request, school_slug):
    """
    View to generate blank reports for a term and standard
    Only accessible by teachers, principals, and admins
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check user permissions
    if not hasattr(request.user, 'profile'):
        messages.error(request, "Access denied.")
        return redirect('core:home')

    user_profile = request.user.profile

    if user_profile.user_type not in ['teacher', 'principal', 'administration']:
        messages.error(request, "Access denied.")
        return redirect('core:home')

    # Get current year and available terms
    from core.utils import get_current_year_and_term
    current_year, current_term, vacation_status = get_current_year_and_term(school=school)

    if not current_year:
        messages.error(request, "No academic year set up for this school.")
        return redirect('core:home')

    available_terms = current_year.terms.all().order_by('term_number')

    # Get available standards based on user type
    if user_profile.user_type == 'teacher':
        # Teachers can only generate for their assigned class
        class_id, class_name, year_id = get_teacher_class_from_session(request)

        if not class_id:
            messages.error(request, "You are not assigned to any class.")
            return redirect('core:home')

        try:
            from schools.models import Standard
            available_standards = [Standard.objects.get(id=class_id)]
        except Standard.DoesNotExist:
            messages.error(request, "Invalid class assignment.")
            return redirect('core:home')
    else:
        # Principals and admins can generate for any class in their school
        from schools.models import Standard
        available_standards = Standard.objects.filter(school=school).order_by('name')

    if request.method == 'POST':
        term_id = request.POST.get('term')
        standard_id = request.POST.get('standard')

        try:
            selected_term = available_terms.get(id=term_id)
            selected_standard = None

            # Verify standard selection based on user permissions
            if user_profile.user_type == 'teacher':
                if int(standard_id) == available_standards[0].id:
                    selected_standard = available_standards[0]
            else:
                selected_standard = available_standards.get(id=standard_id)

            if not selected_standard:
                messages.error(request, "Invalid standard selection.")
                return redirect('reports:generate_blank_reports', school_slug=school_slug)

            # Generate blank reports
            reports_created = StudentTermReview.generate_blank_reports(selected_term, selected_standard)

            if reports_created > 0:
                messages.success(request, f"Generated {reports_created} blank reports for {selected_standard.get_name_display()} - {selected_term}.")
            else:
                messages.info(request, f"All reports already exist for {selected_standard.get_name_display()} - {selected_term}.")

            return redirect('reports:report_list', school_slug=school_slug)

        except Exception as e:
            messages.error(request, f"Error generating reports: {str(e)}")

    return render(request, 'reports/generate_blank_reports.html', {
        'available_terms': available_terms,
        'available_standards': available_standards,
        'current_year': current_year,
        'user_type': user_profile.user_type,
        'school': school,
        'school_slug': school_slug
    })

@login_required
def report_edit(request, school_slug, report_id):
    """
    View to edit a term report (attendance, behavioral ratings, remarks)
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check user permissions
    if not hasattr(request.user, 'profile'):
        messages.error(request, "Access denied.")
        return redirect('core:home')

    user_profile = request.user.profile

    # Get the report
    report = get_object_or_404(StudentTermReview, id=report_id)

    # Verify school access
    if report.term.year.school != school:
        messages.error(request, "Report not found in this school.")
        return redirect('core:home')

    # Get the student's current enrollment to determine their class
    from core.utils import get_current_student_enrollment
    current_enrollment = get_current_student_enrollment(report.student, report.term.year)

    # Check permissions based on user type
    if user_profile.user_type == 'teacher':
        # Teachers can only edit reports for their assigned class
        class_id, _, _ = get_teacher_class_from_session(request)

        if not class_id:
            messages.error(request, "You are not assigned to any class.")
            return redirect('core:home')

        # Check if this student is in teacher's class
        if not current_enrollment or current_enrollment.standard.id != class_id:
            messages.error(request, "You can only edit reports for students in your assigned class.")
            return redirect('reports:report_list', school_slug=school_slug)

    else:
        # Only teachers can edit reports
        messages.error(request, "Only teachers can edit reports.")
        return redirect('reports:report_detail', school_slug=school_slug, report_id=report_id)

    # Get next report for "Save and Next" functionality
    # Get all reports for the same term, ordered by student last name, first name
    all_reports = StudentTermReview.objects.filter(term=report.term).select_related('student').order_by('student__last_name', 'student__first_name')

    # Filter based on user permissions
    if user_profile.user_type == 'teacher':
        # Filter to teacher's class only
        from core.utils import get_current_student_enrollment
        teacher_reports = []
        for r in all_reports:
            current_enrollment = get_current_student_enrollment(r.student, report.term.year)
            if current_enrollment and current_enrollment.standard.id == class_id:
                teacher_reports.append(r)
        all_reports = teacher_reports

    # Find current report position and get next
    report_list = list(all_reports)
    current_index = None
    for i, r in enumerate(report_list):
        if r.id == report.id:
            current_index = i
            break

    next_report = None
    if current_index is not None and current_index < len(report_list) - 1:
        next_report = report_list[current_index + 1]

    if request.method == 'POST':
        form = StudentTermReviewForm(request.POST, instance=report)
        if form.is_valid():
            form.save()
            messages.success(request, f"Report for {report.student.get_full_name()} has been updated successfully.")

            # Check if "Save and Next" was clicked
            if 'save_and_next' in request.POST and next_report:
                return redirect('reports:report_edit', school_slug=school_slug, report_id=next_report.id)
            else:
                return redirect('reports:report_detail', school_slug=school_slug, report_id=report.id)
    else:
        form = StudentTermReviewForm(instance=report)

    return render(request, 'reports/report_edit.html', {
        'form': form,
        'report': report,
        'next_report': next_report,
        'school': school,
        'school_slug': school_slug,
        'current_enrollment': current_enrollment
    })


@login_required
def download_report_pdf(request, school_slug, report_id):
    """
    Download a pre-generated PDF for a single student report
    """
    # Get the report and related objects
    report = get_object_or_404(StudentTermReview, id=report_id)
    school = get_object_or_404(School, slug=school_slug)

    # Verify the report belongs to this school
    if report.term.year.school != school:
        messages.error(request, "Report not found for this school.")
        return redirect('core:home')

    # Check permissions - teachers can only access their own class reports
    user_profile = request.user.profile
    if user_profile.user_type == 'teacher':
        # Get current enrollment to check if this student is in teacher's class
        current_enrollment = StandardEnrollment.objects.filter(
            student=report.student,
            year=report.term.year,
            standard__isnull=False
        ).select_related('standard').order_by('-created_at').first()

        if not current_enrollment:
            messages.error(request, "Student enrollment not found.")
            return redirect('core:home')

        # Check if teacher is assigned to this standard
        from core.utils import get_current_teacher_assignment
        teacher_assignment = get_current_teacher_assignment(user_profile, report.term.year)
        if not teacher_assignment or teacher_assignment.standard != current_enrollment.standard:
            messages.error(request, "You don't have permission to access this report.")
            return redirect('core:home')

    # Check if report is finalized and PDF exists
    if not report.is_finalized:
        messages.error(request, "Report must be finalized before downloading. Please finalize the report first.")
        return redirect('reports:report_detail', school_slug=school_slug, report_id=report_id)

    if not report.pdf_generated or not report.pdf_path:
        messages.error(request, "PDF not available. Please contact your administrator.")
        return redirect('reports:report_detail', school_slug=school_slug, report_id=report_id)

    # Check if PDF file exists
    import os
    if not os.path.exists(report.pdf_path):
        messages.error(request, "PDF file not found. Please contact your administrator.")
        return redirect('reports:report_detail', school_slug=school_slug, report_id=report_id)

    # Serve the pre-generated PDF file
    try:
        with open(report.pdf_path, 'rb') as pdf_file:
            pdf_content = pdf_file.read()

        filename = report.get_pdf_filename()
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response
    except Exception as e:
        messages.error(request, f"Failed to download PDF: {str(e)}")
        return redirect('reports:report_detail', school_slug=school_slug, report_id=report_id)


@login_required
def bulk_generate_class_reports_pdf(request, school_slug, term_id, class_id):
    """
    Download pre-generated ZIP file containing all class reports
    """
    # Get the school, term, and class
    school = get_object_or_404(School, slug=school_slug)
    term = get_object_or_404(Term, id=term_id, year__school=school)
    standard = get_object_or_404(Standard, id=class_id, school=school)

    # Check user permissions
    if not hasattr(request.user, 'profile'):
        messages.error(request, "Access denied.")
        return redirect('core:home')

    user_profile = request.user.profile

    # Check permissions based on user type
    if user_profile.user_type == 'teacher':
        # Teachers can only generate reports for their assigned class
        class_id_session, class_name, _ = get_teacher_class_from_session(request)

        if not class_id_session or class_id_session != class_id:
            messages.error(request, "You can only generate reports for your assigned class.")
            return redirect('core:home')

    elif user_profile.user_type not in ['principal', 'administration']:
        messages.error(request, "Access denied.")
        return redirect('core:home')

    # Get all reports for this term and class
    reports = StudentTermReview.objects.filter(
        term=term,
        student__standard_enrollments__standard=standard,
        student__standard_enrollments__year=term.year
    ).select_related('student').order_by('student__last_name', 'student__first_name')

    if not reports.exists():
        messages.error(request, "No reports found for this class and term.")
        return redirect('reports:term_class_report_list',
                       school_slug=school_slug, term_id=term_id, class_id=class_id)

    # Check if reports are finalized
    finalized_reports = reports.filter(is_finalized=True)
    if not finalized_reports.exists():
        messages.error(request, "No finalized reports found. Please finalize reports before downloading.")
        return redirect('reports:term_class_report_list',
                       school_slug=school_slug, term_id=term_id, class_id=class_id)

    # Get the ZIP file path
    year_str = f"{term.year.start_year}-{term.year.start_year + 1}"
    term_str = f"Term{term.term_number}"
    class_name = standard.get_name_display().replace(' ', '_')
    zip_filename = f"{class_name}_{term_str}_{year_str}_Reports.zip"

    # Get the first report to determine directory structure
    first_report = finalized_reports.first()
    pdf_dir = first_report.get_pdf_directory(school_slug)

    if not pdf_dir:
        messages.error(request, "Unable to determine report directory.")
        return redirect('reports:term_class_report_list',
                       school_slug=school_slug, term_id=term_id, class_id=class_id)


    # Check if ZIP file exists
    import os
    zip_path = os.path.join(pdf_dir, zip_filename)
    if not os.path.exists(zip_path):
        messages.error(request, "Bulk download file not found. Please finalize reports first to generate the download file.")
        return redirect('reports:term_class_report_list',
                       school_slug=school_slug, term_id=term_id, class_id=class_id)

    # Serve the pre-generated ZIP file
    try:
        with open(zip_path, 'rb') as zip_file:
            response = HttpResponse(zip_file.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'

        messages.success(request, f"Downloaded {finalized_reports.count()} report PDFs.")
        return response

    except Exception as e:
        messages.error(request, f"Failed to download ZIP file: {str(e)}")
        return redirect('reports:term_class_report_list',
                       school_slug=school_slug, term_id=term_id, class_id=class_id)




@login_required
def finalize_class_reports(request, school_slug, term_id, class_id):
    """
    View to finalize all reports for a class/term and generate PDFs
    """
    # Get the school
    school = get_object_or_404(School, slug=school_slug)

    # Check if user is a teacher
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'teacher':
        messages.error(request, "Only teachers can finalize reports.")
        return redirect('core:home')

    teacher = request.user.profile

    # Verify teacher belongs to this school using SchoolStaff
    school_staff = SchoolStaff.objects.filter(
        staff=teacher,
        school=school,
        is_active=True
    ).first()

    if not school_staff:
        messages.error(request, "You don't have permission to finalize reports for this school.")
        return redirect('core:home')

    # Get the term and standard
    term = get_object_or_404(Term, id=term_id, year__school=school)
    standard = get_object_or_404(Standard, id=class_id)

    # Verify teacher is assigned to this standard
    from core.utils import get_current_teacher_assignment
    teacher_assignment = get_current_teacher_assignment(teacher, term.year)
    if not teacher_assignment or teacher_assignment.standard != standard:
        messages.error(request, "You don't have permission to finalize reports for this class.")
        return redirect('core:home')

    # Get all reports for this term and class
    reports = StudentTermReview.objects.filter(
        term=term,
        student__standard_enrollments__standard=standard,
        student__standard_enrollments__year=term.year
    ).select_related('student').distinct().order_by('student__last_name', 'student__first_name')

    if not reports.exists():
        messages.error(request, "No reports found for this class and term.")
        return redirect('reports:term_class_report_list',
                       school_slug=school_slug, term_id=term_id, class_id=class_id)

    # Check if any reports are already finalized
    finalized_count = reports.filter(is_finalized=True).count()
    total_count = reports.count()

    # Check readiness for finalization
    unready_reports = []
    for report in reports:
        if not report.is_finalized:
            can_finalize, message = report.can_be_finalized()
            if not can_finalize:
                unready_reports.append(f"{report.student.get_full_name()}: {message}")

    if request.method == 'POST':
        if unready_reports:
            messages.error(request, f"Cannot finalize reports. Please fix the following issues: {'; '.join(unready_reports[:5])}")
            return redirect('reports:finalize_class_reports',
                           school_slug=school_slug, term_id=term_id, class_id=class_id)

        # Finalize all reports
        success_count, error_count, error_messages = StudentTermReview.finalize_class_reports(
            term, standard, teacher
        )

        if success_count > 0:
            messages.success(request, f"Successfully finalized {success_count} reports.")

            # Generate PDFs for finalized reports
            try:
                finalized_reports = reports.filter(is_finalized=True)
                pdf_success_count = generate_class_report_pdfs(finalized_reports, school, school_slug, request)
                if pdf_success_count > 0:
                    messages.success(request, f"Generated {pdf_success_count} PDF reports.")

                    # Generate ZIP file for bulk download
                    zip_path = generate_class_reports_zip(finalized_reports, school_slug, term, standard)
                    if zip_path:
                        messages.success(request, "Bulk download ZIP file created successfully.")
                    else:
                        messages.warning(request, "Individual PDFs generated but ZIP file creation failed.")
            except Exception as e:
                messages.warning(request, f"Reports finalized but PDF generation failed: {str(e)}")

        if error_count > 0:
            for error_msg in error_messages[:5]:  # Show first 5 errors
                messages.error(request, error_msg)

        return redirect('reports:term_class_report_list',
                       school_slug=school_slug, term_id=term_id, class_id=class_id)

    return render(request, 'reports/finalize_class_reports.html', {
        'school': school,
        'school_slug': school_slug,
        'term': term,
        'standard': standard,
        'reports': reports,
        'total_count': total_count,
        'finalized_count': finalized_count,
        'unready_reports': unready_reports,
        'can_finalize': len(unready_reports) == 0 and finalized_count < total_count,
    })


def generate_class_report_pdfs(reports, school, school_slug, request):
    """
    Generate PDF files for a queryset of finalized reports
    Returns the number of successfully generated PDFs
    """
    if not WEASYPRINT_AVAILABLE:
        raise Exception("PDF generation is not available. WeasyPrint library is not installed.")

    success_count = 0

    for report in reports:
        try:
            # Generate PDF
            success, pdf_content, error_message = generate_report_pdf(
                report=report,
                school=school,
                school_slug=school_slug,
                request=request
            )

            if success and pdf_content:
                # Get the directory and filename
                pdf_dir = report.get_pdf_directory(school_slug)
                if not pdf_dir:
                    continue

                # Create directory if it doesn't exist
                os.makedirs(pdf_dir, exist_ok=True)

                # Save PDF to file
                pdf_filename = report.get_pdf_filename()
                pdf_path = os.path.join(pdf_dir, pdf_filename)

                with open(pdf_path, 'wb') as pdf_file:
                    pdf_file.write(pdf_content)

                # Update report with PDF info
                report.pdf_generated = True
                report.pdf_path = pdf_path
                report.pdf_generated_at = timezone.now()
                report.save()

                success_count += 1

        except Exception as e:
            # Log error but continue with other reports
            print(f"Failed to generate PDF for {report.student.get_full_name()}: {str(e)}")
            continue

    return success_count


def generate_class_reports_zip(reports, school_slug, term, standard):
    """
    Generate a ZIP file containing all finalized report PDFs for a class
    Returns the path to the ZIP file or None if failed
    """
    import os
    from django.conf import settings

    # Get the first report to determine directory structure
    first_report = reports.first()
    if not first_report:
        return None

    pdf_dir = first_report.get_pdf_directory(school_slug)
    if not pdf_dir:
        return None

    # Create ZIP filename
    year_str = f"{term.year.start_year}-{term.year.start_year + 1}"
    term_str = f"Term{term.term_number}"
    class_name = standard.get_name_display().replace(' ', '_')
    zip_filename = f"{class_name}_{term_str}_{year_str}_Reports.zip"
    zip_path = os.path.join(pdf_dir, zip_filename)

    try:
        import zipfile
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for report in reports:
                if report.pdf_generated and report.pdf_path and os.path.exists(report.pdf_path):
                    # Add PDF to ZIP with just the filename (not full path)
                    pdf_filename = report.get_pdf_filename()
                    zipf.write(report.pdf_path, pdf_filename)

        return zip_path
    except Exception as e:
        print(f"Failed to create ZIP file: {str(e)}")
        return None
