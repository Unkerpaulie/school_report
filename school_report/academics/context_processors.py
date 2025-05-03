"""
Context processors for the academics app.
"""
from .views import get_current_school_year_and_term

def current_school_year_and_term(request):
    """
    Context processor to add current school year and term to all templates.
    Uses the session-based function to avoid repeated database queries.
    """
    # Only process if user is authenticated
    if not request.user.is_authenticated:
        return {}

    # Use the helper function that handles session caching
    return get_current_school_year_and_term(request)
