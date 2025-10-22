from .base import *

# Development-specific settings
DEBUG = True

# Development email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable cache in development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

print("🔧 NexusPM Enterprise - Development Mode Active")