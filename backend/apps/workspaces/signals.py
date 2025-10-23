"""
NexusPM Enterprise - Workspaces Signals

This module handles automatic actions when workspaces are created, updated,
or when memberships change. Essential for maintaining data consistency
and implementing business rules in a multi-tenant environment.

Key Responsibilities:
- Automatic workspace setup and configuration
- Member limit enforcement based on organization subscription
- Default settings initialization per workspace type
- Audit logging for compliance and troubleshooting
- Cache invalidation for performance optimization
"""

from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

from .models import Workspace, WorkspaceMembership

User = get_user_model()
logger = logging.getLogger('nexuspm.workspaces')


@receiver(post_save, sender=Workspace)
def workspace_created_handler(sender, instance, created, **kwargs):
    """
    Handle actions when a workspace is created.
    
    Enterprise SaaS Pattern:
    - Set up default configurations based on workspace type
    - Add creator as workspace admin automatically
    - Initialize workspace-specific settings
    - Validate organization limits
    """
    if created:
        logger.info(
            f"New workspace created: {instance.name} in {instance.organization.name}",
            extra={
                'workspace_id': str(instance.id),
                'workspace_name': instance.name,
                'organization_id': str(instance.organization.id),
                'workspace_type': instance.workspace_type,
                'created_by': instance.created_by.email,
                'action': 'workspace_created'
            }
        )
        
        # 1. Add creator as workspace admin automatically
        WorkspaceMembership.objects.get_or_create(
            user=instance.created_by,
            workspace=instance,
            defaults={
                'role': WorkspaceMembership.Role.ADMIN,
                'is_active': True,
                'joined_at': timezone.now()
            }
        )
        
        logger.info(f"Added {instance.created_by.email} as admin of workspace {instance.name}")
        
        # 2. Initialize default settings based on workspace type
        if not instance.settings:
            instance.settings = instance.get_default_settings()
            instance.save(update_fields=['settings'])
            
            logger.info(f"Initialized default settings for {instance.workspace_type} workspace")
        
        # 3. Validate organization limits (post-creation check)
        if not instance.organization.check_usage_limit('workspaces'):
            logger.warning(
                f"Organization {instance.organization.name} may have exceeded workspace limits",
                extra={
                    'organization_id': str(instance.organization.id),
                    'workspace_count': instance.organization.workspaces.filter(deleted_at__isnull=True).count(),
                    'action': 'workspace_limit_warning'
                }
            )
        
        # TODO: Send workspace creation notification to organization admins
        # TODO: Track workspace creation analytics
        # TODO: Set up default project templates based on workspace type


@receiver(post_save, sender=WorkspaceMembership)
def workspace_membership_changed_handler(sender, instance, created, **kwargs):
    """
    Handle workspace membership changes.
    
    Critical for:
    - User access management
    - Audit trail maintenance
    - Cache invalidation for permissions
    - Usage analytics tracking
    """
    if created:
        logger.info(
            f"New workspace member: {instance.user.email} → {instance.workspace.name} ({instance.role})",
            extra={
                'user_id': str(instance.user.id),
                'workspace_id': str(instance.workspace.id),
                'organization_id': str(instance.workspace.organization.id),
                'role': instance.role,
                'invited_by': instance.invited_by.email if instance.invited_by else None,
                'action': 'workspace_member_added'
            }
        )
        
        # Update cached member count
        active_count = instance.workspace.memberships.filter(is_active=True).count()
        instance.workspace.member_count = active_count
        instance.workspace.save(update_fields=['member_count'])
        
        # Check organization user limits
        org_total_members = instance.workspace.organization.memberships.filter(is_active=True).count()
        org_limits = instance.workspace.organization.get_usage_limits()
        
        if org_total_members > org_limits['max_users']:
            logger.warning(
                f"Organization {instance.workspace.organization.name} may have exceeded user limits: "
                f"{org_total_members}/{org_limits['max_users']}",
                extra={
                    'organization_id': str(instance.workspace.organization.id),
                    'current_users': org_total_members,
                    'max_users': org_limits['max_users'],
                    'action': 'user_limit_warning'
                }
            )
    
    # Handle activation/deactivation
    if hasattr(instance, '_previous_is_active') and instance._previous_is_active != instance.is_active:
        action = 'member_activated' if instance.is_active else 'member_deactivated'
        
        logger.info(
            f"Workspace membership {action}: {instance.user.email} → {instance.workspace.name}",
            extra={
                'user_id': str(instance.user.id),
                'workspace_id': str(instance.workspace.id),
                'action': action
            }
        )
        
        # Update cached member count
        active_count = instance.workspace.memberships.filter(is_active=True).count()
        instance.workspace.member_count = active_count
        instance.workspace.save(update_fields=['member_count'])
    
    # TODO: Send workspace access notification to user
    # TODO: Update user's workspace access cache
    # TODO: Track member engagement analytics


@receiver(pre_delete, sender=Workspace)
def workspace_deleting_handler(sender, instance, **kwargs):
    """
    Handle actions before a workspace is deleted.
    
    Enterprise Data Management:
    - Ensure proper cleanup of related data
    - Maintain audit trail for compliance
    - Handle cascade deletion policies
    - Notify affected users
    """
    logger.warning(
        f"Workspace being deleted: {instance.name} in {instance.organization.name}",
        extra={
            'workspace_id': str(instance.id),
            'workspace_name': instance.name,
            'organization_id': str(instance.organization.id),
            'project_count': instance.get_project_count(),
            'member_count': instance.get_member_count(),
            'action': 'workspace_deleting'
        }
    )
    
    # Log affected members for audit trail
    affected_members = instance.get_active_members()
    for membership in affected_members:
        logger.info(
            f"User {membership.user.email} will lose access to workspace {instance.name}",
            extra={
                'user_id': str(membership.user.id),
                'workspace_id': str(instance.id),
                'action': 'member_access_removed'
            }
        )
    
    # TODO: Send notification to workspace members about deletion
    # TODO: Archive or transfer projects to another workspace
    # TODO: Update organization workspace count cache


# Track membership changes for audit logging
@receiver(post_save, sender=WorkspaceMembership)
def track_membership_changes(sender, instance, **kwargs):
    """Track previous state for change detection"""
    if instance.pk:
        try:
            previous = WorkspaceMembership.objects.get(pk=instance.pk)
            instance._previous_is_active = previous.is_active
        except WorkspaceMembership.DoesNotExist:
            instance._previous_is_active = None