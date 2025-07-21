from django.utils import timezone
from django.db.models import Q
from academics.models import SchoolYear, Term

def get_current_year_and_term(school=None):
    """
    Get the current academic year and term based on the current date.

    IMPORTANT: This function requires a valid school parameter to work properly.
    If no school is provided, it will return (None, None, True) to indicate
    that no academic year can be determined.

    Args:
        school: School object to filter by (required for creating years)

    Returns:
        tuple: (current_year, current_term, is_on_vacation)
            - current_year: SchoolYear object or None if no school provided
            - current_term: int (1, 2, or 3) or None (None during vacation or no school)
            - is_on_vacation: bool (True if no school provided)
    """
    # If no school is provided, we cannot determine or create academic years
    if not school:
        return None, None, True

    today = timezone.now().date()

    # Step 1: Check if we're currently in an active term
    query = Q(start_date__lte=today, end_date__gte=today, year__school=school)
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
    Requires a valid school parameter.
    """
    # School is required for creating/managing academic years
    if not school:
        return None

    # Get all school years for this school, ordered by start year
    school_years = SchoolYear.objects.filter(school=school).order_by('start_year')

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
        year_id = request.session.get('current_year_id')  # Updated to use new session key
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


def get_current_standard_teacher(standard, school_year):
    """
    Get the current teacher assigned to a standard in a given school year.
    Returns the latest StandardTeacher record with a non-null teacher.

    This is the complement to get_current_teacher_assignment() and solves
    the asymmetry problem by checking from the standard's perspective.
    """
    from academics.models import StandardTeacher

    # Get the latest assignment record for this standard in this year
    latest_assignment = StandardTeacher.objects.filter(
        standard=standard,
        year=school_year
    ).order_by('-created_at').first()

    # Return the assignment if it has a teacher (not unassigned)
    if latest_assignment and latest_assignment.teacher:
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


def unassign_teacher(teacher, standard, school_year):
    """
    Unassign a teacher by creating bidirectional unassignment records.

    This creates two records to maintain historical integrity:
    1. Teacher record with standard=None (teacher is unassigned)
    2. Standard record with teacher=None (standard has no teacher)

    This ensures both sides of the relationship show the unassignment
    in their latest records, solving the asymmetry problem.

    Args:
        teacher: UserProfile instance of the teacher to unassign
        standard: Standard instance to unassign the teacher from
        school_year: SchoolYear instance for the academic year
    """
    from academics.models import StandardTeacher

    # Create teacher unassignment record
    StandardTeacher.objects.create(
        teacher=teacher,
        year=school_year,
        standard=None  # Teacher is unassigned from any standard
    )

    # Create standard unassignment record
    StandardTeacher.objects.create(
        teacher=None,  # Standard has no teacher assigned
        year=school_year,
        standard=standard
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


def user_has_school_access(user, school):
    """
    Check if a user has access to a specific school.

    Returns:
        tuple: (has_access, user_role, details)
        - has_access: Boolean indicating if user can access the school
        - user_role: String indicating the user's role in the school
        - details: Dict with additional information about the access
    """
    if not hasattr(user, 'profile'):
        return False, None, {'reason': 'No user profile'}

    user_profile = user.profile
    user_type = user_profile.user_type

    # Get current year for the school
    current_year, current_term, is_on_vacation = get_current_year_and_term(school=school)

    if user_type == 'principal':
        # Check if user is a principal of this school via SchoolStaff
        from academics.models import SchoolStaff
        principal_staff = SchoolStaff.objects.filter(
            staff=user_profile,
            school=school,
            is_active=True
        ).filter(
            staff__user_type='principal'
        ).first()

        if principal_staff:
            return True, 'principal', {
                'school_staff_id': principal_staff.id,
                'position': principal_staff.position or 'Principal'
            }
        else:
            return False, None, {'reason': 'Not a principal of this school'}

    elif user_type == 'administration':
        # Check if user is admin staff of this school via SchoolStaff
        from academics.models import SchoolStaff
        admin_staff = SchoolStaff.objects.filter(
            staff=user_profile,
            school=school,
            is_active=True
        ).filter(
            staff__user_type='administration'
        ).first()

        if admin_staff:
            return True, 'administration', {
                'school_staff_id': admin_staff.id,
                'position': admin_staff.position or 'Administrator'
            }
        else:
            return False, None, {'reason': 'Not an administrator of this school'}

    elif user_type == 'teacher':
        # Check if user is a teacher of this school via SchoolStaff
        from academics.models import SchoolStaff
        teacher_staff = SchoolStaff.objects.filter(
            staff=user_profile,
            school=school,
            is_active=True
        ).filter(
            staff__user_type='teacher'
        ).first()

        if teacher_staff:
            # Get current teacher assignment
            current_assignment = get_current_teacher_assignment(user_profile, current_year)
            return True, 'teacher', {
                'school_staff_id': teacher_staff.id,
                'position': teacher_staff.position or 'Teacher',
                'current_assignment': current_assignment,
                'assigned_class': current_assignment.standard if current_assignment else None
            }
        else:
            return False, None, {'reason': 'Not a teacher of this school'}

    else:
        return False, None, {'reason': f'User type {user_type} not supported'}


def setup_user_session(request, user):
    """
    Set up comprehensive user session with all necessary information at login.
    This is the single point where we determine user access and capabilities.
    """
    # Clear any existing session data first
    clear_user_session(request)

    if not hasattr(user, 'profile'):
        return False

    user_profile = user.profile

    # Set basic user information
    request.session['user_id'] = user.id
    request.session['user_type'] = user_profile.user_type

    # Find user's school association via SchoolStaff
    from academics.models import SchoolStaff
    school_staff = SchoolStaff.objects.filter(
        staff=user_profile,
        is_active=True
    ).select_related('school').first()

    if school_staff:
        school = school_staff.school

        # Set school information
        request.session['user_school_id'] = school.id
        request.session['user_school_slug'] = school.slug
        request.session['user_role'] = user_profile.user_type
        request.session['user_position'] = school_staff.position or user_profile.user_type.title()

        # Get current academic year and term information
        current_year, current_term, is_on_vacation = get_current_year_and_term(school=school)

        if current_year:
            request.session['current_year_id'] = current_year.id
            request.session['current_term'] = current_term
            request.session['is_on_vacation'] = is_on_vacation

            # For teachers, get their current class assignment
            if user_profile.user_type == 'teacher':
                teacher_assignment = get_current_teacher_assignment(user_profile, current_year)
                if teacher_assignment:
                    request.session['teacher_class_id'] = teacher_assignment.standard.id
                    request.session['teacher_class_name'] = str(teacher_assignment.standard)
        else:
            # School exists but no academic year set up yet
            request.session['current_year_id'] = None
            request.session['current_term'] = None
            request.session['is_on_vacation'] = None
    else:
        # User not associated with any school
        request.session['user_school_id'] = None
        request.session['user_school_slug'] = None
        request.session['user_role'] = user_profile.user_type
        request.session['current_year_id'] = None
        request.session['current_term'] = None
        request.session['is_on_vacation'] = None

    return True


def clear_user_session(request):
    """
    Clear all user session variables.
    """
    session_keys = [
        'user_id', 'user_type', 'user_school_id', 'user_school_slug',
        'user_role', 'user_position', 'current_year_id', 'current_term',
        'is_on_vacation', 'teacher_class_id', 'teacher_class_name'
    ]
    for key in session_keys:
        request.session.pop(key, None)


def get_user_session_info(request):
    """
    Get comprehensive user session information.
    Returns a dictionary with all session data.
    """
    return {
        'user_id': request.session.get('user_id'),
        'user_type': request.session.get('user_type'),
        'user_school_id': request.session.get('user_school_id'),
        'user_school_slug': request.session.get('user_school_slug'),
        'user_role': request.session.get('user_role'),
        'user_position': request.session.get('user_position'),
        'current_year_id': request.session.get('current_year_id'),
        'current_term': request.session.get('current_term'),
        'is_on_vacation': request.session.get('is_on_vacation'),
        'teacher_class_id': request.session.get('teacher_class_id'),
        'teacher_class_name': request.session.get('teacher_class_name'),
    }


def user_has_school_access_session(request, school_slug):
    """
    Check if user has access to a specific school using session data.
    Much faster than database queries.
    """
    session_school_slug = request.session.get('user_school_slug')
    return session_school_slug == school_slug


def user_can_access_view(request, required_role=None, required_school_slug=None):
    """
    Universal access control function using session data.

    Args:
        request: Django request object
        required_role: Required user role ('principal', 'administration', 'teacher') or list of roles
        required_school_slug: Required school slug for access

    Returns:
        tuple: (can_access, redirect_url, message)
    """
    if not request.user.is_authenticated:
        return False, 'login', 'Please log in to continue.'

    session_info = get_user_session_info(request)

    # Check if user has basic session setup
    if not session_info['user_id']:
        return False, 'core:home', 'Session expired. Please log in again.'

    # Check role requirements
    if required_role:
        user_role = session_info['user_role']
        if isinstance(required_role, list):
            if user_role not in required_role:
                return False, 'core:home', f'Access restricted to {", ".join(required_role)} only.'
        else:
            if user_role != required_role:
                return False, 'core:home', f'Access restricted to {required_role} only.'

    # Check school access requirements
    if required_school_slug:
        if not session_info['user_school_slug']:
            if session_info['user_role'] == 'principal':
                return False, 'core:register_school', 'Please register your school first.'
            else:
                return False, 'core:home', 'You are not associated with any school. Please contact your principal.'

        if session_info['user_school_slug'] != required_school_slug:
            return False, 'core:home', 'You do not have access to this school.'

    return True, None, None
