"""
NexusPM API Application Configuration

Main API application for the NexusPM Enterprise Platform.
Handles REST API endpoints, authentication, and serialization.
"""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.api'
    verbose_name = 'NexusPM API'