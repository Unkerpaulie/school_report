from django.utils import timezone
from django.db.models import Q
from academics.models import SchoolYear, Term

def get_current_year_and_term():
    """
    Get the current academic year and term based on the current date.
    
    Returns:
        tuple: (current_year, current_term, is_on_vacation)
            - current_year: SchoolYear object or None
            - current_term: int (1, 2, or 3) or None
            - is_on_vacation: bool
    """
    today = timezone.now().date()
    
    # Get all terms that include today's date
    current_terms = Term.objects.filter(
        start_date__lte=today,
        end_date__gte=today
    ).select_related('year')
    
    if current_terms.exists():
        term = current_terms.first()
        return term.year, term.term_number, False
    
    # If no terms found, we're on vacation
    return None, None, True
