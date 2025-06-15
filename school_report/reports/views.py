from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.db import transaction
from django.forms import modelformset_factory
from academics.models import StandardSubject, StandardTeacher, SchoolStaff, SchoolYear
from schools.models import Student, School, Standard
from core.models import UserProfile
from core.utils import get_current_year_and_term, get_teacher_class_from_session, get_current_teacher_assignment
import json
from .models import Test, TestSubject, TestScore

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
    current_year, current_term, is_on_vacation = get_current_year_and_term(school=school)

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

    # Get current academic year and term
    current_year, current_term, is_on_vacation = get_current_year_and_term()

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
    current_year, current_term, is_on_vacation = get_current_year_and_term(school=school)

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

    # Organize scores by student and subject
    # Get students currently enrolled in the test's standard for the test's year
    from core.utils import get_current_student_enrollment

    # Get all students who have enrollments for this standard and year
    from academics.models import Enrollment
    enrolled_student_ids = []

    # Get all students who have enrollment records for this standard and year
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
        messages.success(request, f"Test has been finalized successfully.")
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
        current_year, current_term, is_on_vacation = get_current_year_and_term(school=school)

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
