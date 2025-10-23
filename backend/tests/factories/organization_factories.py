"""
NexusPM Enterprise - Organization Factories (FIELD LENGTH FIXED)

Fixed field length issues for database constraints.
"""

import factory
from factory import django, fuzzy, SubFactory, LazyAttribute, RelatedFactory
from faker import Faker
from django.utils import timezone
from decimal import Decimal
import random

from apps.organizations.models import (
    Organization, 
    SubscriptionPlan, 
    Subscription,
    OrganizationMembership
)
from .user_factories import UserFactory

fake = Faker()

# Shorter company names to fit database constraints
COMPANY_NAMES = [
    'Apple', 'Microsoft', 'Google', 'Amazon', 'Meta', 'Tesla', 'Netflix',
    'Samsung', 'Oracle', 'IBM', 'Intel', 'Cisco', 'Adobe', 'Zoom',
    'Slack', 'Linear', 'Figma', 'Stripe', 'Spotify', 'Uber'
]

# Industry categories
INDUSTRIES = [
    'Technology', 'Finance', 'Healthcare', 'Retail', 'Manufacturing',
    'Energy', 'Telecom', 'Media', 'Automotive', 'Aerospace'
]

# Company sizes
COMPANY_SIZES = [
    '1-10', '11-50', '51-200', '201-500', '501-1000', 
    '1001-5000', '5001-10000', '10000+'
]


class SubscriptionPlanFactory(django.DjangoModelFactory):
    """Factory for creating subscription plans."""
    
    class Meta:
        model = SubscriptionPlan
    
    name = factory.LazyAttribute(lambda obj: obj.plan_type.title())
    plan_type = factory.fuzzy.FuzzyChoice(['free', 'starter', 'professional', 'enterprise'])
    
    # Dynamic pricing based on plan type
    price_monthly = factory.LazyAttribute(lambda obj: {
        'free': 0, 'starter': 20, 'professional': 50, 'enterprise': 150
    }.get(obj.plan_type, 20))
    
    price_yearly = factory.LazyAttribute(
        lambda obj: obj.price_monthly * 10 if obj.price_monthly > 0 else 0
    )
    
    # Dynamic limits based on plan type
    max_workspaces = factory.LazyAttribute(lambda obj: {
        'free': 2, 'starter': 5, 'professional': 15, 'enterprise': 999
    }.get(obj.plan_type, 5))
    
    max_users = factory.LazyAttribute(lambda obj: {
        'free': 5, 'starter': 15, 'professional': 50, 'enterprise': 999
    }.get(obj.plan_type, 15))
    
    max_storage_gb = factory.LazyAttribute(lambda obj: {
        'free': 0, 'starter': 1, 'professional': 10, 'enterprise': 100
    }.get(obj.plan_type, 1))
    
    # Simple features
    features = factory.LazyAttribute(lambda obj: {
        'free': {'basic': True},
        'starter': {'basic': True, 'time_tracking': True},
        'professional': {'basic': True, 'analytics': True},
        'enterprise': {'basic': True, 'api_access': True}
    }.get(obj.plan_type, {}))


class OrganizationFactory(django.DjangoModelFactory):
    """Factory for creating organizations with realistic enterprise data."""
    
    class Meta:
        model = Organization
    
    # Basic information - shorter names to fit constraints
    name = factory.fuzzy.FuzzyChoice(COMPANY_NAMES)
    slug = factory.LazyAttribute(
        lambda obj: obj.name.lower().replace(' ', '-')[:20]  # Ensure max 20 chars
    )
    description = factory.LazyAttribute(
        lambda obj: f"{obj.name} - Enterprise software company"
    )
    
    # Ownership
    owner = SubFactory(UserFactory)
    
    # Contact information
    email = factory.LazyAttribute(
        lambda obj: f"biz@{obj.slug}.com"  # Short email format
    )
    phone = factory.Sequence(lambda n: f"+1-555-{n:04d}")  # Sequential short phone
    website = factory.LazyAttribute(
        lambda obj: f"https://{obj.slug}.com"
    )
    
    # Address information - shorter values
    address_line1 = factory.Faker('street_address')
    city = factory.Faker('city')
    state = factory.Faker('state_abbr')  # 2-char state codes
    postal_code = factory.Faker('zipcode')  # US zip codes
    country = factory.fuzzy.FuzzyChoice(['US', 'CA', 'GB', 'DE', 'FR'])
    
    # Organization settings - simplified
    settings = factory.LazyAttribute(lambda obj: {
        'industry': random.choice(INDUSTRIES),
        'company_size': random.choice(COMPANY_SIZES),
        'onboarding_completed': True,
        'billing_email': obj.email,
        'currency': 'USD'
    })
    
    # Status
    status = Organization.Status.ACTIVE


