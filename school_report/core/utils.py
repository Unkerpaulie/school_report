from django.utils import timezone
from django.db.models import Q
from academics.models import SchoolYear, Term

def get_current_year_and_term(school=None):
    """
    Get the current academic year and term based on the current date.

    The current year should NEVER be None. Logic:
    - During terms: return current year and current term number
    - During vacation (between terms): return current year and None for term
    - After term 3 ends: automatically advance to next year (create if needed)
    - If no years exist: create default year with terms

    Args:
        school: School object to filter by (optional). If None, returns the first match across all schools.

    Returns:
        tuple: (current_year, current_term, is_on_vacation)
            - current_year: SchoolYear object (never None)
            - current_term: int (1, 2, or 3) or None (None during vacation)
            - is_on_vacation: bool
    """
    today = timezone.now().date()

    # Step 1: Check if we're currently in an active term
    query = Q(start_date__lte=today, end_date__gte=today)
    if school:
        query &= Q(year__school=school)

    current_terms = Term.objects.filter(query).select_related('year')

    if current_terms.exists():
        # We're in an active term
        term = current_terms.first()
        return term.year, term.term_number, False

    # Step 2: We're not in an active term, determine which year we should be in
    current_year = _determine_current_year(school, today)

    # Step 3: Return the year with no active term (vacation)
    return current_year, None, True


def _determine_current_year(school, today):
    """
    Determine which academic year we should be in based on today's date.
    This ensures current_year is never None.
    """
    # Get all school years for this school, ordered by start year
    if school:
        school_years = SchoolYear.objects.filter(school=school).order_by('start_year')
    else:
        school_years = SchoolYear.objects.all().order_by('start_year')

    if not school_years.exists():
        # No school years exist, create the first one
        return _create_default_school_year(school, today)

    # Check each year to see if today falls within its span
    for year in school_years:
        terms = Term.objects.filter(year=year).order_by('term_number')
        if terms.exists():
            first_term = terms.first()
            last_term = terms.last()

            # If today is within this academic year span (including vacation periods)
            if first_term.start_date <= today <= last_term.end_date:
                return year

    # Check if we're past the last academic year
    latest_year = school_years.last()
    latest_terms = Term.objects.filter(year=latest_year).order_by('term_number')

    if latest_terms.exists():
        last_term = latest_terms.last()
        if today > last_term.end_date:
            # We're past the last term, create next year
            return _create_next_school_year(school, latest_year)

    # Fallback: return the latest year (shouldn't normally reach here)
    return latest_year


def _create_next_school_year(school, previous_year):
    """
    Create the next school year with default terms.
    """
    next_start_year = previous_year.start_year + 1

    # Create the next school year
    next_year = SchoolYear.objects.create(
        school=school,
        start_year=next_start_year
    )

    # Create default terms for Caribbean school system (Sept-July)
    _create_default_terms(next_year, next_start_year)

    return next_year


def _create_default_school_year(school, today):
    """
    Create a default school year for schools that don't have any years set up.
    """
    import datetime

    # Determine the appropriate start year based on current date
    # Caribbean school year typically starts in September
    if today.month >= 9:  # Sept-Dec: current calendar year
        start_year = today.year
    else:  # Jan-Aug: previous calendar year (still in same academic year)
        start_year = today.year - 1

    # Create the school year
    school_year = SchoolYear.objects.create(
        school=school,
        start_year=start_year
    )

    # Create default terms
    _create_default_terms(school_year, start_year)

    return school_year


def _create_default_terms(school_year, start_year):
    """
    Create default terms for a school year (Caribbean system: Sept-July).
    """
    import datetime

    # Default Caribbean school year terms
    terms_data = [
        {
            'term_number': 1,
            'start_date': datetime.date(start_year, 9, 1),
            'end_date': datetime.date(start_year, 12, 15),
            'school_days': 70
        },
        {
            'term_number': 2,
            'start_date': datetime.date(start_year + 1, 1, 8),
            'end_date': datetime.date(start_year + 1, 4, 12),
            'school_days': 65
        },
        {
            'term_number': 3,
            'start_date': datetime.date(start_year + 1, 4, 22),
            'end_date': datetime.date(start_year + 1, 7, 5),
            'school_days': 55
        }
    ]

    # Create the terms
    for term_data in terms_data:
        Term.objects.create(
            year=school_year,
            term_number=term_data['term_number'],
            start_date=term_data['start_date'],
            end_date=term_data['end_date'],
            school_days=term_data['school_days']
        )


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
