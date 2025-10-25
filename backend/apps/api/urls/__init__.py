"""
NexusPM API - Main URLs

Central URL configuration for all API endpoints.
Implements versioned API routing and documentation.
"""

from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)

app_name = 'api'

# API v1 patterns
v1_patterns = [
    # User endpoints
    path('', include('apps.api.urls.user_urls')),
    
    # Organization endpoints (to be implemented)
    # path('', include('apps.api.urls.organization_urls')),
    
    # Workspace endpoints (to be implemented)
    # path('', include('apps.api.urls.workspace_urls')),
]

urlpatterns = [
    # API versioning
    path('v1/', include((v1_patterns, 'v1'))),
    
    # API Documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
]