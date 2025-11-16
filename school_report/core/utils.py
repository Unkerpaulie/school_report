from django.utils import timezone
from django.db.models import Q
from academics.models import SchoolYear, Term

def get_current_year_and_term(school=None):
    """
    Get the current academic year and term based on the current date.

    IMPORTANT: This function requires a valid school parameter to work properly.
    If no school is provided, it will return (None, None, None) to indicate
    that no academic year can be determined.

    Args:
        school: School object to filter by (required for creating years)

    Returns:
        tuple: (current_year, current_term, vacation_status)
            - current_year: SchoolYear object or None if no school provided
            - current_term: int (1, 2, or 3) or None (None during vacation or no school)
            - vacation_status: str or None
                - None: In active term or no school provided
                - 'christmas': Between term 1 and term 2 (Christmas vacation)
                - 'easter': Between term 2 and term 3 (Easter vacation)
                - 'summer': Between term 3 and next year's term 1 (Summer vacation)
    """
    # If no school is provided, we cannot determine or create academic years
    if not school:
        return None, None, None

    today = timezone.now().date()
    # today = timezone.datetime(2025, 1, 10).date() # to create data for previous year

    # Step 1: Check if we're currently in an active term
    query = Q(start_date__lte=today, end_date__gte=today, year__school=school)
    current_terms = Term.objects.filter(query).select_related('year')

    if current_terms.exists():
        # We're in an active term
        term = current_terms.first()
        return term.year, term.term_number, None

    # Step 2: We're not in an active term, determine which year we should be in
    current_year = _determine_current_year(school, today)

    # Step 3: Determine which vacation period we're in
    vacation_status = _determine_vacation_period(school, current_year, today)

    # Step 4: Return the year with vacation status
    return current_year, None, vacation_status


def _determine_vacation_period(school, current_year, today):
    """
    Determine which vacation period we're currently in.

    Args:
        school: School object
        current_year: SchoolYear object (guaranteed to exist)
        today: Current date

    Returns:
        str or None: 'christmas', 'easter', 'summer', or None if not in vacation
    """
    if not current_year:
        return None

    # Get all terms for the current year, ordered by term number
    terms = Term.objects.filter(year=current_year).order_by('term_number')

    if not terms.exists():
        return None

    term_list = list(terms)

    # Check if we're between term 1 and term 2 (Christmas vacation)
    if len(term_list) >= 2:
        term1_end = term_list[0].end_date
        term2_start = term_list[1].start_date
        if term1_end < today < term2_start:
            return 'christmas'

    # Check if we're between term 2 and term 3 (Easter vacation)
    if len(term_list) >= 3:
        term2_end = term_list[1].end_date
        term3_start = term_list[2].start_date
        if term2_end < today < term3_start:
            return 'easter'

    # Check if we're in summer vacation (current year is next academic year, but before Term 1)
    # This happens when we've transitioned to the next academic year after Term 3 ended
    if len(term_list) >= 1:
        term1_start = term_list[0].start_date
        if today < term1_start:
            # We're in the academic year but before Term 1 starts = Summer vacation
            # This means we transitioned from previous year's Term 3 end
            return 'summer'

    return None


def _determine_current_year(school, today):
    """
    Determine which academic year we should be in based on today's date.

    Key Logic: Once Term 3 of an academic year ends, we immediately transition
    to the next academic year (even during summer vacation). This allows proper
    student advancement and administrative preparation for the new year.

    Requires a valid school parameter.
    """
    # School is required for creating/managing academic years
    if not school:
        return None

    # Get all school years for this school, ordered by start year
    school_years = SchoolYear.objects.filter(school=school).order_by('start_year')

    if not school_years.exists():
        # No school years exist, create the first one
        # Determine the appropriate start year based on current date
        # Caribbean school year typically starts in September
        # but our system current year includes preceding summer vacation which starts in July
        if today.month >= 7:  # July-Dec: current calendar year
            start_year = today.year
        else:  # Jan-Jun: previous calendar year (still in same academic year)
            start_year = today.year - 1
        return _create_school_year(school, start_year)

    # Check each year to see if today falls within its active period
    for year in school_years:
        terms = Term.objects.filter(year=year).order_by('term_number')
        if terms.exists():
            first_term = terms.first()
            last_term = terms.last()

            # CRITICAL: Academic year is "current" from Term 1 start until Term 3 END
            # After Term 3 ends, we transition to the next academic year
            if first_term.start_date <= today <= last_term.end_date:
                return year

    # If we're past the last term of any year, determine next year
    latest_year = school_years.last()
    latest_terms = Term.objects.filter(year=latest_year).order_by('term_number')

    if latest_terms.exists():
        last_term = latest_terms.last()
        if today > last_term.end_date:
            # We're past the last term - transition to next academic year
            # Check if next year already exists
            next_year = SchoolYear.objects.filter(
                school=school,
                start_year=latest_year.start_year + 1
            ).first()

            if next_year:
                # Next year exists, return it as current
                return next_year
            else:
                # Next year doesn't exist, create it
                return _create_school_year(school, latest_year.start_year + 1)

    # Fallback: return the latest year (shouldn't normally reach here)
    return latest_year


