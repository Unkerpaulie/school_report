"""
Custom authentication backend for session setup
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .utils import setup_user_session

User = get_user_model()


class SessionSetupBackend(ModelBackend):
    """
    Custom authentication backend that sets up user session on login
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Use the default authentication
        user = super().authenticate(request, username, password, **kwargs)
        
        if user and request:
            # Set up comprehensive user session
            setup_user_session(request, user)
        
        return user
