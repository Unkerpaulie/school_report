# Seenode Deployment Guide

## 🚀 Overview

This guide covers deploying the Caribbean Primary School System to Seenode, a cloud platform for Django applications.

## 📋 Prerequisites

- Seenode account created
- Project repository pushed to GitHub/GitLab
- Database connection string from Seenode

## 🔧 Deployment Steps

### 1. Project Setup on Seenode

1. **Create New Project** on Seenode dashboard
2. **Connect Repository** (GitHub/GitLab)
3. **Configure Build Settings**:
   - **Build Command**: `bash seenode_build.sh`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT school_report.wsgi:application`
   - **Python Version**: 3.12

### 2. Environment Variables

Copy the database connection string from Seenode and set these environment variables in your project settings:

#### Required Variables:
```bash
DJANGO_SETTINGS_MODULE=school_report.settings.seenode
DJANGO_SECRET_KEY=your-super-secret-key-here
DEBUG=False
DATABASE_URL=postgresql://username:password@hostname:port/database_name
ALLOWED_HOSTS=your-seenode-domain.com
SEENODE_HOSTNAME=your-seenode-domain.com
USE_HTTPS=True
```

#### Optional Variables:
```bash
# Superuser Creation
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@school.local
DJANGO_SUPERUSER_PASSWORD=your-secure-password

# Demo Data (for testing)
GENERATE_DEMO_DATA=false

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=your-email@gmail.com

# Cloud Storage (if needed)
USE_S3_MEDIA=false
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
```

### 3. Build Configuration

The `seenode_build.sh` script automatically:
- ✅ Installs Python dependencies
- ✅ Collects static files
- ✅ Runs database migrations
- ✅ Creates superuser (if credentials provided)
- ✅ Generates demo data (if requested)

### 4. Database Setup

Seenode provides a PostgreSQL database with a connection string like:
```
postgresql://username:password@hostname:port/database_name
```

The `DATABASE_URL` environment variable is automatically parsed by `dj-database-url`.

## 🎯 Post-Deployment

### 1. Access Your Application
- **Main Site**: `https://your-seenode-domain.com`
- **Admin Panel**: `https://your-seenode-domain.com/admin`

### 2. Create School and Users
1. Login to admin panel with superuser credentials
2. Create your first school
3. Add teachers and students
4. Set up academic years and terms

### 3. Generate Demo Data (Optional)
Set `GENERATE_DEMO_DATA=true` in environment variables to auto-generate:
- Sample school with multiple classes
- Teachers assigned to classes
- Students enrolled in classes
- Sample test data and reports

## 🔒 Security Considerations

### Production Security:
- ✅ **HTTPS Enabled**: `USE_HTTPS=True`
- ✅ **Debug Disabled**: `DEBUG=False`
- ✅ **Secure Cookies**: Automatically configured
- ✅ **HSTS Headers**: Enabled for HTTPS
- ✅ **XSS Protection**: Enabled
- ✅ **Content Type Sniffing**: Disabled

### Secret Key:
Generate a secure secret key:
```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

## 🛠️ Troubleshooting

### Common Issues:

**1. Database Connection Error**
- Verify `DATABASE_URL` is correct
- Check database credentials in Seenode dashboard

**2. Static Files Not Loading**
- Ensure `ALLOWED_HOSTS` includes your domain
- Check WhiteNoise configuration

**3. Migration Errors**
- Check database permissions
- Verify PostgreSQL version compatibility

**4. Superuser Creation Failed**
- Verify all three variables are set:
  - `DJANGO_SUPERUSER_USERNAME`
  - `DJANGO_SUPERUSER_EMAIL`
  - `DJANGO_SUPERUSER_PASSWORD`

### Logs and Debugging:
- Check Seenode deployment logs
- Set `DJANGO_LOG_LEVEL=DEBUG` for detailed logging
- Use `DEBUG=True` temporarily for development

## 📚 Additional Resources

- [Seenode Documentation](https://seenode.com/docs)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [dj-database-url Documentation](https://github.com/jazzband/dj-database-url)
