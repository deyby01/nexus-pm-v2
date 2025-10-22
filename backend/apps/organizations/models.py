"""
NexusPM Enterprise - Organizations Models

This module implements multi-tenancy and billing for the platform.
Every business entity (workspaces, projects, tasks) belongs to an Organization,
ensuring complete data isolation between different companies using the platform.

Key Architecture Decisions:
- Organization-level multi-tenancy (not database-level)
- Subscription-based billing model with usage limits  
- Flexible membership system (users can belong to multiple orgs)
- Row-level security through organization_id filtering

Business Model:
- Organizations pay for subscriptions
- Plans define limits (users, workspaces, storage, features)
- Freemium model with upgrade paths
- Usage tracking for billing and limits enforcement
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal

User = get_user_model()


class SubscriptionPlan(models.Model):
    """
    Defines the available subscription plans for organizations.
    
    This is our pricing model - the plans that organizations can subscribe to.
    Each plan has different limits and features, following a freemium SaaS model.
    
    Business Logic:
    - Free plan to attract users, paid plans for revenue
    - Clear upgrade path with increasing limits and features
    - Features are stored as JSON for flexibility
    - Stripe integration for payment processing
    """
    
    class PlanType(models.TextChoices):
        """
        Plan types for easy identification and business logic.
        Used throughout the codebase to check user permissions.
        """
        FREE = 'free', 'Free'
        STARTER = 'starter', 'Starter' 
        PROFESSIONAL = 'professional', 'Professional'
        ENTERPRISE = 'enterprise', 'Enterprise'
    
    # Basic plan information
    name = models.CharField(
        max_length=50,
        help_text="Display name for the plan (e.g., 'Professional')"
    )
    plan_type = models.CharField(
        max_length=20, 
        choices=PlanType.choices,
        unique=True,
        help_text="Internal identifier for the plan type"
    )
    description = models.TextField(
        blank=True,
        help_text="Marketing description of the plan"
    )
    
    # Pricing
    price_monthly = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Monthly price in USD"
    )
    price_yearly = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Yearly price in USD (usually discounted)"
    )
    
    # Usage limits (what the organization can do)
    max_workspaces = models.PositiveIntegerField(
        help_text="Maximum number of workspaces allowed"
    )
    max_users = models.PositiveIntegerField(
        help_text="Maximum number of users in the organization"
    )
    max_storage_gb = models.PositiveIntegerField(
        help_text="Maximum storage in GB for file uploads"
    )
    max_projects_per_workspace = models.PositiveIntegerField(
        default=100,
        help_text="Maximum projects per workspace"
    )
    
    # Features (what functionality is available)
    features = models.JSONField(
        default=dict,
        help_text="Available features as JSON (e.g., {'time_tracking': True, 'api_access': False})"
    )
    
    # Stripe integration
    stripe_price_id_monthly = models.CharField(
        max_length=100,
        blank=True,
        help_text="Stripe Price ID for monthly billing"
    )
    stripe_price_id_yearly = models.CharField(
        max_length=100,
        blank=True, 
        help_text="Stripe Price ID for yearly billing"
    )
    
    # Plan status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this plan is available for new subscriptions"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organizations_subscription_plan'
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'
        ordering = ['price_monthly']
    
    def __str__(self):
        return f"{self.name} (${self.price_monthly}/month)"
    
    @property
    def yearly_discount_percentage(self):
        """Calculate the discount percentage for yearly billing"""
        if self.price_monthly == 0:
            return 0
        monthly_yearly = self.price_monthly * 12
        if monthly_yearly == 0:
            return 0
        discount = (monthly_yearly - self.price_yearly) / monthly_yearly * 100
        return round(discount, 1)
    
    def has_feature(self, feature_name):
        """Check if this plan includes a specific feature"""
        return self.features.get(feature_name, False)


class OrganizationMembership(models.Model):
    """
    Represents a User's membership in an Organization.
    
    This is the junction table that connects Users to Organizations,
    allowing users to belong to multiple organizations with different
    roles and permissions in each one.
    
    Key Features:
    - Users can be members of multiple organizations
    - Each membership has a role (owner, admin, member, viewer)
    - Invitation system for adding new members
    - Activity tracking (when joined, last active, etc.)
    
    IMPORTANT: This model is defined BEFORE Organization because
    Organization references it in the through= parameter.
    """
    
    class Role(models.TextChoices):
        """
        Roles define what a user can do within an organization.
        These map to permissions throughout the application.
        """
        OWNER = 'owner', 'Owner'          # Full control, billing access
        ADMIN = 'admin', 'Administrator'   # Full control except billing  
        MEMBER = 'member', 'Member'        # Standard access
        VIEWER = 'viewer', 'Viewer'        # Read-only access
    
    # Relationships
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='organization_memberships',
        help_text="User who is a member of the organization"
    )
    organization = models.ForeignKey(
        'Organization',  # Forward reference since Organization is defined after
        on_delete=models.CASCADE,
        related_name='memberships',
        help_text="Organization the user belongs to"
    )
    
    # Membership details
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        help_text="User's role within this organization"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this membership is currently active"
    )
    
    # Invitation tracking
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_organization_invites',
        help_text="User who invited this member (if applicable)"
    )
    invited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the invitation was sent"
    )
    
    # Activity tracking
    joined_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the user joined the organization"
    )
    last_active_at = models.DateTimeField(
        auto_now=True,
        help_text="When the user was last active in this organization"
    )
    
    class Meta:
        db_table = 'organizations_membership'
        verbose_name = 'Organization Membership'
        verbose_name_plural = 'Organization Memberships'
        unique_together = ['user', 'organization']
        indexes = [
            models.Index(fields=['organization', 'role']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} → {self.organization.name} ({self.role})"
    
    def has_permission(self, permission):
        """
        Check if this membership has a specific permission.
        This will be expanded as we build the permission system.
        """
        role_permissions = {
            self.Role.OWNER: ['all'],
            self.Role.ADMIN: ['manage_users', 'manage_projects', 'view_analytics'],
            self.Role.MEMBER: ['create_projects', 'manage_tasks'],
            self.Role.VIEWER: ['view_projects', 'view_tasks'],
        }
        
        user_permissions = role_permissions.get(self.role, [])
        return 'all' in user_permissions or permission in user_permissions


class Organization(models.Model):
    """
    The root entity for multi-tenancy in NexusPM Enterprise.
    
    Every piece of business data (workspaces, projects, tasks) belongs to 
    exactly one Organization. This ensures complete data isolation between
    different companies using our platform.
    
    Key Responsibilities:
    - Data isolation boundary (Netflix can't see Spotify's data)
    - Billing entity (Organizations pay for subscriptions)
    - Branding and customization container
    - User access control scope
    
    Business Rules:
    - Must have exactly one active subscription
    - Can have multiple users with different roles  
    - Slug must be globally unique (for subdomains)
    - Owner cannot be deleted while owning organizations
    """
    
    class Status(models.TextChoices):
        """Organization lifecycle states"""
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'  # Non-payment, policy violation
        CANCELLED = 'cancelled', 'Cancelled'  # User requested cancellation
    
    # Primary identification
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for this organization"
    )
    
    # Basic information
    name = models.CharField(
        max_length=100,
        help_text="Organization name (e.g., 'Acme Corporation')"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL-friendly identifier (e.g., 'acme-corp' for acme-corp.nexuspm.com)"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the organization"
    )
    
    # Ownership and control
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # Cannot delete user who owns organizations
        related_name='owned_organizations',
        help_text="User who owns and has full control over this organization"
    )
    
    # Status and lifecycle
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Current status of the organization"
    )
    
    # Branding and customization
    logo = models.ImageField(
        upload_to='organization_logos/%Y/%m/',
        null=True,
        blank=True,
        help_text="Organization logo for branding"
    )
    website = models.URLField(
        blank=True,
        help_text="Organization website URL"
    )
    
    # Contact information
    email = models.EmailField(
        blank=True,
        help_text="Primary contact email for the organization"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be in format: '+999999999'"
        )],
        help_text="Primary contact phone number"
    )
    
    # Address (for billing and compliance)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True) 
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=2, blank=True, help_text="ISO country code")
    
    # Settings and preferences
    settings = models.JSONField(
        default=dict,
        help_text="Organization-wide settings and preferences"
    )
    
    # Billing integration
    stripe_customer_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Stripe Customer ID for billing"
    )
    
    # Member relationships - FIXED: specify which ForeignKeys to use
    members = models.ManyToManyField(
        User,
        through='OrganizationMembership',
        through_fields=('organization', 'user'),  # ← FIX: specify the exact fields
        related_name='organizations',
        help_text="Users who are members of this organization"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'organizations_organization'
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['owner']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided"""
        if not self.slug:
            self.slug = slugify(self.name)
            
            # Ensure slug uniqueness
            counter = 1
            original_slug = self.slug
            while Organization.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        super().save(*args, **kwargs)
    
    # Business logic methods
    @property
    def current_subscription(self):
        """Get the current active subscription"""
        return self.subscriptions.filter(
            status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING]
        ).first()
    
    @property
    def current_plan(self):
        """Get the current subscription plan"""
        subscription = self.current_subscription
        return subscription.plan if subscription else None
    
    def is_feature_enabled(self, feature_name):
        """Check if a feature is enabled for this organization"""
        plan = self.current_plan
        return plan.has_feature(feature_name) if plan else False
    
    def get_usage_limits(self):
        """Get current usage limits based on subscription"""
        plan = self.current_plan
        if not plan:
            # Return minimal limits if no plan
            return {
                'max_workspaces': 1,
                'max_users': 1, 
                'max_storage_gb': 0,
                'max_projects_per_workspace': 1
            }
        
        return {
            'max_workspaces': plan.max_workspaces,
            'max_users': plan.max_users,
            'max_storage_gb': plan.max_storage_gb,
            'max_projects_per_workspace': plan.max_projects_per_workspace
        }
    
    def check_usage_limit(self, limit_type):
        """Check if organization is within usage limits"""
        limits = self.get_usage_limits()
        
        if limit_type == 'workspaces':
            current = self.workspaces.filter(deleted_at__isnull=True).count()
            return current < limits['max_workspaces']
        elif limit_type == 'users':
            current = self.memberships.filter(is_active=True).count()
            return current < limits['max_users']
        # Add more limit checks as needed
        
        return True
    
    def soft_delete(self):
        """Soft delete the organization and all related data"""
        self.deleted_at = timezone.now()
        self.status = self.Status.CANCELLED
        self.save(update_fields=['deleted_at', 'status'])


