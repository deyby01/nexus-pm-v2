"""
NexusPM Enterprise - Organizations Signals

This module handles automatic actions when organizations are created, updated,
or when subscriptions change. Following Clean Architecture, signals keep
business logic separate from models while ensuring consistency.

Key Responsibilities:
- Create default subscription for new organizations
- Set up initial organization settings and preferences
- Handle subscription lifecycle events (activated, cancelled, etc.)
- Ensure data consistency across related entities
- Audit logging for compliance and debugging
"""

from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

from .models import Organization, Subscription, SubscriptionPlan, OrganizationMembership

User = get_user_model()
logger = logging.getLogger('nexuspm.organizations')


@receiver(post_save, sender=Organization)
def organization_created_handler(sender, instance, created, **kwargs):
    """
    Handle actions when an organization is created.
    
    This is critical for SaaS setup - every new organization needs:
    1. A default subscription (usually Free plan)
    2. The owner as the first member with Owner role
    3. Default organization settings
    4. Audit logging for tracking
    """
    if created:
        logger.info(
            f"New organization created: {instance.name} (ID: {instance.id})",
            extra={
                'organization_id': str(instance.id),
                'organization_name': instance.name,
                'owner_email': instance.owner.email,
                'action': 'organization_created'
            }
        )
        
        # 1. Create default Free subscription
        try:
            free_plan = SubscriptionPlan.objects.get(plan_type=SubscriptionPlan.PlanType.FREE)
            
            # Create subscription with trial period (common SaaS pattern)
            trial_end = timezone.now() + timezone.timedelta(days=14)  # 14-day trial
            
            Subscription.objects.create(
                organization=instance,
                plan=free_plan,
                status=Subscription.Status.TRIALING,
                billing_cycle=Subscription.BillingCycle.MONTHLY,
                current_period_start=timezone.now(),
                current_period_end=trial_end,
                trial_start=timezone.now(),
                trial_end=trial_end
            )
            
            logger.info(f"Created Free trial subscription for organization {instance.name}")
            
        except SubscriptionPlan.DoesNotExist:
            logger.error(f"Free plan not found! Cannot create subscription for {instance.name}")
        
        # 2. Make the owner the first member with Owner role
        OrganizationMembership.objects.get_or_create(
            user=instance.owner,
            organization=instance,
            defaults={
                'role': OrganizationMembership.Role.OWNER,
                'is_active': True,
                'joined_at': timezone.now()
            }
        )
        
        logger.info(f"Added owner {instance.owner.email} as Owner of {instance.name}")
        
        # 3. Set up default organization settings
        default_settings = {
            'created_via': 'web',  # Could be 'api', 'invitation', etc.
            'onboarding_completed': False,
            'notifications': {
                'email_project_updates': True,
                'email_task_assignments': True,
                'email_mentions': True,
            },
            'preferences': {
                'default_timezone': instance.owner.timezone,
                'default_language': instance.owner.language,
                'week_starts_on': 'monday',
            }
        }
        
        # Update settings if empty
        if not instance.settings:
            instance.settings = default_settings
            instance.save(update_fields=['settings'])
        
        # TODO: Send welcome email to organization owner
        # TODO: Track organization creation in analytics
        # TODO: Create default workspace (if that's part of your UX)


@receiver(post_save, sender=Subscription)
def subscription_changed_handler(sender, instance, created, **kwargs):
    """
    Handle subscription lifecycle events.
    
    This is crucial for SaaS business logic:
    - When subscriptions activate/cancel, update organization access
    - Handle upgrades/downgrades
    - Enforce usage limits based on plan changes
    """
    if created:
        logger.info(
            f"New subscription created: {instance.organization.name} → {instance.plan.name}",
            extra={
                'organization_id': str(instance.organization.id),
                'plan_type': instance.plan.plan_type,
                'billing_cycle': instance.billing_cycle,
                'action': 'subscription_created'
            }
        )
    else:
        logger.info(
            f"Subscription updated: {instance.organization.name} → {instance.plan.name} ({instance.status})",
            extra={
                'organization_id': str(instance.organization.id),
                'plan_type': instance.plan.plan_type,
                'status': instance.status,
                'action': 'subscription_updated'
            }
        )
    
    # Handle status changes
    if instance.status == Subscription.Status.CANCELLED:
        # Organization subscription cancelled - handle gracefully
        logger.warning(f"Organization {instance.organization.name} subscription cancelled")
        
    elif instance.status == Subscription.Status.ACTIVE:
        # Subscription activated - ensure full access
        if instance.organization.status != Organization.Status.ACTIVE:
            instance.organization.status = Organization.Status.ACTIVE
            instance.organization.save(update_fields=['status'])
        
        logger.info(f"Organization {instance.organization.name} subscription activated")
    
    elif instance.status == Subscription.Status.PAST_DUE:
        # Payment failed - handle gracefully (don't immediately cut access)
        logger.warning(f"Organization {instance.organization.name} payment past due")


@receiver(post_save, sender=OrganizationMembership)
def membership_created_handler(sender, instance, created, **kwargs):
    """
    Handle when users join or leave organizations.
    
    Important for user management and access control:
    - Log membership changes for audit trail
    - Send welcome emails to new members
    - Handle user limits enforcement
    """
    if created:
        logger.info(
            f"New member added: {instance.user.email} → {instance.organization.name} ({instance.role})",
            extra={
                'user_id': str(instance.user.id),
                'organization_id': str(instance.organization.id),
                'role': instance.role,
                'action': 'member_added'
            }
        )
        
        # Check user limits for the organization's plan
        current_plan = instance.organization.current_plan
        if current_plan:
            active_members = instance.organization.memberships.filter(is_active=True).count()
            if active_members > current_plan.max_users:
                logger.warning(
                    f"Organization {instance.organization.name} exceeded user limit: "
                    f"{active_members}/{current_plan.max_users}"
                )


@receiver(pre_delete, sender=Organization)
def organization_deleting_handler(sender, instance, **kwargs):
    """
    Handle actions before an organization is deleted.
    
    Critical for data integrity and compliance:
    - Ensure all related data is properly handled
    - Cancel active subscriptions
    - Log deletion for audit trail
    """
    logger.warning(
        f"Organization being deleted: {instance.name} (ID: {instance.id})",
        extra={
            'organization_id': str(instance.id),
            'organization_name': instance.name,
            'owner_email': instance.owner.email,
            'action': 'organization_deleting'
        }
    )
    
    # Cancel active subscriptions
    active_subscriptions = instance.subscriptions.filter(
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING]
    )
    
    for subscription in active_subscriptions:
        subscription.status = Subscription.Status.CANCELLED
        subscription.cancelled_at = timezone.now()
        subscription.save()
        
        logger.info(f"Cancelled subscription {subscription.id} for deleting organization")