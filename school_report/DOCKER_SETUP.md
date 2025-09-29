# Docker Development Setup

## 🐳 Overview

This setup provides a complete Docker-based development environment for the Caribbean Primary School System, including:

- **Django Web Application** with WeasyPrint support
- **PostgreSQL Database** for data persistence
- **Redis** for caching and sessions
- **pgAdmin** for database management
- **Persistent Volumes** for data, media, and report archives

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed and running
- WSL2 enabled (Windows)
- Git for version control

### 1. Start Development Environment

**Windows:**
```cmd
docker-dev.bat start
```

**Linux/Mac:**
```bash
chmod +x docker-dev.sh
./docker-dev.sh start
```

### 2. Access Your Application

- **Django App**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin (admin / admin123)
- **pgAdmin**: http://localhost:5050 (admin@school.local / admin123)
- **Database**: localhost:5432 (school_admin / school_dev_password_2024)

## 📁 Directory Structure

```
school_report/
├── docker-compose.dev.yml      # Development Docker Compose
├── Dockerfile.dev              # Development Dockerfile
├── docker-dev.sh              # Linux/Mac management script
├── docker-dev.bat             # Windows management script
├── .env.dev                   # Environment template
├── docker/
│   └── postgres/
│       └── init.sql           # PostgreSQL initialization
└── volumes/ (created by Docker)
    ├── postgres_dev_data/     # Database data
    ├── media_dev_data/        # School logos, uploads
    ├── report_archives/       # PDF report archives
    ├── static_dev_data/       # Static files
    └── redis_dev_data/        # Redis data
```

## 🛠️ Management Commands

### Basic Operations
```bash
# Start environment
./docker-dev.sh start

# Stop environment
./docker-dev.sh stop

# Restart all containers
./docker-dev.sh restart

# View container status
./docker-dev.sh status
```

### Development Tasks
```bash
# Open Django shell
./docker-dev.sh shell

# Open bash in web container
./docker-dev.sh bash

# Run migrations
./docker-dev.sh migrate

# Create new migrations
./docker-dev.sh makemigrations

# Collect static files
./docker-dev.sh collectstatic

# Run tests
./docker-dev.sh test

# Generate demo data
./docker-dev.sh demo
```

### Debugging
```bash
# View all logs
./docker-dev.sh logs

# View specific service logs
./docker-dev.sh logs web
./docker-dev.sh logs db
./docker-dev.sh logs redis
```

### Cleanup
```bash
# Remove everything (including data!)
./docker-dev.sh clean
```

## 🔧 Configuration

### Environment Variables
The `.env` file is created from `.env.dev` template. Key variables:

```env
# Django
DJANGO_ENVIRONMENT=development
DEBUG=True
DJANGO_SECRET_KEY=dev-secret-key-change-in-production-2024

# Database
DB_NAME=school_report_dev
DB_USER=school_admin
DB_PASSWORD=school_dev_password_2024
DB_HOST=db
DB_PORT=5432

# Superuser
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@school.local
DJANGO_SUPERUSER_PASSWORD=admin123
```

### Volume Mounts
- **Source Code**: Live-mounted for hot reloading
- **Database**: Persistent PostgreSQL data
- **Media**: School logos and uploads
- **Report Archives**: PDF report batches (separate from media)
- **Static Files**: CSS, JS, images

## 📊 Services

### Web (Django)
- **Port**: 8000
- **Features**: Hot reloading, WeasyPrint, Debug Toolbar
- **Volumes**: Source code, media, static files, report archives

### Database (PostgreSQL)
- **Port**: 5432
- **Version**: PostgreSQL 15
- **Features**: Persistent data, health checks
- **Credentials**: school_admin / school_dev_password_2024

### Redis
- **Port**: 6379
- **Purpose**: Caching, sessions (optional)
- **Features**: Persistent data

### pgAdmin
- **Port**: 5050
- **Purpose**: Database management GUI
- **Credentials**: admin@school.local / admin123

## 🎯 Development Workflow

### 1. Daily Development
```bash
# Start your day
./docker-dev.sh start

# Make code changes (files are live-mounted)
# Changes are reflected immediately

# Run migrations when models change
./docker-dev.sh makemigrations
./docker-dev.sh migrate

# Stop when done
./docker-dev.sh stop
```

### 2. Testing PDF Generation
```bash
# Start environment
./docker-dev.sh start

# Generate demo data
./docker-dev.sh demo

# Navigate to http://localhost:8000
# Login with admin/admin123
# Go to Reports > Class Reports
# Click "Print All Reports" button
# PDFs will be generated using WeasyPrint!
```

### 3. Database Management
```bash
# Access pgAdmin at http://localhost:5050
# Add server with:
# Host: db
# Port: 5432
# Username: school_admin
# Password: school_dev_password_2024
```

## 🔍 Troubleshooting

### Container Won't Start
```bash
# Check Docker is running
docker info

# Check container status
./docker-dev.sh status

# View logs
./docker-dev.sh logs
```

### Database Issues
```bash
# Reset database
./docker-dev.sh clean
./docker-dev.sh start

# Or just restart database
docker-compose -f docker-compose.dev.yml restart db
```

### Permission Issues (Linux/Mac)
```bash
# Fix script permissions
chmod +x docker-dev.sh

# Fix volume permissions
sudo chown -R $USER:$USER volumes/
```

### WeasyPrint Issues
WeasyPrint should work out of the box in the Linux container. If you see errors:

```bash
# Check if WeasyPrint is installed
./docker-dev.sh bash
python -c "import weasyprint; print('WeasyPrint works!')"
```

## 🚀 Production Deployment

This development setup can be adapted for production:

1. Use `docker-compose.yml` (with nginx)
2. Set `DJANGO_ENVIRONMENT=production`
3. Use proper secrets management
4. Configure SSL certificates
5. Use managed database services

## 📝 Notes

- **Data Persistence**: All data is stored in Docker volumes
- **Hot Reloading**: Code changes are reflected immediately
- **PDF Generation**: WeasyPrint works perfectly in Linux containers
- **Database**: PostgreSQL provides production-like environment
- **Security**: Development credentials are safe for local use only
