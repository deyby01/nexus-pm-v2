"""
NexusPM Enterprise - User Signals

This module contains Django signal handlers for the User model.
Signals allow us to hook into the Django model lifecycle to perform
automatic actions when users are created, updated, or deleted.

Following Clean Architecture, signals handle cross-cutting concerns
like logging, notifications, and audit trails without coupling
business logic to the models themselves.
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger('nexuspm.users')


@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    """
    Handle actions when a user is created or updated.
    
    Actions on creation:
    - Log user creation for audit trail
    - Send welcome email (future)
    - Create default user preferences (future)
    
    Actions on update:
    - Log significant changes (future)
    - Update related caches (future)
    """
    if created:
        logger.info(
            f"New user created: {instance.email} (ID: {instance.id})",
            extra={
                'user_id': str(instance.id),
                'email': instance.email,
                'action': 'user_created'
            }
        )
        
        # TODO: Send welcome email via Celery task
        # TODO: Create default user preferences
        # TODO: Track user acquisition metrics


@receiver(pre_delete, sender=User)
def user_deleted_handler(sender, instance, **kwargs):
    """
    Handle actions before a user is deleted.
    
    Note: In our architecture, we use soft deletes via the soft_delete()
    method, so this signal typically won't fire. However, it's here
    for completeness and future hard delete scenarios.
    """
    logger.warning(
        f"User being deleted: {instance.email} (ID: {instance.id})",
        extra={
            'user_id': str(instance.id),
            'email': instance.email,
            'action': 'user_deleted'
        }
    )
    
    # TODO: Anonymize user data if required by GDPR
    # TODO: Transfer ownership of resources
    # TODO: Notify related users