"""
NexusPM API - User URLs

URL patterns for user-related API endpoints.
Implements RESTful routing for user management operations.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from ..views.user_views import (
    UserListCreateView,
    UserDetailView,
    CurrentUserView,
    PasswordChangeView,
    UserRegisterView,
    CustomTokenObtainPairView,
    logout_view,
)

app_name = 'users'

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', UserRegisterView.as_view(), name='user-register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='user-login'),
    path('auth/logout/', logout_view, name='user-logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # User management endpoints
    path('users/', UserListCreateView.as_view(), name='user-list-create'),
    path('users/<uuid:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('users/me/', CurrentUserView.as_view(), name='current-user'),
    path('users/me/change-password/', PasswordChangeView.as_view(), name='password-change'),
]