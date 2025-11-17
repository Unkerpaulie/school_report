# 🚀 Seenode Quick Setup Guide

## Step 1: Seenode Project Configuration

**Build Command:**
```bash
bash seenode_build.sh
```

**Start Command:**
```bash
gunicorn --bind 0.0.0.0:$PORT school_report.wsgi:application
```

**Python Version:** `3.12`

## Step 2: Required Environment Variables

Copy your **DATABASE_URL** from Seenode dashboard and set these variables:

```bash
# Essential Configuration
DJANGO_SETTINGS_MODULE=school_report.settings.seenode
DJANGO_SECRET_KEY=your-super-secret-key-here
DEBUG=False
DATABASE_URL=postgresql://username:password@hostname:port/database_name
ALLOWED_HOSTS=your-seenode-domain.com
USE_HTTPS=True

# Optional: Auto-create admin user
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@school.local
DJANGO_SUPERUSER_PASSWORD=your-secure-password

# Optional: Generate demo data for testing
GENERATE_DEMO_DATA=false
```

## Step 3: Generate Secret Key

Run this locally to generate a secure secret key:

```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

## Step 4: Deploy

1. Push your code to GitHub/GitLab
2. Connect repository to Seenode
3. Set environment variables
4. Deploy!

## Step 5: Access Your App

- **Main Site**: `https://your-seenode-domain.com`
- **Admin Panel**: `https://your-seenode-domain.com/admin`

## 🎯 What the Build Script Does

✅ Installs dependencies from `requirements-new.txt`  
✅ Collects static files with WhiteNoise  
✅ Runs database migrations  
✅ Creates superuser (if credentials provided)  
✅ Generates demo data (if requested)  

## 🔧 Key Features

- **DATABASE_URL Support**: Automatic PostgreSQL connection parsing
- **WhiteNoise**: Static file serving without external storage
- **Security**: HTTPS, secure cookies, HSTS headers
- **Logging**: Structured logging for production monitoring
- **Flexible**: Optional S3 media storage, email configuration

## 📞 Need Help?

Check `SEENODE_DEPLOYMENT.md` for detailed troubleshooting and configuration options.
