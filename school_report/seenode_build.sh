#!/bin/bash
# Seenode deployment build script for Caribbean Primary School System

set -e

echo "Starting Seenode deployment build..."
echo "Environment Variables Check:"
python -c "
import os
print('ENVIRONMENT:', os.environ.get('ENVIRONMENT', 'NOT SET'))
print('ALLOWED_HOSTS:', os.environ.get('ALLOWED_HOSTS', 'NOT SET'))
print('DATABASE_URL:', 'SET' if os.environ.get('DATABASE_URL') else 'NOT SET')

# Install dependencies
echo "Installing Python dependencies..."
pip install --no-cache-dir -r requirements-new.txt

# Set Django settings module for Seenode
export DJANGO_SETTINGS_MODULE=school_report.settings.seenode

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist (only if credentials are provided)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
"
else
    echo "Skipping superuser creation (credentials not provided)"
fi

# Optional: Generate demo data if requested
if [ "$GENERATE_DEMO_DATA" = "true" ]; then
    echo "Generating demo data..."
    python manage.py generate_demo_data --schools=1 --students-per-class=15
    echo "Demo data generated"
fi

echo "Seenode build completed successfully!"
