"""
NexusPM Enterprise - Projects & Tasks Signals

This module handles automatic actions for project and task lifecycle events.
Critical for maintaining data consistency, calculating metrics, and
implementing business rules in the project management domain.

Key Responsibilities:
- Project progress calculation when tasks change
- Automatic project member addition for task creators/assignees
- Workspace project count maintenance
- Dependency validation and workflow enforcement
- Timeline tracking and deadline notifications
- Audit logging for project management activities
"""

from django.db.models.signals import post_save, pre_delete, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

from .models import Project, Task, ProjectMembership, TaskDependency

User = get_user_model()
logger = logging.getLogger('nexuspm.projects')


@receiver(post_save, sender=Project)
def project_created_handler(sender, instance, created, **kwargs):
    """
    Handle actions when a project is created.
    
    Enterprise SaaS Pattern:
    - Add creator as project lead automatically
    - Update workspace project count cache
    - Initialize default project settings
    - Set up project tracking and analytics
    """
    if created:
        logger.info(
            f"New project created: {instance.name} in {instance.workspace.name}",
            extra={
                'project_id': str(instance.id),
                'project_name': instance.name,
                'workspace_id': str(instance.workspace.id),
                'organization_id': str(instance.workspace.organization.id),
                'created_by': instance.created_by.email,
                'action': 'project_created'
            }
        )
        
        # 1. Add creator as project lead automatically
        ProjectMembership.objects.get_or_create(
            user=instance.created_by,
            project=instance,
            defaults={
                'role': ProjectMembership.Role.LEAD,
                'is_active': True,
                'assigned_by': instance.created_by  # Self-assigned
            }
        )
        
        logger.info(f"Added {instance.created_by.email} as lead of project {instance.name}")
        
        # 2. Update workspace project count cache
        workspace = instance.workspace
        workspace.project_count = workspace.projects.filter(deleted_at__isnull=True).count()
        workspace.save(update_fields=['project_count'])
        
        # 3. Initialize default project settings based on workspace type
        if not instance.settings:
            workspace_defaults = workspace.get_default_settings()
            instance.settings = {
                'workflow': workspace_defaults.get('default_project_template', 'general'),
                'task_statuses': workspace_defaults.get('default_task_statuses', ['To Do', 'In Progress', 'Done']),
                'enable_time_tracking': workspace_defaults.get('enable_time_tracking', False),
                'notifications': {
                    'task_assignments': True,
                    'due_date_reminders': True,
                    'status_changes': True
                }
            }
            instance.save(update_fields=['settings'])
        
        # 4. Add project manager as member if specified and different from creator
        if instance.project_manager and instance.project_manager != instance.created_by:
            ProjectMembership.objects.get_or_create(
                user=instance.project_manager,
                project=instance,
                defaults={
                    'role': ProjectMembership.Role.LEAD,
                    'is_active': True,
                    'assigned_by': instance.created_by
                }
            )
            logger.info(f"Added project manager {instance.project_manager.email} to project {instance.name}")


