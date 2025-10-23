"""
NexusPM Enterprise - Workspaces Models (FIXED)

This module implements team-level organization within multi-tenant organizations.
Workspaces serve as containers for projects and provide granular access control
at the team level, essential for enterprise-scale project management.

Note: Project-related methods are temporarily commented out until Projects model is implemented.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError

User = get_user_model()


class WorkspaceMembership(models.Model):
    """
    Represents a User's membership in a Workspace.
    
    This provides granular access control at the team level, allowing
    organizations to control which users can access which teams/departments.
    
    Permission Hierarchy:
    1. Organization membership (base requirement)
    2. Workspace membership (team access)  
    3. Project access (inherited from workspace)
    4. Task permissions (inherited from project)
    
    Business Logic:
    - User must be Organization member to join Workspace
    - Workspace roles can be more restrictive than Organization roles
    - Users can have different roles in different workspaces
    - Invitations are scoped to workspace level
    """
    
    class Role(models.TextChoices):
        """
        Workspace-level roles for team management.
        These are more granular than organization roles.
        """
        ADMIN = 'admin', 'Workspace Admin'     # Full workspace control
        MANAGER = 'manager', 'Project Manager' # Project creation & management
        MEMBER = 'member', 'Team Member'       # Standard team access
        CONTRIBUTOR = 'contributor', 'Contributor' # Limited access (contractors)
        VIEWER = 'viewer', 'Viewer'            # Read-only team access
    
    # Relationships
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='workspace_memberships',
        help_text="User who is a member of this workspace"
    )
    workspace = models.ForeignKey(
        'Workspace',  # Forward reference
        on_delete=models.CASCADE,
        related_name='memberships',
        help_text="Workspace the user belongs to"
    )
    
    # Membership details
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        help_text="User's role within this workspace"
    )
    
    # Status and activity
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this membership is currently active"
    )
    
    # Invitation system
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_workspace_invites',
        help_text="User who invited this member to the workspace"
    )
    invited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the workspace invitation was sent"
    )
    
    # Activity tracking
    joined_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the user joined this workspace"
    )
    last_active_at = models.DateTimeField(
        auto_now=True,
        help_text="When the user was last active in this workspace"
    )
    
    class Meta:
        db_table = 'workspaces_membership'
        verbose_name = 'Workspace Membership'
        verbose_name_plural = 'Workspace Memberships'
        unique_together = ['user', 'workspace']
        indexes = [
            models.Index(fields=['workspace', 'role']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['last_active_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} → {self.workspace.name} ({self.role})"
    
    def clean(self):
        """
        Custom validation to ensure business rules.
        This is enterprise-grade validation.
        """
        super().clean()
        
        # Rule 1: User must be a member of the workspace's organization
        if hasattr(self, 'user') and hasattr(self, 'workspace'):
            org_membership = self.user.organization_memberships.filter(
                organization=self.workspace.organization,
                is_active=True
            ).first()
            
            if not org_membership:
                raise ValidationError(
                    f"User {self.user.email} must be a member of organization "
                    f"'{self.workspace.organization.name}' before joining this workspace."
                )
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)
    
    def has_permission(self, permission):
        """
        Check workspace-level permissions.
        These are more granular than organization permissions.
        """
        workspace_permissions = {
            self.Role.ADMIN: [
                'manage_workspace_settings',
                'manage_workspace_members', 
                'create_projects',
                'delete_projects',
                'manage_all_tasks',
                'view_workspace_analytics'
            ],
            self.Role.MANAGER: [
                'create_projects',
                'manage_own_projects',
                'assign_tasks',
                'view_team_analytics'
            ],
            self.Role.MEMBER: [
                'view_projects',
                'create_tasks',
                'manage_own_tasks',
                'comment_on_tasks'
            ],
            self.Role.CONTRIBUTOR: [
                'view_assigned_projects',
                'manage_assigned_tasks',
                'comment_on_tasks'
            ],
            self.Role.VIEWER: [
                'view_projects',
                'view_tasks',
                'view_comments'
            ],
        }
        
        user_permissions = workspace_permissions.get(self.role, [])
        return permission in user_permissions
    
    @property
    def effective_role(self):
        """
        Get the effective role considering both organization and workspace roles.
        Organization Owner/Admin can override workspace restrictions.
        """
        # Check organization role
        org_membership = self.user.organization_memberships.filter(
            organization=self.workspace.organization,
            is_active=True
        ).first()
        
        if org_membership and org_membership.role in ['owner', 'admin']:
            return 'admin'  # Organization admins have full workspace access
        
        return self.role


class Workspace(models.Model):
    """
    Team containers within Organizations for project grouping and access control.
    
    Workspaces provide the middle layer of our multi-tenant architecture:
    Organization → Workspace → Project → Task
    
    Key Responsibilities:
    - Team-level data organization and access control
    - Project container and categorization
    - Team-specific settings and workflows
    - Resource allocation within organization limits
    - Granular permission boundaries for enterprise security
    """
    
    class Status(models.TextChoices):
        """Workspace lifecycle states"""
        ACTIVE = 'active', 'Active'           # Normal operational state
        ARCHIVED = 'archived', 'Archived'     # Completed/inactive projects
        SUSPENDED = 'suspended', 'Suspended'  # Temporarily disabled
    
    class WorkspaceType(models.TextChoices):
        """
        Workspace types for better categorization and UX.
        Used for icons, default settings, and workflow suggestions.
        """
        DEVELOPMENT = 'development', 'Development Team'
        MARKETING = 'marketing', 'Marketing Team'
        DESIGN = 'design', 'Design Team'
        SALES = 'sales', 'Sales Team'
        SUPPORT = 'support', 'Customer Support'
        OPERATIONS = 'operations', 'Operations Team'
        FINANCE = 'finance', 'Finance Team'
        HR = 'hr', 'Human Resources'
        GENERAL = 'general', 'General Purpose'
        CLIENT = 'client', 'Client Project'  # For agencies
    
    # Primary identification
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this workspace"
    )
    
    # Basic information
    name = models.CharField(
        max_length=100,
        help_text="Workspace name (e.g., 'Engineering Team', 'Client Projects')"
    )
    slug = models.SlugField(
        max_length=100,
        help_text="URL-friendly identifier within the organization"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the workspace purpose and scope"
    )
    
    # Organizational relationship
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='workspaces',
        help_text="Organization this workspace belongs to"
    )
    
    # Workspace categorization
    workspace_type = models.CharField(
        max_length=20,
        choices=WorkspaceType.choices,
        default=WorkspaceType.GENERAL,
        help_text="Type of workspace for better organization and UX"
    )
    
    # Status and visibility
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Current operational status of the workspace"
    )
    is_private = models.BooleanField(
        default=False,
        help_text="Whether this workspace is private (invitation-only)"
    )
    
    # Management and ownership
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_workspaces',
        help_text="User who created this workspace"
    )
    
    # Visual customization
    color = models.CharField(
        max_length=7,
        default='#3B82F6',  # Blue
        help_text="Hex color for workspace branding and UI"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon identifier for workspace display"
    )
    
    # Team member relationships
    members = models.ManyToManyField(
        User,
        through='WorkspaceMembership',
        through_fields=('workspace', 'user'),
        related_name='workspaces',
        help_text="Users who are members of this workspace"
    )
    
    # Settings and configuration
    settings = models.JSONField(
        default=dict,
        help_text="Workspace-specific settings and preferences"
    )
    
    # Usage tracking (for analytics and limits)
    project_count = models.PositiveIntegerField(
        default=0,
        help_text="Cached count of active projects in this workspace"
    )
    member_count = models.PositiveIntegerField(
        default=0,
        help_text="Cached count of active members in this workspace"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'workspaces_workspace'
        verbose_name = 'Workspace'
        verbose_name_plural = 'Workspaces'
        unique_together = ['organization', 'slug']  # Slug unique within organization
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['created_by']),
            models.Index(fields=['workspace_type', 'status']),
            models.Index(fields=['is_private', 'status']),
        ]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.organization.name} → {self.name}"
    
    def save(self, *args, **kwargs):
        """Auto-generate slug and validate business rules"""
        # Auto-generate slug from name if not provided
        if not self.slug:
            self.slug = slugify(self.name)
            
            # Ensure slug uniqueness within organization
            counter = 1
            original_slug = self.slug
            while Workspace.objects.filter(
                organization=self.organization,
                slug=self.slug
            ).exclude(id=self.id).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """
        Enterprise-grade validation for business rules.
        This ensures data integrity and business logic compliance.
        """
        super().clean()
        
        # Rule 1: Check organization workspace limits
        if not self.pk:  # Only for new workspaces
            if not self.organization.check_usage_limit('workspaces'):
                limits = self.organization.get_usage_limits()
                raise ValidationError(
                    f"Organization '{self.organization.name}' has reached its workspace limit "
                    f"of {limits['max_workspaces']}. Upgrade subscription to create more workspaces."
                )
        
        # Rule 2: Creator must be organization member
        if hasattr(self, 'created_by') and hasattr(self, 'organization'):
            if not self.created_by.organization_memberships.filter(
                organization=self.organization,
                is_active=True
            ).exists():
                raise ValidationError(
                    f"User {self.created_by.email} must be a member of organization "
                    f"'{self.organization.name}' to create workspaces."
                )
    
    # Business logic methods
    def get_active_members(self):
        """Get all active members of this workspace"""
        return self.memberships.filter(is_active=True).select_related('user')
    
    def get_member_count(self):
        """Get cached or computed active member count"""
        return self.member_count or self.memberships.filter(is_active=True).count()
    
    def get_project_count(self):
        """Get cached or computed active project count (placeholder for now)"""
        # TODO: Implement when Project model is created
        # return self.project_count or self.projects.filter(deleted_at__isnull=True).count()
        return self.project_count  # Return cached value for now
    
    def can_user_access(self, user):
        """
        Check if a user can access this workspace.
        
        Access Rules:
        1. User must be organization member
        2. If workspace is private, user must be workspace member
        3. If workspace is public, organization membership is sufficient
        """
        # Check organization membership first
        org_membership = user.organization_memberships.filter(
            organization=self.organization,
            is_active=True
        ).first()
        
        if not org_membership:
            return False
        
        # Organization owners and admins always have access
        if org_membership.role in ['owner', 'admin']:
            return True
        
        # For private workspaces, explicit membership required
        if self.is_private:
            return self.memberships.filter(
                user=user,
                is_active=True
            ).exists()
        
        # Public workspaces are accessible to all org members
        return True
    
    def add_member(self, user, role=WorkspaceMembership.Role.MEMBER, invited_by=None):
        """
        Add a user as a member of this workspace.
        
        This is the primary way to grant workspace access.
        Includes validation and automatic setup.
        """
        # Validation
        if not self.can_user_access(user):
            raise ValidationError(
                f"User {user.email} cannot be added to workspace '{self.name}'. "
                f"User must be a member of organization '{self.organization.name}'."
            )
        
        # Create or update membership
        membership, created = WorkspaceMembership.objects.get_or_create(
            user=user,
            workspace=self,
            defaults={
                'role': role,
                'is_active': True,
                'invited_by': invited_by,
                'invited_at': timezone.now() if invited_by else None,
            }
        )
        
        if not created:
            # Reactivate if was previously inactive
            membership.is_active = True
            membership.role = role
            membership.save(update_fields=['is_active', 'role'])
        
        # Update cached member count
        self.member_count = self.memberships.filter(is_active=True).count()
        self.save(update_fields=['member_count'])
        
        return membership
    
    def remove_member(self, user):
        """Remove a user from this workspace"""
        self.memberships.filter(user=user).update(is_active=False)
        
        # Update cached member count
        self.member_count = self.memberships.filter(is_active=True).count()
        self.save(update_fields=['member_count'])
    
    def get_default_settings(self):
        """
        Get default settings for new workspaces.
        These can be customized per workspace type.
        """
        type_defaults = {
            self.WorkspaceType.DEVELOPMENT: {
                'default_project_template': 'agile_scrum',
                'enable_time_tracking': True,
                'enable_code_integration': True,
                'default_task_statuses': ['Backlog', 'In Progress', 'Code Review', 'Testing', 'Done'],
            },
            self.WorkspaceType.MARKETING: {
                'default_project_template': 'campaign',
                'enable_asset_management': True,
                'enable_approval_workflows': True,
                'default_task_statuses': ['Ideas', 'Planning', 'In Progress', 'Review', 'Published'],
            },
            self.WorkspaceType.DESIGN: {
                'default_project_template': 'design_sprint',
                'enable_asset_management': True,
                'enable_version_control': True,
                'default_task_statuses': ['Concept', 'Design', 'Review', 'Approved', 'Delivered'],
            }
        }
        
        # Get type-specific defaults or use general defaults
        return type_defaults.get(self.workspace_type, {
            'default_project_template': 'general',
            'enable_time_tracking': False,
            'default_task_statuses': ['To Do', 'In Progress', 'Done'],
        })
    
    def soft_delete(self):
        """
        Soft delete the workspace and handle related data.
        
        Enterprise pattern: Don't actually delete, just mark as deleted
        for audit trail and data recovery purposes.
        """
        self.deleted_at = timezone.now()
        self.status = self.Status.ARCHIVED
        self.save(update_fields=['deleted_at', 'status'])
        
        # TODO: Soft delete all projects in this workspace when Project model exists
        
    def restore(self):
        """Restore a soft-deleted workspace"""
        self.deleted_at = None
        self.status = self.Status.ACTIVE
        self.save(update_fields=['deleted_at', 'status'])
    
    @property
    def is_over_member_limit(self):
        """Check if workspace exceeds organization's user limits"""
        org_limits = self.organization.get_usage_limits()
        return self.get_member_count() > org_limits['max_users']
    
    @property
    def is_over_project_limit(self):
        """Check if workspace exceeds project limits (placeholder)"""
        # TODO: Implement when Project model is created
        org_limits = self.organization.get_usage_limits()
        return self.get_project_count() > org_limits['max_projects_per_workspace']