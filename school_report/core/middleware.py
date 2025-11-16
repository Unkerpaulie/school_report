import time
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import logout
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

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
                    # Define allowed URLs when password change is required
                    allowed_urls = [
                        reverse('core:password_change'),
                        reverse('core:password_change_done'),
                        reverse('core:custom_logout'),
                    ]

                    # Allow access to password change related pages and logout
                    if request.path not in allowed_urls:
                        messages.warning(request, "You must change your password before continuing.")
                        return redirect('core:password_change')
            except AttributeError:
                # If profile doesn't exist, just continue
                pass
            except Exception:
                # Handle any other exceptions gracefully
                pass

        response = self.get_response(request)
        return response


class IdleTimeoutMiddleware(MiddlewareMixin):
    """
    Middleware to handle idle timeout for authenticated users.

    This provides server-side session timeout that works even when
    tabs are closed, complementing the client-side JavaScript timeout.
    """

    def process_request(self, request):
        """
        Check if user session has exceeded idle timeout
        """
        # Skip timeout check for unauthenticated users
        if not request.user.is_authenticated:
            return None

        # Skip timeout check for login/logout pages to avoid redirect loops
        if request.path in [reverse('login'), reverse('core:custom_logout')]:
            return None

        # Skip timeout check for AJAX requests and static files
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return None
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None

        # Get current time
        current_time = time.time()

        # Get last activity time from session
        last_activity = request.session.get('last_activity')

        if last_activity:
            # Calculate idle time
            idle_time = current_time - last_activity

            # Check if idle timeout exceeded
            if idle_time > settings.IDLE_TIMEOUT_SECONDS:
                # Log out the user
                logout(request)

                # Add a message to inform user about timeout
                messages.warning(
                    request,
                    f'Your session expired after {settings.IDLE_TIMEOUT_MINUTES} minutes of inactivity. '
                    'Please log in again.'
                )

                # Redirect to login page
                return redirect('login')

        # Update last activity time
        request.session['last_activity'] = current_time

        return None
