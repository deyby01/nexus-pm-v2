"""
NexusPM Enterprise - Organizations Admin Configuration

This module configures the Django admin interface for managing organizations,
subscriptions, and memberships. Critical for operations team to manage
customers, billing issues, and support requests.

Enterprise Features:
- Advanced filtering and search for customer support
- Bulk actions for operational efficiency  
- Financial data visibility for billing management
- Member management for user access issues
- Audit trail visibility for compliance
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.db.models import Count, Q
import logging

from .models import (
    Organization, 
    SubscriptionPlan, 
    Subscription, 
    OrganizationMembership
)

logger = logging.getLogger('nexuspm.organizations')


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    """
    Admin for managing subscription plans.
    
    Used by business team to:
    - Create new pricing plans
    - Update existing plan limits and features
    - Manage Stripe integration
    - Analyze plan performance
    """
    
    list_display = [
        'name',
        'plan_type', 
        'price_monthly_display',
        'price_yearly_display',
        'yearly_discount',
        'max_users',
        'max_workspaces',
        'max_storage_gb',
        'active_subscriptions_count',
        'is_active'
    ]
    
    list_filter = [
        'plan_type',
        'is_active',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'description',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'active_subscriptions_count',
        'yearly_discount'
    ]
    
    fieldsets = (
        ('📋 Plan Information', {
            'fields': ('name', 'plan_type', 'description', 'is_active')
        }),
        ('💰 Pricing', {
            'fields': ('price_monthly', 'price_yearly', 'yearly_discount'),
        }),
        ('📊 Limits & Features', {
            'fields': (
                'max_users', 
                'max_workspaces', 
                'max_storage_gb',
                'max_projects_per_workspace',
                'features'
            ),
        }),
        ('🔗 Stripe Integration', {
            'fields': ('stripe_price_id_monthly', 'stripe_price_id_yearly'),
            'classes': ['collapse'],
        }),
        ('📅 Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ['collapse'],
        }),
    )
    
    def price_monthly_display(self, obj):
        """Format monthly price for display"""
        if obj.price_monthly == 0:
            return "FREE"
        return f"${obj.price_monthly}"
    price_monthly_display.short_description = "Monthly Price"
    
    def price_yearly_display(self, obj):
        """Format yearly price for display"""
        if obj.price_yearly == 0:
            return "FREE"
        return f"${obj.price_yearly}"
    price_yearly_display.short_description = "Yearly Price"
    
    def yearly_discount(self, obj):
        """Show yearly discount percentage"""
        discount = obj.yearly_discount_percentage
        if discount > 0:
            return f"{discount}% off"
        return "No discount"
    yearly_discount.short_description = "Yearly Discount"
    
    def active_subscriptions_count(self, obj):
        """Count active subscriptions for this plan"""
        count = obj.subscriptions.filter(
            status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING]
        ).count()
        return count
    active_subscriptions_count.short_description = "Active Subscriptions"


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """
    Main admin interface for managing organizations.
    
    Critical for customer support and operations:
    - View customer information and subscription status
    - Handle billing issues and plan changes
    - Manage user access and roles
    - Monitor organization health and usage
    """
    
    list_display = [
        'logo_preview',
        'name',
        'slug',
        'owner_email',
        'current_plan_display',
        'subscription_status',
        'member_count',
        'status',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'slug', 
        'email',
        'owner__email',
        'owner__first_name',
        'owner__last_name',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'current_plan_display',
        'subscription_status',
        'member_count',
    ]
    
    fieldsets = (
        ('🏢 Organization Info', {
            'fields': ('name', 'slug', 'description', 'status', 'owner')
        }),
        ('🎨 Branding', {
            'fields': ('logo', 'website'),
            'classes': ['collapse'],
        }),
        ('📞 Contact Info', {
            'fields': ('email', 'phone'),
            'classes': ['collapse'],
        }),
        ('📍 Address', {
            'fields': (
                'address_line1', 'address_line2', 
                'city', 'state', 'postal_code', 'country'
            ),
            'classes': ['collapse'],
        }),
        ('💰 Billing & Subscription', {
            'fields': (
                'current_plan_display',
                'subscription_status', 
                'stripe_customer_id',
            ),
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
    
    def get_queryset(self, request):
        """Optimize queries with select_related and prefetch_related"""
        return super().get_queryset(request).select_related('owner')
    
    def logo_preview(self, obj):
        """Show organization logo in admin list"""
        if obj.logo:
            return format_html(
                '<img src="{}" width="30" height="30" style="border-radius: 4px;" />',
                obj.logo.url
            )
        return format_html(
            '<div style="width:30px;height:30px;background:#007cba;color:white;border-radius:4px;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:10px;">{}</div>',
            obj.name[:2].upper()
        )
    logo_preview.short_description = '🏢'
    
    def owner_email(self, obj):
        """Display owner email"""
        return obj.owner.email
    owner_email.short_description = "Owner"
    
    def current_plan_display(self, obj):
        """Show current subscription plan with status"""
        subscription = obj.current_subscription
        if not subscription:
            return format_html('<span style="color: red;">No Active Plan</span>')
        
        color = {
            'active': 'green',
            'trialing': 'orange', 
            'past_due': 'red',
            'cancelled': 'gray'
        }.get(subscription.status, 'black')
        
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            subscription.plan.name
        )
    current_plan_display.short_description = "Current Plan"
    
    def subscription_status(self, obj):
        """Show subscription status with days until renewal"""
        subscription = obj.current_subscription
        if not subscription:
            return "No subscription"
        
        status = subscription.status
        if subscription.is_active:
            days_left = subscription.days_until_renewal
            return f"{status.title()} ({days_left} days left)"
        return status.title()
    subscription_status.short_description = "Subscription Status"
    
    def member_count(self, obj):
        """Show member count"""
        count = obj.memberships.filter(is_active=True).count()
        return f"{count} members"
    member_count.short_description = "Members"


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """
    Admin interface for managing subscriptions and billing.
    """
    
    list_display = [
        'organization_name',
        'plan_name',
        'status',
        'billing_cycle',
        'current_period_end',
        'is_trial_display',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'billing_cycle',
        'plan__plan_type',
        'created_at',
    ]
    
    search_fields = [
        'organization__name',
        'organization__slug',
    ]
    
    def organization_name(self, obj):
        return obj.organization.name
    organization_name.short_description = "Organization"
    
    def plan_name(self, obj):
        return f"{obj.plan.name} (${obj.plan.price_monthly}/mo)"
    plan_name.short_description = "Plan"
    
    def is_trial_display(self, obj):
        if obj.is_trial:
            return format_html('<span style="color: orange;">Trial</span>')
        return "Active"
    is_trial_display.short_description = "Trial Status"


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    """
    Admin interface for managing organization memberships.
    """
    
    list_display = [
        'user_email',
        'organization_name', 
        'role',
        'is_active',
        'joined_at',
    ]
    
    list_filter = [
        'role',
        'is_active',
        'joined_at',
    ]
    
    search_fields = [
        'user__email',
        'organization__name',
    ]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "User"
    
    def organization_name(self, obj):
        return obj.organization.name
    organization_name.short_description = "Organization"