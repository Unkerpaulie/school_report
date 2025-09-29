@echo off
REM Docker development management script for Windows

setlocal enabledelayedexpansion

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop.
    exit /b 1
)

if "%1"=="start" goto start
if "%1"=="up" goto start
if "%1"=="stop" goto stop
if "%1"=="down" goto stop
if "%1"=="restart" goto restart
if "%1"=="logs" goto logs
if "%1"=="shell" goto shell
if "%1"=="bash" goto bash
if "%1"=="migrate" goto migrate
if "%1"=="makemigrations" goto makemigrations
if "%1"=="collectstatic" goto collectstatic
if "%1"=="test" goto test
if "%1"=="demo" goto demo
if "%1"=="clean" goto clean
if "%1"=="status" goto status
goto help

:start
echo ================================
echo Starting School Report Development Environment
echo ================================

REM Copy environment file if it doesn't exist
if not exist .env (
    echo [INFO] Creating .env file from .env.dev template...
    copy .env.dev .env
)

echo [INFO] Building and starting containers...
docker-compose -f docker-compose.dev.yml up --build -d

echo [INFO] Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo [INFO] Running database migrations...
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate

echo [INFO] Creating superuser if needed...
docker-compose -f docker-compose.dev.yml exec web python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@school.local', 'admin123') if not User.objects.filter(username='admin').exists() else print('Superuser already exists')"

echo ================================
echo Development Environment Ready!
echo ================================
echo Django App: http://localhost:8000
echo pgAdmin: http://localhost:5050 (admin@school.local / admin123)
echo Database: localhost:5432 (school_admin / school_dev_password_2024)
echo Admin Panel: http://localhost:8000/admin (admin / admin123)
goto end

:stop
echo [INFO] Stopping Development Environment
docker-compose -f docker-compose.dev.yml down
echo [INFO] All containers stopped
goto end

:restart
echo [INFO] Restarting Development Environment
docker-compose -f docker-compose.dev.yml restart
echo [INFO] All containers restarted
goto end

:logs
if "%2"=="" (
    docker-compose -f docker-compose.dev.yml logs -f
) else (
    docker-compose -f docker-compose.dev.yml logs -f %2
)
goto end

:shell
echo [INFO] Opening Django shell in web container...
docker-compose -f docker-compose.dev.yml exec web python manage.py shell
goto end

:bash
echo [INFO] Opening bash shell in web container...
docker-compose -f docker-compose.dev.yml exec web bash
goto end

:migrate
echo [INFO] Running database migrations...
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate
goto end

:makemigrations
echo [INFO] Creating new migrations...
docker-compose -f docker-compose.dev.yml exec web python manage.py makemigrations
goto end

:collectstatic
echo [INFO] Collecting static files...
docker-compose -f docker-compose.dev.yml exec web python manage.py collectstatic --noinput
goto end

:test
echo [INFO] Running tests...
docker-compose -f docker-compose.dev.yml exec web python manage.py test
goto end

:demo
echo [INFO] Generating demo data...
docker-compose -f docker-compose.dev.yml exec web python manage.py generate_demo_data --schools=1 --students-per-class=15
goto end

:clean
echo ================================
echo Cleaning Up Development Environment
echo ================================
echo WARNING: This will remove all containers, volumes, and data!
set /p confirm="Are you sure? (y/N): "
if /i "!confirm!"=="y" (
    docker-compose -f docker-compose.dev.yml down -v --remove-orphans
    docker system prune -f
    echo [INFO] Cleanup completed
) else (
    echo [INFO] Cleanup cancelled
)
goto end

:status
echo ================================
echo Development Environment Status
echo ================================
docker-compose -f docker-compose.dev.yml ps
goto end

:help
echo ================================
echo School Report Docker Development Helper
echo ================================
echo Usage: %0 {command}
echo.
echo Commands:
echo   start/up          - Start the development environment
echo   stop/down         - Stop the development environment
echo   restart           - Restart all containers
echo   logs [service]    - Show logs (optionally for specific service)
echo   shell             - Open Django shell
echo   bash              - Open bash shell in web container
echo   migrate           - Run database migrations
echo   makemigrations    - Create new migrations
echo   collectstatic     - Collect static files
echo   test              - Run tests
echo   demo              - Generate demo data
echo   status            - Show container status
echo   clean             - Clean up everything (removes data!)
echo.
echo Examples:
echo   %0 start          - Start development environment
echo   %0 logs web       - Show web container logs
echo   %0 shell          - Open Django shell

:end
