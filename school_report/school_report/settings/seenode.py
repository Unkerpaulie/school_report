"""
Seenode deployment settings for school_report project.
"""

import os
import dj_database_url
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', os.environ.get('SECRET_KEY'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Seenode deployment hosts
ALLOWED_HOSTS = []

# Add Seenode hostname if available
if os.environ.get('SEENODE_HOSTNAME'):
    ALLOWED_HOSTS.append(os.environ.get('SEENODE_HOSTNAME'))

# Also allow hosts from environment variable (comma-separated)
if os.environ.get('ALLOWED_HOSTS'):
    ALLOWED_HOSTS.extend(os.environ.get('ALLOWED_HOSTS').split(','))

# Fallback for local testing
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Database configuration using DATABASE_URL
# Seenode provides DATABASE_URL environment variable
# Seenode uses PostgreSQL via DATABASE_URL or individual parameters
database_url = os.environ.get('DATABASE_URL')

if database_url:
    # Use DATABASE_URL if provided
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    # Fallback to individual parameters
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', ''),
            'USER': os.environ.get('DB_USER', ''),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', ''),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }
    
# DATABASES = {
#     'default': dj_database_url.config(
#         default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
#         conn_max_age=600,
#         conn_health_checks=True,
#     )
# }

# WhiteNoise configuration for static files (Seenode compatible)
MIDDLEWARE = ['whitenoise.middleware.WhiteNoiseMiddleware'] + MIDDLEWARE

# WhiteNoise settings
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Additional static files settings for WhiteNoise
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS settings (enable if using HTTPS on Seenode)
if os.environ.get('USE_HTTPS', 'True').lower() == 'true':
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Email configuration
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
if EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
    EMAIL_HOST = os.environ.get('EMAIL_HOST')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')

# Session settings
SESSION_COOKIE_AGE = int(os.environ.get('SESSION_COOKIE_AGE', 86400))  # 24 hours default
SESSION_EXPIRE_AT_BROWSER_CLOSE = os.environ.get('SESSION_EXPIRE_AT_BROWSER_CLOSE', 'True').lower() == 'true'

# Media files configuration
# For Seenode, you might want to use cloud storage for media files
if os.environ.get('USE_S3_MEDIA', 'False').lower() == 'true':
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN')
    AWS_DEFAULT_ACL = 'private'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_LOCATION = 'media'
else:
    # Use local media storage (default)
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

# CSRF Trusted Hosts
CSRF_TRUSTED_ORIGINS = [f'https://{host}' for host in ALLOWED_HOSTS]

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose' if DEBUG else 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'school_report': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
