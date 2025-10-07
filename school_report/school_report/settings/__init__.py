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
elif environment == 'docker_dev' or (environment == 'development' and os.environ.get('DATABASE_URL')):
    # Use Docker development settings if explicitly set or if DATABASE_URL is present
    from .docker_dev import *
else:
    from .development import *
