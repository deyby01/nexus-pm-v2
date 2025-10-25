"""
NexusPM API - User Permissions

Enterprise-grade permissions for user-related API endpoints.
Implements role-based access control and user data protection.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    Permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` attribute.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in SAFE_METHODS:
            return True
        
        # Write permissions only to the owner
        return obj == request.user


class IsUserOrReadOnly(BasePermission):
    """
    Permission for user profile access.
    Users can view any profile but only modify their own.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in SAFE_METHODS:
            return True
        
        # Write permissions only to the user themselves
        return obj == request.user


class IsAdminOrOwner(BasePermission):
    """
    Permission for admin or owner access.
    Allows admin users or the object owner to perform actions.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin users can do anything
        if request.user.is_staff:
            return True
        
        # Object owner can modify
        return obj == request.user


class CanManageUsers(BasePermission):
    """
    Permission for user management operations.
    Only administrators can create, update, or delete users.
    """
    
    def has_permission(self, request, view):
        # Read permissions for authenticated users
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Write permissions only for admin users
        return request.user and request.user.is_staff