class SubscriptionFactory(django.DjangoModelFactory):
    """Factory for creating subscriptions with realistic billing data."""
    
    class Meta:
        model = Subscription
    
    organization = SubFactory(OrganizationFactory)
    plan = SubFactory(SubscriptionPlanFactory)
    
    # Use random.choices instead of fake.choices
    status = factory.LazyAttribute(
        lambda obj: random.choices(
            population=['active', 'trialing', 'past_due'],
            weights=[70, 20, 10],
            k=1
        )[0]
    )
    
    billing_cycle = factory.LazyAttribute(
        lambda obj: random.choices(
            population=['monthly', 'yearly'], 
            weights=[30, 70],
            k=1
        )[0]
    )
    
    # Dates with timezone
    trial_end = factory.LazyFunction(
        lambda: fake.future_datetime(end_date='+30d', tzinfo=timezone.utc)
    )
    current_period_start = factory.LazyFunction(
        lambda: fake.past_datetime(start_date='-30d', tzinfo=timezone.utc)
    )
    current_period_end = factory.LazyFunction(
        lambda: fake.future_datetime(end_date='+30d', tzinfo=timezone.utc)
    )
    
    # Stripe integration (shorter IDs)
    stripe_customer_id = factory.LazyAttribute(
        lambda obj: f"cus_{fake.lexify('????????', letters='abcdef0123456789')}"  # 12 chars total
    )
    stripe_subscription_id = factory.LazyAttribute(
        lambda obj: f"sub_{fake.lexify('????????', letters='abcdef0123456789')}"  # 12 chars total
    )


class OrganizationMembershipFactory(django.DjangoModelFactory):
    """Factory for creating organization memberships."""
    
    class Meta:
        model = OrganizationMembership
    
    user = SubFactory(UserFactory)
    organization = SubFactory(OrganizationFactory)
    
    # Use random.choices
    role = factory.LazyAttribute(
        lambda obj: random.choices(
            population=['member', 'admin', 'owner'],
            weights=[70, 25, 5],
            k=1
        )[0]
    )
    
    is_active = True
    
    # Invitation data
    invited_by = SubFactory(UserFactory)
    invited_at = factory.LazyFunction(
        lambda: fake.past_datetime(start_date='-90d', tzinfo=timezone.utc)
    )


# Utility functions
def create_complete_organization(plan_type='professional', team_size=15):
    """Create a complete organization with subscription, plan, and team members."""
    # Create subscription plan
    plan = SubscriptionPlanFactory(plan_type=plan_type)
    
    # Create organization with owner
    owner = UserFactory(is_staff=True)
    org = OrganizationFactory(owner=owner)
    
    # Create subscription
    subscription = SubscriptionFactory(
        organization=org,
        plan=plan,
        status='active'
    )
    
    # Create team members
    admins = UserFactory.create_batch(max(1, team_size // 10))
    members = UserFactory.create_batch(team_size - len(admins))
    
    # Create organization memberships
    org_memberships = []
    
    for admin in admins:
        membership = OrganizationMembershipFactory(
            user=admin,
            organization=org,
            role='admin',
            invited_by=owner
        )
        org_memberships.append(membership)
    
    for member in members:
        membership = OrganizationMembershipFactory(
            user=member,
            organization=org,
            role='member',
            invited_by=random.choice([owner] + admins)
        )
        org_memberships.append(membership)
    
    return {
        'organization': org,
        'owner': owner,
        'plan': plan,
        'subscription': subscription,
        'admins': admins,
        'members': members,
        'memberships': org_memberships
    }


def create_netflix_organization():
    """Create Netflix organization matching our simulation data."""
    from .user_factories import create_netflix_team
    
    # Create Netflix team
    netflix_users = create_netflix_team()
    reed_hastings = next(u for u in netflix_users if u.email == "reed.hastings@netflix.com")
    
    # Create enterprise plan
    enterprise_plan = SubscriptionPlanFactory(plan_type='enterprise')
    
    # Create Netflix organization - shorter values
    netflix_org = OrganizationFactory(
        name="Netflix",  # ← SHORTER NAME
        slug="netflix",  # ← SHORTER SLUG
        owner=reed_hastings,
        email="biz@netflix.com",  # ← SHORTER EMAIL
        phone="+1-555-0100",      # ← SHORTER PHONE
        website="https://netflix.com",
        address_line1="100 Winchester",  # ← SHORTER ADDRESS
        city="Los Gatos",
        state="CA", 
        postal_code="95032",
        country="US",
        settings={
            'industry': 'Media',  # ← SHORTER
            'company_size': '10000+',
            'onboarding_completed': True
        }
    )
    
    # Create subscription
    subscription = SubscriptionFactory(
        organization=netflix_org,
        plan=enterprise_plan,
        status='active',
        billing_cycle='yearly'
    )
    
    # Create organization memberships
    org_memberships = []
    role_mapping = {
        "reed.hastings@netflix.com": "owner",
        "greg.peters@netflix.com": "admin",
        "sarah.connor@netflix.com": "admin", 
        "david.wells@netflix.com": "admin",
    }
    
    for user in netflix_users:
        role = role_mapping.get(user.email, 'member')
        membership = OrganizationMembershipFactory(
            user=user,
            organization=netflix_org,
            role=role,
            invited_by=reed_hastings
        )
        org_memberships.append(membership)
    
    return {
        'organization': netflix_org,
        'users': netflix_users,
        'owner': reed_hastings,
        'plan': enterprise_plan,
        'subscription': subscription,
        'memberships': org_memberships
    }