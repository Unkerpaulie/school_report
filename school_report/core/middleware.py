from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class PasswordChangeMiddleware:
    """
    Middleware to force users to change their password if required
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if user needs to change password
            try:
                if request.user.profile.must_change_password:
                    # Allow access to password change page and logout
                    if not request.path == reverse('password_change') and not request.path == reverse('logout'):
                        messages.warning(request, "You must change your password before continuing.")
                        return redirect('password_change')
            except:
                # If profile doesn't exist, just continue
                pass
                
        response = self.get_response(request)
        return response
