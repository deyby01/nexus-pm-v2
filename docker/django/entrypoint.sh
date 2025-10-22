#!/bin/bash
set -e

echo "🚀 NexusPM Enterprise - Starting application..."

# Function to wait for a service to be ready
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    
    echo "⏳ Waiting for $service to be ready..."
    while ! nc -z $host $port; do
        echo "   $service is not ready yet, waiting..."
        sleep 2
    done
    echo "✅ $service is ready!"
}

# Wait for PostgreSQL
wait_for_service postgres 5432 "PostgreSQL"

# Wait for Redis  
wait_for_service redis 6379 "Redis"

# Wait for MinIO
wait_for_service minio 9000 "MinIO"

echo "🔄 All services are ready! Proceeding with application startup..."

# Run Django-specific commands only for web service
if [ "$1" = "python" ] && [ "$2" = "manage.py" ] && [ "$3" = "runserver" ]; then
    echo "📦 Running Django setup commands..."
    
    echo "🔄 Collecting static files..."
    python manage.py collectstatic --noinput --clear
    
    echo "🔄 Running database migrations..."
    python manage.py migrate --noinput
    
    echo "👤 Creating superuser if it doesn't exist..."
    python manage.py shell << EOF
from django.contrib.auth import get_user_model
import os

User = get_user_model()
email = 'admin@nexuspm.dev'
password = 'admin123'

if not User.objects.filter(email=email).exists():
    user = User.objects.create_superuser(
        email=email,
        password=password,
        first_name='Admin',
        last_name='User'
    )
    print(f'✅ Superuser created: {email}')
else:
    print(f'ℹ️  Superuser already exists: {email}')
EOF

    echo "📊 Loading initial data..."
    # python manage.py loaddata initial_data.json  # Uncomment when we create fixtures
    
    echo "🎉 Django setup completed successfully!"
    echo ""
    echo "🌐 Access Points:"
    echo "   • Django API:    http://localhost:8000"
    echo "   • Django Admin:  http://localhost:8000/admin/"
    echo "   • API Docs:      http://localhost:8000/api/docs/"
    echo "   • PgAdmin:       http://localhost:5050"
    echo "   • MinIO Console: http://localhost:9001"
    echo "   • MailHog:       http://localhost:8025"
    echo "   • Redis UI:      http://localhost:8081"
    echo "   • Flower:        http://localhost:5555"
    echo ""
    echo "👤 Default Admin Credentials:"
    echo "   • Email:    admin@nexuspm.dev"
    echo "   • Password: admin123"
    echo ""
fi

# Execute the main command
exec "$@"