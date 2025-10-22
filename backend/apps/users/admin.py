"""
NexusPM Enterprise - User Admin Configuration

This module configures the Django admin interface for user management.
Following enterprise best practices, it provides comprehensive user
management capabilities while maintaining security and usability.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.utils import timezone

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Enhanced User admin with enterprise-grade features.
    
    Features:
    - Custom list display with key user information
    - Advanced filtering and search capabilities
    - Security-focused fieldsets
    - Bulk actions for user management
    - Avatar preview in admin
    """
    
    # List view configuration
    list_display = [
        'avatar_preview',
        'email',
        'first_name', 
        'last_name',
        'job_title',
        'is_active',
        'is_email_verified',
        'last_login',
        'created_at',
    ]
    
    list_filter = [
        'is_active',
        'is_staff',
        'is_superuser',
        'is_email_verified',
        'language',
        'created_at',
        'last_login',
    ]
    
    search_fields = [
        'email',
        'first_name',
        'last_name',
        'job_title',
    ]
    
    ordering = ['-created_at']
    
    list_per_page = 25
    
    # Detail view configuration
    fieldsets = (
        ('🔐 Authentication', {
            'fields': ('email', 'password')
        }),
        ('👤 Personal Information', {
            'fields': ('first_name', 'last_name', 'avatar', 'job_title', 'phone_number')
        }),
        ('🌐 Preferences', {
            'fields': ('language', 'timezone', 'date_format'),
            'classes': ['collapse']
        }),
        ('🔒 Security & Status', {
            'fields': (
                'is_active',
                'is_email_verified', 
                'email_verified_at',
                'last_login_ip',
                'failed_login_attempts',
                'locked_until'
            ),
            'classes': ['collapse']
        }),
        ('👨‍💼 Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ['collapse']
        }),
        ('📅 Important Dates', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at', 'deleted_at'),
            'classes': ['collapse']
        }),
    )
    
    add_fieldsets = (
        ('🔐 Required Information', {
            'classes': ['wide'],
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
        ('👤 Optional Information', {
            'classes': ['wide', 'collapse'],
            'fields': ('job_title', 'phone_number', 'language', 'timezone'),
        }),
    )
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at', 
        'date_joined',
        'last_login',
        'username',  # Auto-generated, shouldn't be edited
    ]
    
    # Custom methods for list display
    def avatar_preview(self, obj):
        """Display user avatar in admin list"""
        if obj.avatar:
            return format_html(
                '<img src="{}" width="30" height="30" style="border-radius: 50%;" />',
                obj.avatar.url
            )
        else:
            # Show initials as fallback
            return format_html(
                '<div style="width:30px;height:30px;background:#007cba;color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:12px;">{}</div>',
                obj.initials
            )
    avatar_preview.short_description = '📸'
    
    # Bulk actions
    actions = ['verify_email', 'unverify_email', 'activate_users', 'deactivate_users']
    
    def verify_email(self, request, queryset):
        """Mark selected users as email verified"""
        count = queryset.update(
            is_email_verified=True,
            email_verified_at=timezone.now()
        )
        self.message_user(request, f"✅ {count} users marked as email verified.")
    verify_email.short_description = "✅ Mark email as verified"
    
    def unverify_email(self, request, queryset):
        """Mark selected users as email not verified"""
        count = queryset.update(
            is_email_verified=False,
            email_verified_at=None
        )
        self.message_user(request, f"❌ {count} users marked as email not verified.")
    unverify_email.short_description = "❌ Mark email as not verified"
    
    def activate_users(self, request, queryset):
        """Activate selected users"""
        count = queryset.update(is_active=True)
        self.message_user(request, f"✅ {count} users activated.")
    activate_users.short_description = "✅ Activate selected users"
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"❌ {count} users deactivated.")
    deactivate_users.short_description = "❌ Deactivate selected users"