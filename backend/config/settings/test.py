"""
Test settings for NexusPM Enterprise.

Optimized for fast, reliable testing with proper isolation.
"""
from .base import *
import tempfile
import os

# SECURITY WARNING: Use a test-specific secret key
SECRET_KEY = 'test-secret-key-for-nexuspm-enterprise-do-not-use-in-production'

# Database configuration for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # In-memory database for speed
        'OPTIONS': {
            'timeout': 20,
        },
        'TEST': {
            'NAME': ':memory:',
        }
    }
}

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Password hashers - use fastest for testing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',  # Fastest for testing
]

# Email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Cache configuration for testing
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Media files for testing
MEDIA_ROOT = tempfile.mkdtemp()

# Static files for testing
STATIC_ROOT = tempfile.mkdtemp()

# Logging configuration for tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'nexuspm': {
            'handlers': ['console'], 
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Disable debug toolbar for tests
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: False,
}

# Time zone for consistent testing
USE_TZ = True
TIME_ZONE = 'UTC'

# Internationalization for testing
USE_I18N = False
USE_L10N = False

# Security settings relaxed for testing
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Celery configuration for testing (if using Celery)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# REST Framework settings for testing
REST_FRAMEWORK.update({
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
})

# Test-specific settings
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Disable unnecessary apps for faster testing
INSTALLED_APPS = [app for app in INSTALLED_APPS if 'debug_toolbar' not in app]

# Factory Boy settings
FACTORY_FOR_DJANGO_USERNAME_FIELD = 'email'

# Coverage settings
COVERAGE_MODULE_EXCLUDES = [
    'tests$', 'settings$', 'urls$', 'locale$',
    'migrations', 'fixtures', 'venv', 'virtualenv',
]

# Pytest-django settings
PYTEST_DJANGO_LIVE_SERVER_ADDRESS = 'localhost:8081-8100'

print("🧪 NexusPM Test Environment Active - Optimized for Speed & Reliability")