class Subscription(models.Model):
    """
    Represents the billing relationship between an Organization and a Plan.
    
    This is where the money flows - each organization has exactly one active
    subscription that determines what they can do and how much they pay.
    
    Integration with Stripe for payment processing and webhook handling.
    
    Business Rules:
    - Organization can have multiple subscriptions over time (upgrades/downgrades)
    - Only one subscription can be active at a time
    - Trials are limited time offers for new organizations
    - Failed payments lead to suspension, not immediate cancellation
    """
    
    class Status(models.TextChoices):
        """Subscription lifecycle states matching Stripe statuses"""
        ACTIVE = 'active', 'Active'
        TRIALING = 'trialing', 'Trial Period'
        PAST_DUE = 'past_due', 'Payment Failed'
        CANCELLED = 'cancelled', 'Cancelled'
        UNPAID = 'unpaid', 'Unpaid'
    
    class BillingCycle(models.TextChoices):
        """How often the customer is billed"""
        MONTHLY = 'monthly', 'Monthly'
        YEARLY = 'yearly', 'Yearly'
    
    # Relationships
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        help_text="Organization that owns this subscription"
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,  # Can't delete plan with active subscriptions
        related_name='subscriptions',
        help_text="The plan this subscription is for"
    )
    
    # Subscription details
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        help_text="Current status of the subscription"
    )
    billing_cycle = models.CharField(
        max_length=10,
        choices=BillingCycle.choices,
        help_text="How often the customer is billed"
    )
    
    # Stripe integration
    stripe_subscription_id = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        help_text="Stripe Subscription ID for payment processing"
    )
    
    # Billing periods
    current_period_start = models.DateTimeField(
        help_text="Start date of the current billing period"
    )
    current_period_end = models.DateTimeField(
        help_text="End date of the current billing period"
    )
    
    # Trial information
    trial_start = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the trial period started"
    )
    trial_end = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When the trial period ends"
    )
    
    # Cancellation
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the subscription was cancelled"
    )
    cancel_at_period_end = models.BooleanField(
        default=False,
        help_text="Whether to cancel at the end of the current period"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organizations_subscription'
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['stripe_subscription_id']),
            models.Index(fields=['current_period_end']),
        ]
    
    def __str__(self):
        return f"{self.organization.name} - {self.plan.name} ({self.status})"
    
    @property
    def is_active(self):
        """Check if subscription is currently active"""
        return self.status in [self.Status.ACTIVE, self.Status.TRIALING]
    
    @property
    def is_trial(self):
        """Check if subscription is in trial period"""
        if not self.trial_end:
            return False
        return timezone.now() < self.trial_end
    
    @property
    def days_until_renewal(self):
        """Calculate days until next billing cycle"""
        if not self.current_period_end:
            return 0
        delta = self.current_period_end - timezone.now()
        return max(0, delta.days)
    
    def cancel(self, at_period_end=True):
        """Cancel the subscription"""
        if at_period_end:
            self.cancel_at_period_end = True
        else:
            self.status = self.Status.CANCELLED
            self.cancelled_at = timezone.now()
        
        self.save()