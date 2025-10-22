.PHONY: help build up down restart logs shell migrate test clean dev-setup

# Colors for output
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo '$(GREEN)NexusPM Enterprise - Development Commands$(NC)'
	@echo ''
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ==========================================
# DOCKER ENVIRONMENT MANAGEMENT
# ==========================================

build: ## Build all Docker containers
	@echo "$(YELLOW)🔨 Building Docker containers...$(NC)"
	docker-compose build --no-cache

up: ## Start all services in detached mode
	@echo "$(GREEN)🚀 Starting all services...$(NC)"
	docker-compose up -d

down: ## Stop all services
	@echo "$(RED)🛑 Stopping all services...$(NC)"
	docker-compose down

restart: ## Restart all services
	@echo "$(YELLOW)🔄 Restarting all services...$(NC)"
	docker-compose restart

stop: ## Stop all services without removing containers
	@echo "$(YELLOW)⏸️  Stopping all services...$(NC)"
	docker-compose stop

start: ## Start previously created containers
	@echo "$(GREEN)▶️  Starting existing containers...$(NC)"
	docker-compose start

# ==========================================
# DEVELOPMENT COMMANDS
# ==========================================

dev-setup: ## Complete development environment setup
	@echo "$(GREEN)🚀 Setting up NexusPM Enterprise development environment...$(NC)"
	@echo "$(BLUE)📁 Creating necessary directories...$(NC)"
	@mkdir -p backend/logs backend/media backend/staticfiles
	@echo "$(BLUE)📄 Copying environment variables...$(NC)"
	@if [ ! -f .env ]; then cp .env.example .env; echo "$(GREEN)✅ .env file created from .env.example$(NC)"; fi
	@echo "$(BLUE)🔨 Building Docker containers...$(NC)"
	@docker-compose build
	@echo "$(BLUE)🚀 Starting infrastructure services...$(NC)"
	@docker-compose up -d postgres redis minio mailhog
	@echo "$(BLUE)⏳ Waiting for services to be ready...$(NC)"
	@sleep 15
	@echo "$(BLUE)🌐 Starting web services...$(NC)"
	@docker-compose up -d
	@echo "$(GREEN)✅ Development environment ready!$(NC)"
	@echo ""
	@echo "$(GREEN)📊 Access Points:$(NC)"
	@echo "  $(BLUE)• Django API:$(NC)     http://localhost:8000"
	@echo "  $(BLUE)• Django Admin:$(NC)   http://localhost:8000/admin/"
	@echo "  $(BLUE)• API Docs:$(NC)       http://localhost:8000/api/docs/"
	@echo "  $(BLUE)• PgAdmin:$(NC)        http://localhost:5050"
	@echo "  $(BLUE)• MinIO Console:$(NC)  http://localhost:9001"
	@echo "  $(BLUE)• MailHog:$(NC)        http://localhost:8025"
	@echo "  $(BLUE)• Redis UI:$(NC)       http://localhost:8081"
	@echo "  $(BLUE)• Flower:$(NC)         http://localhost:5555"
	@echo ""
	@echo "$(GREEN)👤 Default Credentials:$(NC)"
	@echo "  $(BLUE)• Django Admin:$(NC)   admin@nexuspm.dev / admin123"
	@echo "  $(BLUE)• PgAdmin:$(NC)        admin@nexuspm.dev / admin123"
	@echo "  $(BLUE)• MinIO:$(NC)          nexus_minio / nexus_minio_2024"

# ==========================================
# LOGGING AND MONITORING
# ==========================================

logs: ## Show logs for all services
	@echo "$(BLUE)📋 Showing logs for all services...$(NC)"
	docker-compose logs -f

logs-web: ## Show Django web server logs
	@echo "$(BLUE)📋 Showing Django logs...$(NC)"
	docker-compose logs -f web

logs-db: ## Show PostgreSQL logs
	@echo "$(BLUE)📋 Showing PostgreSQL logs...$(NC)"
	docker-compose logs -f postgres

logs-redis: ## Show Redis logs
	@echo "$(BLUE)📋 Showing Redis logs...$(NC)"
	docker-compose logs -f redis

logs-celery: ## Show Celery worker logs
	@echo "$(BLUE)📋 Showing Celery logs...$(NC)"
	docker-compose logs -f celery_worker

# ==========================================
# DJANGO MANAGEMENT
# ==========================================

shell: ## Open Django shell inside container
	@echo "$(BLUE)🐍 Opening Django shell...$(NC)"
	docker-compose exec web python manage.py shell

bash: ## Open bash shell in web container
	@echo "$(BLUE)💻 Opening bash shell in web container...$(NC)"
	docker-compose exec web bash

bash-db: ## Open bash shell in postgres container
	@echo "$(BLUE)💻 Opening bash shell in postgres container...$(NC)"
	docker-compose exec postgres bash

migrate: ## Run Django migrations
	@echo "$(BLUE)🔄 Running Django migrations...$(NC)"
	docker-compose exec web python manage.py migrate