def _create_school_year(school, start_year):
    """
    Create a school year.
    """
    import datetime

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
    Get the current (latest) class assignment for a student in a given year.
    Returns StandardEnrollment object or None.
    """
    from academics.models import StandardEnrollment

    latest_enrollment = StandardEnrollment.objects.filter(
        student=student,
        year=school_year
    ).order_by('-created_at').first()

    # Return enrollment only if it has a standard (not unassigned)
    if latest_enrollment and latest_enrollment.standard:
        return latest_enrollment
    return None


def get_next_term_start_date(current_term):
    """
    Get the start date of the next term after the given term.

    Args:
        current_term: Term object

    Returns:
        date: Start date of the next term, or None if no next term exists
    """
    if not current_term:
        return None

    # Try to get the next term in the same year
    next_term_in_year = Term.objects.filter(
        year=current_term.year,
        term_number=current_term.term_number + 1
    ).first()

    if next_term_in_year:
        return next_term_in_year.start_date

    # If no next term in current year, get Term 1 of next year
    next_year = SchoolYear.objects.filter(
        school=current_term.year.school,
        start_year=current_term.year.start_year + 1
    ).first()

    if next_year:
        next_year_term1 = Term.objects.filter(
            year=next_year,
            term_number=1
        ).first()

        if next_year_term1:
            return next_year_term1.start_date

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


def unassign_all_teachers_for_school(school, from_year):
    """
    Automatically unassign all teachers from their standards for a school year.
    This is triggered when summer vacation begins.

    Args:
        school: School instance
        from_year: SchoolYear instance to unassign teachers from
    """
    from academics.models import StandardTeacher
    from schools.models import Standard

    # Get all current teacher assignments for this school year
    current_assignments = StandardTeacher.objects.filter(
        year=from_year,
        standard__school=school,
        standard__isnull=False,  # Only get actual assignments, not unassignment records
        teacher__isnull=False
    ).select_related('teacher', 'standard')

    # Get the latest assignment for each teacher-standard pair
    processed_pairs = set()
    for assignment in current_assignments.order_by('-created_at'):
        pair_key = (assignment.teacher_id, assignment.standard_id)
        if pair_key not in processed_pairs:
            # Check if this is still the latest assignment (not already unassigned)
            latest_teacher_record = StandardTeacher.objects.filter(
                teacher=assignment.teacher,
                year=from_year
            ).order_by('-created_at').first()

            latest_standard_record = StandardTeacher.objects.filter(
                standard=assignment.standard,
                year=from_year
            ).order_by('-created_at').first()

            # Only unassign if both sides still show assignment
            if (latest_teacher_record and latest_teacher_record.standard == assignment.standard and
                latest_standard_record and latest_standard_record.teacher == assignment.teacher):

                unassign_teacher(assignment.teacher, assignment.standard, from_year)
                processed_pairs.add(pair_key)


def unenroll_student(student, school_year):
    """
    Unassign a student from their class by creating a new record with null standard.
    """
    from academics.models import StandardEnrollment

    StandardEnrollment.objects.create(
        student=student,
        year=school_year,
        standard=None  # Null = unassigned
    )


def handle_summer_vacation_triggers(school):
    """
    Handle system triggers when summer vacation begins.

    This function:
    1. Verifies the next academic year exists
    2. Creates/updates the AcademicTransition record

    Note: Teacher unassignment is handled manually by administration.

    Args:
        school: School instance

    Returns:
        tuple: (transition_record, actions_taken)
    """
    from academics.models import SchoolYear, AcademicTransition
    from django.utils import timezone

    actions_taken = []

    # Get current year and next year
    current_year, _, vacation_status = get_current_year_and_term(school=school)

    if vacation_status != 'summer':
        return None, []

    # Find the previous year (the one we're transitioning from)
    from_year = SchoolYear.objects.filter(
        school=school,
        start_year=current_year.start_year - 1
    ).first()

    if not from_year:
        return None, []

    # Get or create transition record
    transition, created = AcademicTransition.objects.get_or_create(
        school=school,
        from_year=from_year,
        to_year=current_year,
        defaults={
            'created_by': None,  # System-created
            'started_at': timezone.now()
        }
    )

    if created:
        actions_taken.append("Created academic transition record")

    # Verify next year exists (it should since we're in summer vacation)
    if not transition.next_year_verified:
        # The fact that we have current_year means next year exists
        transition.next_year_verified = True
        actions_taken.append("Verified next academic year exists")

    # Mark teachers as "unassigned" since this is now handled manually
    if not transition.teachers_unassigned:
        transition.teachers_unassigned = True
        transition.teachers_unassigned_at = timezone.now()
        actions_taken.append("Teacher reassignment ready (handled manually)")

    # Save the transition record
    if actions_taken:
        transition.save()

    return transition, actions_taken


def get_student_school_enrollment(student, school):
    """
    Get the school enrollment record for a student at a specific school.
    Returns SchoolEnrollment object or None.
    """
    from academics.models import SchoolEnrollment

    return SchoolEnrollment.objects.filter(
        student=student,
        school=school,
        is_active=True
    ).first()


def enroll_student_in_school(student, school, enrollment_date=None):
    """
    Enroll a student in a school (create SchoolEnrollment record).
    This is separate from class assignment.
    """
    from academics.models import SchoolEnrollment
    from django.utils import timezone

    if not enrollment_date:
        enrollment_date = timezone.now().date()

    school_enrollment, created = SchoolEnrollment.objects.get_or_create(
        student=student,
        school=school,
        defaults={
            'enrollment_date': enrollment_date,
            'is_active': True
        }
    )

    return school_enrollment, created


def graduate_student(student, school, graduation_date=None):
    """
    Mark a student as graduated from a school.
    """
    from django.utils import timezone

    if not graduation_date:
        graduation_date = timezone.now().date()

    school_enrollment = get_student_school_enrollment(student, school)
    if school_enrollment:
        school_enrollment.is_active = False
        school_enrollment.graduation_date = graduation_date
        school_enrollment.save()
        return True
    return False


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
    current_year, current_term, vacation_status = get_current_year_and_term(school=school)

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
        current_year, current_term, vacation_status = get_current_year_and_term(school=school)

        if current_year:
            request.session['current_year_id'] = current_year.id
            request.session['current_term'] = current_term
            request.session['vacation_status'] = vacation_status
            # Keep backward compatibility for is_on_vacation
            request.session['is_on_vacation'] = vacation_status is not None

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
            request.session['vacation_status'] = None
            request.session['is_on_vacation'] = None
    else:
        # User not associated with any school
        request.session['user_school_id'] = None
        request.session['user_school_slug'] = None
        request.session['user_role'] = user_profile.user_type
        request.session['current_year_id'] = None
        request.session['current_term'] = None
        request.session['vacation_status'] = None
        request.session['is_on_vacation'] = None

    return True


def clear_user_session(request):
    """
    Clear all user session variables.
    """
    session_keys = [
        'user_id', 'user_type', 'user_school_id', 'user_school_slug',
        'user_role', 'user_position', 'current_year_id', 'current_term',
        'vacation_status', 'is_on_vacation', 'teacher_class_id', 'teacher_class_name'
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
        'vacation_status': request.session.get('vacation_status'),
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


def cleanup_old_pdf_files(school_slug, days_old=7):
    """
    Clean up old PDF files from the media directory for a specific school.

    Args:
        school_slug: The school slug to clean files for
        days_old: Number of days old files should be before deletion (default: 7)

    Returns:
        tuple: (files_deleted, errors)
    """
    import os
    import time
    from django.conf import settings

    files_deleted = 0
    errors = []

    try:
        school_media_path = os.path.join(settings.MEDIA_ROOT, school_slug)

        if not os.path.exists(school_media_path):
            return files_deleted, errors

        cutoff_time = time.time() - (days_old * 24 * 60 * 60)

        # Walk through all subdirectories
        for root, dirs, files in os.walk(school_media_path):
            for file in files:
                if file.endswith('.pdf') or file.endswith('.zip'):
                    file_path = os.path.join(root, file)
                    try:
                        # Check if file is older than cutoff
                        if os.path.getmtime(file_path) < cutoff_time:
                            os.remove(file_path)
                            files_deleted += 1
                    except OSError as e:
                        errors.append(f"Failed to delete {file_path}: {str(e)}")

        # Remove empty directories
        for root, dirs, files in os.walk(school_media_path, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):  # Directory is empty
                        os.rmdir(dir_path)
                except OSError:
                    pass  # Ignore errors when removing directories

    except Exception as e:
        errors.append(f"General cleanup error: {str(e)}")

    return files_deleted, errors
