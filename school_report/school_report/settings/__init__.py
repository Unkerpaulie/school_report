"""
Settings package initialization.
Import the appropriate settings based on the environment.
"""
import os

# Default to development settings
environment = os.environ.get('DJANGO_ENVIRONMENT', 'development')

if environment == 'production':
    from .production import *
elif environment == 'demo':
    from .demo import *
else:
    from .development import *
