#!/usr/bin/env bash
# Exit on error
set -o errexit

# install libraries
pip install -r requirements-new.txt

# install whitenoise for the css to work on render.com
pip install whitenoise

# Note: WeasyPrint system dependencies (libpango, etc.) are pre-installed on Render.com
# If PDF generation fails, it will gracefully degrade with user-friendly error messages

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

# Flush database if requested (DANGER: This wipes all data!)
if [ "$FLUSH_DATABASE" = "true" ]; then
    echo "🗑️  WARNING: Flushing database - all data will be lost!"
    python manage.py flush --noinput || true
    echo "✅ Database flushed"

    # Recreate superuser after flush
    if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
        echo "👤 Recreating superuser after database flush..."
        python manage.py createsuperuser --noinput \
            --username "$DJANGO_SUPERUSER_USERNAME" \
            --email "$DJANGO_SUPERUSER_EMAIL" || true
        echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.get(username='$DJANGO_SUPERUSER_USERNAME').set_password('$DJANGO_SUPERUSER_PASSWORD'); User.objects.get(username='$DJANGO_SUPERUSER_USERNAME').save()" | python manage.py shell || true
        echo "✅ Superuser recreated"
    fi
fi

# Generate demo data if requested
if [ "$GENERATE_DEMO_DATA" = "true" ]; then
    echo "🎲 Generating demo data..."

    # Create the output directory in static files
    mkdir -p core/static/tmp

    # Generate demo data with JSON output to static directory
    python manage.py generate_demo_data --schools=1 --students-per-class=15 --output-dir=core/static/tmp || true

    # Make sure the JSON files are collected as static files
    python manage.py collectstatic --no-input

    echo "✅ Demo data generation completed"
    echo "📁 JSON files accessible at: /static/tmp/"
fi

# Note: The `|| true` at the end of the superuser commands makes the script continue
# even if createsuperuser/shell command fails (e.g., user already exists).
# This is useful for idempotent builds.
