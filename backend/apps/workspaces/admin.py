"""
NexusPM Enterprise - Workspaces Admin Configuration (FIXED)

This module configures advanced admin interfaces for workspace management.
Essential for operations teams managing enterprise clients with complex
team structures and access control requirements.

Note: Project-related fields are commented out until Projects model is implemented.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from django.utils import timezone
import logging

from .models import Workspace, WorkspaceMembership

logger = logging.getLogger('nexuspm.workspaces')


class WorkspaceMembershipInline(admin.TabularInline):
    """
    Inline editor for workspace members.
    Allows managing team members directly from workspace admin.
    """
    model = WorkspaceMembership
    extra = 0
    fields = [
        'user', 
        'role', 
        'is_active', 
        'invited_by', 
        'joined_at', 
        'last_active_at'
    ]
    readonly_fields = ['joined_at', 'last_active_at']
    
    def get_queryset(self, request):
        """Optimize queries to avoid N+1 problems"""
        return super().get_queryset(request).select_related(
            'user', 'invited_by'
        )


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    """
    Main admin interface for workspace management.
    
    Critical for enterprise operations:
    - Monitor workspace health and usage
    - Handle team access and permission issues
    - Manage workspace limits and compliance
    - Track team activity and engagement
    """
    
    list_display = [
        'workspace_icon',
        'name',
        'organization_link',
        'workspace_type',
        'status',
        'member_count_display',
        # 'project_count_display',  # TODO: Uncomment when Project model is created
        'is_private',
        'created_by_email',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'workspace_type',
        'is_private',
        'created_at',
        'organization__status',
    ]
    
    search_fields = [
        'name',
        'slug',
        'description',
        'organization__name',
        'created_by__email',
    ]
    
    readonly_fields = [
        'id',
        'slug',
        'member_count_display',
        # 'project_count_display',  # TODO: Uncomment when Project model is created
        'created_at',
        'updated_at',
        'organization_limits_status',
    ]
    
    fieldsets = (
        ('🏠 Workspace Information', {
            'fields': ('name', 'slug', 'description', 'organization', 'workspace_type')
        }),
        ('🎨 Appearance', {
            'fields': ('color', 'icon'),
            'classes': ['collapse'],
        }),
        ('🔐 Access Control', {
            'fields': ('status', 'is_private', 'created_by'),
        }),
        ('📊 Usage Statistics', {
            'fields': ('member_count_display', 'organization_limits_status'),
            # 'fields': ('member_count_display', 'project_count_display', 'organization_limits_status'),  # TODO: Uncomment when Project model exists
        }),
        ('⚙️ Settings', {
            'fields': ('settings',),
            'classes': ['collapse'],
        }),
        ('📅 Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ['collapse'],
        }),
    )
    
    inlines = [WorkspaceMembershipInline]
    
    actions = [
        'archive_workspaces', 
        'activate_workspaces', 
        'make_private', 
        'make_public'
    ]
    
    def get_queryset(self, request):
        """Optimize queries with related data"""
        return super().get_queryset(request).select_related(
            'organization', 'created_by'
        ).prefetch_related(
            'memberships__user'
        ).annotate(
            active_member_count=Count(
                'memberships', 
                filter=Q(memberships__is_active=True)
            )
        )
    
    def workspace_icon(self, obj):
        """Display workspace with color and type icon"""
        type_icons = {
            'development': '💻',
            'marketing': '📢', 
            'design': '🎨',
            'sales': '💼',
            'support': '🎧',
            'operations': '⚙️',
            'finance': '💰',
            'hr': '👥',
            'general': '📋',
            'client': '🤝',
        }
        
        icon = type_icons.get(obj.workspace_type, '📋')
        
        return format_html(
            '<div style="display:flex;align-items:center;">'
            '<div style="width:20px;height:20px;background:{};border-radius:3px;display:flex;align-items:center;justify-content:center;margin-right:8px;font-size:12px;">{}</div>'
            '</div>',
            obj.color,
            icon
        )
    workspace_icon.short_description = ''
    
    def organization_link(self, obj):
        """Link to organization admin"""
        url = reverse('admin:organizations_organization_change', args=[obj.organization.pk])
        return format_html('<a href="{}">{}</a>', url, obj.organization.name)
    organization_link.short_description = "Organization"
    
    def member_count_display(self, obj):
        """Display member count with status"""
        count = getattr(obj, 'active_member_count', obj.get_member_count())
        
        # Check if approaching limits
        org_limits = obj.organization.get_usage_limits()
        if count >= org_limits['max_users'] * 0.9:  # 90% of limit
            return format_html(
                '<span style="color: orange;" title="Approaching user limit">{} members ⚠️</span>',
                count
            )
        elif count >= org_limits['max_users']:
            return format_html(
                '<span style="color: red;" title="Exceeded user limit">{} members ❌</span>',
                count
            )
        
        return f"{count} members"
    member_count_display.short_description = "Members"
    
    # TODO: Uncomment when Project model is implemented
    # def project_count_display(self, obj):
    #     """Display project count"""
    #     count = obj.get_project_count()
    #     return f"{count} projects"
    # project_count_display.short_description = "Projects"
    
    def created_by_email(self, obj):
        """Link to creator's user admin"""
        url = reverse('admin:users_user_change', args=[obj.created_by.pk])
        return format_html('<a href="{}">{}</a>', url, obj.created_by.email)
    created_by_email.short_description = "Created By"
    
    def organization_limits_status(self, obj):
        """Show organization limits compliance"""
        limits = obj.organization.get_usage_limits()
        current_workspaces = obj.organization.workspaces.filter(deleted_at__isnull=True).count()
        
        status_color = 'green'
        if current_workspaces >= limits['max_workspaces']:
            status_color = 'red'
        elif current_workspaces >= limits['max_workspaces'] * 0.9:
            status_color = 'orange'
        
        return format_html(
            '<span style="color: {};">Workspaces: {}/{}</span>',
            status_color,
            current_workspaces,
            limits['max_workspaces']
        )
    organization_limits_status.short_description = "Org Limits"
    
    # Bulk actions
    def archive_workspaces(self, request, queryset):
        """Archive selected workspaces"""
        count = 0
        for workspace in queryset:
            workspace.soft_delete()
            count += 1
        
        self.message_user(request, f"📦 {count} workspaces archived.")
        logger.info(f"Admin bulk archived {count} workspaces", extra={'admin_user': request.user.email})
    archive_workspaces.short_description = "📦 Archive selected workspaces"
    
    def activate_workspaces(self, request, queryset):
        """Activate selected workspaces"""
        count = queryset.update(status=Workspace.Status.ACTIVE, deleted_at=None)
        self.message_user(request, f"✅ {count} workspaces activated.")
        logger.info(f"Admin bulk activated {count} workspaces", extra={'admin_user': request.user.email})
    activate_workspaces.short_description = "✅ Activate selected workspaces"
    
    def make_private(self, request, queryset):
        """Make selected workspaces private"""
        count = queryset.update(is_private=True)
        self.message_user(request, f"🔒 {count} workspaces made private.")
    make_private.short_description = "🔒 Make private"
    
    def make_public(self, request, queryset):
        """Make selected workspaces public"""
        count = queryset.update(is_private=False)
        self.message_user(request, f"🔓 {count} workspaces made public.")
    make_public.short_description = "🔓 Make public"


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    """
    Admin interface for workspace membership management.
    
    Essential for:
    - Resolving user access issues
    - Managing team permissions
    - Tracking user engagement
    - Handling membership disputes
    """
    
    list_display = [
        'user_email',
        'workspace_name',
        'organization_name',
        'role',
        'is_active',
        'joined_at',
        'last_active_at',
        'activity_status',
    ]
    
    list_filter = [
        'role',
        'is_active',
        'joined_at',
        'workspace__workspace_type',
        'workspace__organization__status',
    ]
    
    search_fields = [
        'user__email',
        'user__first_name',
        'user__last_name',
        'workspace__name',
        'workspace__organization__name',
    ]
    
    readonly_fields = ['joined_at', 'last_active_at', 'activity_status']
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related(
            'user', 'workspace', 'workspace__organization', 'invited_by'
        )
    
    def user_email(self, obj):
        """Link to user admin"""
        url = reverse('admin:users_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_email.short_description = "User"
    
    def workspace_name(self, obj):
        """Link to workspace admin"""
        url = reverse('admin:workspaces_workspace_change', args=[obj.workspace.pk])
        return format_html('<a href="{}">{}</a>', url, obj.workspace.name)
    workspace_name.short_description = "Workspace"
    
    def organization_name(self, obj):
        """Link to organization admin"""
        url = reverse('admin:organizations_organization_change', args=[obj.workspace.organization.pk])
        return format_html('<a href="{}">{}</a>', url, obj.workspace.organization.name)
    organization_name.short_description = "Organization"
    
    def activity_status(self, obj):
        """Show user activity status in workspace"""
        if not obj.last_active_at:
            return "Never active"
        
        days_since_active = (timezone.now() - obj.last_active_at).days
        
        if days_since_active == 0:
            return format_html('<span style="color: green;">Active today</span>')
        elif days_since_active <= 7:
            return format_html('<span style="color: orange;">{}d ago</span>', days_since_active)
        else:
            return format_html('<span style="color: red;">{}d ago</span>', days_since_active)
    activity_status.short_description = "Activity"