makemigrations: ## Create Django migrations
	@echo "$(BLUE)📝 Creating Django migrations...$(NC)"
	docker-compose exec web python manage.py makemigrations

collectstatic: ## Collect static files
	@echo "$(BLUE)📂 Collecting static files...$(NC)"
	docker-compose exec web python manage.py collectstatic --noinput

superuser: ## Create Django superuser
	@echo "$(BLUE)👤 Creating Django superuser...$(NC)"
	docker-compose exec web python manage.py createsuperuser

# ==========================================
# DATABASE MANAGEMENT
# ==========================================

psql: ## Connect to PostgreSQL database
	@echo "$(BLUE)🗄️  Connecting to PostgreSQL...$(NC)"
	docker-compose exec postgres psql -U nexus_admin -d nexuspm

redis-cli: ## Connect to Redis CLI
	@echo "$(BLUE)🔴 Connecting to Redis CLI...$(NC)"
	docker-compose exec redis redis-cli -a nexus_redis_2024

db-reset: ## Reset database (DANGER: deletes all data)
	@echo "$(RED)⚠️  DANGER: This will delete ALL database data!$(NC)"
	@echo -n "Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]
	docker-compose down
	docker volume rm nexus_postgres_data || true
	docker-compose up -d postgres
	@echo "$(GREEN)✅ Database reset completed$(NC)"

db-backup: ## Create database backup
	@echo "$(BLUE)💾 Creating database backup...$(NC)"
	docker-compose exec postgres pg_dump -U nexus_admin -d nexuspm > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Database backup created$(NC)"

# ==========================================
# TESTING
# ==========================================

test: ## Run all tests
	@echo "$(BLUE)🧪 Running tests...$(NC)"
	docker-compose exec web python manage.py test

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)📊 Running tests with coverage...$(NC)"
	docker-compose exec web coverage run --source='.' manage.py test
	docker-compose exec web coverage report
	docker-compose exec web coverage html

lint: ## Run code quality checks
	@echo "$(BLUE)🔍 Running linting checks...$(NC)"
	docker-compose exec web flake8 .
	docker-compose exec web black --check .
	docker-compose exec web isort --check-only .

format: ## Format code automatically
	@echo "$(BLUE)✨ Formatting code...$(NC)"
	docker-compose exec web black .
	docker-compose exec web isort .

# ==========================================
# UTILITY COMMANDS
# ==========================================

status: ## Show status of all containers
	@echo "$(BLUE)📊 Container status:$(NC)"
	docker-compose ps

top: ## Show running processes in containers
	@echo "$(BLUE)📈 Running processes:$(NC)"
	docker-compose top

stats: ## Show container resource usage statistics
	@echo "$(BLUE)📊 Container resource usage:$(NC)"
	docker stats $(shell docker-compose ps -q)

clean: ## Clean up containers and volumes
	@echo "$(RED)🧹 Cleaning up containers and volumes...$(NC)"
	docker-compose down -v
	docker system prune -f

clean-all: ## Clean everything (DANGER: removes all unused Docker resources)
	@echo "$(RED)⚠️  DANGER: This will remove all unused Docker resources!$(NC)"
	@echo -n "Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]
	docker-compose down -v
	docker system prune -a -f
	docker volume prune -f
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

# ==========================================
# MONITORING SHORTCUTS
# ==========================================

open-admin: ## Open Django admin in browser
	@echo "$(BLUE)🌐 Opening Django admin...$(NC)"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:8000/admin/ || echo "Visit: http://localhost:8000/admin/"

open-api: ## Open API documentation in browser  
	@echo "$(BLUE)📚 Opening API documentation...$(NC)"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:8000/api/docs/ || echo "Visit: http://localhost:8000/api/docs/"

open-pgadmin: ## Open PgAdmin in browser
	@echo "$(BLUE)🗄️  Opening PgAdmin...$(NC)"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:5050 || echo "Visit: http://localhost:5050"

open-minio: ## Open MinIO console in browser
	@echo "$(BLUE)📦 Opening MinIO console...$(NC)"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:9001 || echo "Visit: http://localhost:9001"

urls: ## Show all service URLs
	@echo "$(GREEN)🌐 NexusPM Enterprise - Service URLs:$(NC)"
	@echo "  $(BLUE)• Django API:$(NC)     http://localhost:8000"
	@echo "  $(BLUE)• Django Admin:$(NC)   http://localhost:8000/admin/"
	@echo "  $(BLUE)• API Documentation:$(NC) http://localhost:8000/api/docs/"
	@echo "  $(BLUE)• PgAdmin:$(NC)        http://localhost:5050"
	@echo "  $(BLUE)• MinIO Console:$(NC)  http://localhost:9001"
	@echo "  $(BLUE)• MailHog:$(NC)        http://localhost:8025"
	@echo "  $(BLUE)• Redis Commander:$(NC) http://localhost:8081"
	@echo "  $(BLUE)• Flower (Celery):$(NC) http://localhost:5555"