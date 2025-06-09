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
