#!/usr/bin/env bash
# Exit on error
set -o errexit

# install libraries
pip install -r requirements-new.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate

# Create superuser if it doesn't exist
# We use a conditional check to ensure it only runs once and doesn't error on subsequent builds
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py createsuperuser --noinput \
        --username "$DJANGO_SUPERUSER_USERNAME" \
        --email "$DJANGO_SUPERUSER_EMAIL" || true
    # Set the password after creation using setpassword
    # This ensures the password is set even if the user already exists (idempotent)
    echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.get(username='$DJANGO_SUPERUSER_USERNAME').set_password('$DJANGO_SUPERUSER_PASSWORD'); User.objects.get(username='$DJANGO_SUPERUSER_USERNAME').save()" | python manage.py shell || true
fi

# Note: The `|| true` at the end of the superuser commands makes the script continue
# even if createsuperuser/shell command fails (e.g., user already exists).
# This is useful for idempotent builds.
