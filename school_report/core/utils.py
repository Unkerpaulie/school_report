from django.utils import timezone
from django.db.models import Q
from academics.models import SchoolYear, Term

def get_current_year_and_term(school=None):
    """
    Get the current academic year and term based on the current date.

    Args:
        school: School object to filter by (optional). If None, returns the first match across all schools.

    Returns:
        tuple: (current_year, current_term, is_on_vacation)
            - current_year: SchoolYear object or None
            - current_term: int (1, 2, or 3) or None
            - is_on_vacation: bool
    """
    today = timezone.now().date()

    # Build the query for terms that include today's date
    query = Q(start_date__lte=today, end_date__gte=today)

    # If school is specified, filter by school
    if school:
        query &= Q(year__school=school)

    # Get all terms that include today's date
    current_terms = Term.objects.filter(query).select_related('year')

    if current_terms.exists():
        term = current_terms.first()
        return term.year, term.term_number, False

    # If no terms found for the current date, check if we have any school year for this school
    # and return the most recent one (fallback for when terms aren't set up properly)
    if school:
        fallback_year = SchoolYear.objects.filter(school=school).order_by('-start_year').first()
        if fallback_year:
            return fallback_year, None, True

    # If no terms found, we're on vacation or no school year exists
    return None, None, True


def get_teacher_class_from_session(request):
    """
    Get teacher's assigned class from session.
    Returns (class_id, class_name, school_year_id) or (None, None, None)
    """
    if hasattr(request.user, 'profile') and request.user.profile.user_type == 'teacher':
        class_id = request.session.get('teacher_class_id')
        class_name = request.session.get('teacher_class_name')
        year_id = request.session.get('teacher_school_year_id')
        return class_id, class_name, year_id
    return None, None, None


def set_teacher_class_session(request, standard, school_year):
    """
    Set teacher's class information in session.
    """
    request.session['teacher_class_id'] = standard.id
    request.session['teacher_class_name'] = str(standard)
    request.session['teacher_school_year_id'] = school_year.id


def clear_teacher_session(request):
    """
    Clear teacher session variables.
    """
    keys_to_remove = ['teacher_class_id', 'teacher_class_name', 'teacher_school_year_id']
    for key in keys_to_remove:
        request.session.pop(key, None)


def get_current_teacher_assignment(teacher, school_year):
    """
    Get the current (latest) assignment for a teacher in a given year.
    Returns StandardTeacher object or None.
    """
    from academics.models import StandardTeacher

    latest_assignment = StandardTeacher.objects.filter(
        teacher=teacher,
        year=school_year
    ).order_by('-created_at').first()

    # Return assignment only if it has a standard (not unassigned)
    if latest_assignment and latest_assignment.standard:
        return latest_assignment
    return None


def get_current_student_enrollment(student, school_year):
    """
    Get the current (latest) enrollment for a student in a given year.
    Returns Enrollment object or None.
    """
    from academics.models import Enrollment

    latest_enrollment = Enrollment.objects.filter(
        student=student,
        year=school_year
    ).order_by('-created_at').first()

    # Return enrollment only if it has a standard (not unenrolled)
    if latest_enrollment and latest_enrollment.standard:
        return latest_enrollment
    return None


def unassign_teacher(teacher, school_year):
    """
    Unassign a teacher by creating a new record with null standard.
    """
    from academics.models import StandardTeacher

    StandardTeacher.objects.create(
        teacher=teacher,
        year=school_year,
        standard=None  # Null = unassigned
    )


def unenroll_student(student, school_year):
    """
    Unenroll a student by creating a new record with null standard.
    """
    from academics.models import Enrollment

    Enrollment.objects.create(
        student=student,
        year=school_year,
        standard=None  # Null = unenrolled
    )