@receiver(post_save, sender=Task)
def task_changed_handler(sender, instance, created, **kwargs):
    """
    Handle task lifecycle events.
    
    Critical for project management:
    - Update project progress when tasks complete
    - Automatic project member addition for assignees
    - Dependency workflow management
    - Timeline and deadline tracking
    """
    if created:
        logger.info(
            f"New task created: {instance.title} in project {instance.project.name}",
            extra={
                'task_id': str(instance.id),
                'task_title': instance.title,
                'project_id': str(instance.project.id),
                'assignee': instance.assignee.email if instance.assignee else None,
                'priority': instance.priority,
                'created_by': instance.created_by.email,
                'action': 'task_created'
            }
        )
        
        # 1. Add task creator to project if not already a member
        if not instance.project.memberships.filter(user=instance.created_by, is_active=True).exists():
            ProjectMembership.objects.create(
                user=instance.created_by,
                project=instance.project,
                role=ProjectMembership.Role.MEMBER,
                is_active=True,
                assigned_by=instance.created_by
            )
            logger.info(f"Auto-added task creator {instance.created_by.email} to project {instance.project.name}")
        
        # 2. Add assignee to project if specified and not already a member
        if instance.assignee and not instance.project.memberships.filter(user=instance.assignee, is_active=True).exists():
            ProjectMembership.objects.create(
                user=instance.assignee,
                project=instance.project,
                role=ProjectMembership.Role.MEMBER,
                is_active=True,
                assigned_by=instance.created_by
            )
            logger.info(f"Auto-added task assignee {instance.assignee.email} to project {instance.project.name}")
    
    # 3. Handle status changes and recalculate project progress
    if not created:
        # Always recalculate project progress when task status changes
        instance.project.calculate_progress_percentage()
        
        # Check if status changed to completed
        if instance.status in [Task.Status.COMPLETED, Task.Status.VERIFIED]:
            logger.info(
                f"Task completed: {instance.title} by {instance.assignee.email if instance.assignee else 'unknown'}",
                extra={
                    'task_id': str(instance.id),
                    'project_id': str(instance.project.id),
                    'assignee': instance.assignee.email if instance.assignee else None,
                    'action': 'task_completed'
                }
            )
            
            # Check if this unblocks other tasks
            dependent_tasks = instance.dependent_tasks.filter(
                status=Task.Status.BLOCKED,
                deleted_at__isnull=True
            )
            
            for dependent_task in dependent_tasks:
                if dependent_task.can_start():  # No other blocking dependencies
                    dependent_task.status = Task.Status.TODO
                    dependent_task.save()
                    logger.info(f"Unblocked task: {dependent_task.title}")


@receiver(post_save, sender=TaskDependency)
def dependency_created_handler(sender, instance, created, **kwargs):
    """
    Handle task dependency creation.
    Updates task statuses based on new dependencies.
    """
    if created:
        logger.info(
            f"New dependency created: {instance.from_task.title} blocks {instance.to_task.title}",
            extra={
                'from_task_id': str(instance.from_task.id),
                'to_task_id': str(instance.to_task.id),
                'dependency_type': instance.dependency_type,
                'action': 'dependency_created'
            }
        )
        
        # Update dependent task status if it should be blocked
        if instance.dependency_type == TaskDependency.DependencyType.BLOCKS:
            if instance.to_task.status == Task.Status.TODO and instance.to_task.is_blocked:
                instance.to_task.status = Task.Status.BLOCKED
                instance.to_task.save()
                logger.info(f"Blocked task due to new dependency: {instance.to_task.title}")


@receiver(pre_delete, sender=Project)
def project_deleting_handler(sender, instance, **kwargs):
    """Handle actions before a project is deleted"""
    logger.warning(
        f"Project being deleted: {instance.name} in {instance.workspace.name}",
        extra={
            'project_id': str(instance.id),
            'project_name': instance.name,
            'workspace_id': str(instance.workspace.id),
            'task_count': instance.tasks.filter(deleted_at__isnull=True).count(),
            'action': 'project_deleting'
        }
    )
    
    # Update workspace project count
    workspace = instance.workspace
    workspace.project_count = workspace.projects.filter(deleted_at__isnull=True).exclude(id=instance.id).count()
    workspace.save(update_fields=['project_count'])


@receiver(pre_delete, sender=Task)
def task_deleting_handler(sender, instance, **kwargs):
    """Handle task deletion and dependency cleanup"""
    logger.info(
        f"Task being deleted: {instance.title} from project {instance.project.name}",
        extra={
            'task_id': str(instance.id),
            'project_id': str(instance.project.id),
            'action': 'task_deleting'
        }
    )
    
    # Remove all dependencies involving this task
    TaskDependency.objects.filter(
        models.Q(from_task=instance) | models.Q(to_task=instance)
    ).delete()
    
    # Update project progress after task deletion
    instance.project.calculate_progress_percentage()