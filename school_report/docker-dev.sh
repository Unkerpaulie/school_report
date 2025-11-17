#!/bin/bash
# Docker development management script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
}

# Main commands
case "$1" in
    "start"|"up")
        print_header "Starting School Report Development Environment"
        check_docker
        
        # Copy environment file if it doesn't exist
        if [ ! -f .env ]; then
            print_status "Creating .env file from .env.dev template..."
            cp .env.dev .env
        fi
        
        print_status "Building and starting containers..."
        docker-compose -f docker-compose.dev.yml up --build -d
        
        print_status "Waiting for services to be ready..."
        sleep 10
        
        print_status "Running database migrations..."
        docker-compose -f docker-compose.dev.yml exec web python manage.py migrate
        
        print_status "Creating superuser (if needed)..."
        docker-compose -f docker-compose.dev.yml exec web python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@school.local', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"
        
        print_header "Development Environment Ready!"
        echo -e "${GREEN}🌐 Django App:${NC} http://localhost:8020"
        echo -e "${GREEN}🗄️  pgAdmin:${NC} http://localhost:5050 (admin@school.local / admin123)"
        echo -e "${GREEN}📊 Database:${NC} localhost:5432 (school_admin / school_dev_password_2024)"
        echo -e "${GREEN}🔧 Admin Panel:${NC} http://localhost:8020/admin (admin / admin123)"
        ;;
        
    "stop"|"down")
        print_header "Stopping Development Environment"
        docker-compose -f docker-compose.dev.yml down
        print_status "All containers stopped"
        ;;
        
    "restart")
        print_header "Restarting Development Environment"
        docker-compose -f docker-compose.dev.yml restart
        print_status "All containers restarted"
        ;;
        
    "logs")
        if [ -n "$2" ]; then
            docker-compose -f docker-compose.dev.yml logs -f "$2"
        else
            docker-compose -f docker-compose.dev.yml logs -f
        fi
        ;;
        
    "shell")
        print_status "Opening Django shell in web container..."
        docker-compose -f docker-compose.dev.yml exec web python manage.py shell
        ;;
        
    "bash")
        print_status "Opening bash shell in web container..."
        docker-compose -f docker-compose.dev.yml exec web bash
        ;;
        
    "migrate")
        print_status "Running database migrations..."
        docker-compose -f docker-compose.dev.yml exec web python manage.py migrate
        ;;
        
    "makemigrations")
        print_status "Creating new migrations..."
        docker-compose -f docker-compose.dev.yml exec web python manage.py makemigrations
        ;;
        
    "collectstatic")
        print_status "Collecting static files..."
        docker-compose -f docker-compose.dev.yml exec web python manage.py collectstatic --noinput
        ;;
        
    "test")
        print_status "Running tests..."
        docker-compose -f docker-compose.dev.yml exec web python manage.py test
        ;;
        
    "demo")
        print_status "Generating demo data..."
        docker-compose -f docker-compose.dev.yml exec web python manage.py generate_demo_data --schools=1 --students-per-class=15
        ;;
        
    "clean")
        print_header "Cleaning Up Development Environment"
        print_warning "This will remove all containers, volumes, and data!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose -f docker-compose.dev.yml down -v --remove-orphans
            docker system prune -f
            print_status "Cleanup completed"
        else
            print_status "Cleanup cancelled"
        fi
        ;;
        
    "status")
        print_header "Development Environment Status"
        docker-compose -f docker-compose.dev.yml ps
        ;;
        
    *)
        print_header "School Report Docker Development Helper"
        echo "Usage: $0 {command}"
        echo ""
        echo "Commands:"
        echo "  start/up          - Start the development environment"
        echo "  stop/down         - Stop the development environment"
        echo "  restart           - Restart all containers"
        echo "  logs [service]    - Show logs (optionally for specific service)"
        echo "  shell             - Open Django shell"
        echo "  bash              - Open bash shell in web container"
        echo "  migrate           - Run database migrations"
        echo "  makemigrations    - Create new migrations"
        echo "  collectstatic     - Collect static files"
        echo "  test              - Run tests"
        echo "  demo              - Generate demo data"
        echo "  status            - Show container status"
        echo "  clean             - Clean up everything (removes data!)"
        echo ""
        echo "Examples:"
        echo "  $0 start          - Start development environment"
        echo "  $0 logs web       - Show web container logs"
        echo "  $0 shell          - Open Django shell"
        ;;
esac
