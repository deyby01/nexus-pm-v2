"""
NexusPM Enterprise - User Factories (GET_OR_CREATE REMOVED)

Removed django_get_or_create to avoid field validation issues.
"""

import factory
from factory import django, fuzzy, SubFactory, LazyAttribute
from faker import Faker
from django.contrib.auth import get_user_model
from django.utils import timezone
import random

User = get_user_model()
fake = Faker()

# Enterprise job titles for realistic test data
ENTERPRISE_JOB_TITLES = [
    'CEO', 'CTO', 'CFO', 'CPO', 'CMO', 'CHRO', 'CDO',
    'VP of Engineering', 'VP of Product', 'VP of Marketing', 'VP of Sales',
    'Engineering Director', 'Product Director', 'Marketing Director',
    'Engineering Manager', 'Product Manager', 'Project Manager',
    'Senior Software Engineer', 'Software Engineer', 'Junior Developer',
    'Senior Designer', 'UX Designer', 'UI Designer',
    'Data Scientist', 'Data Analyst', 'DevOps Engineer',
]

# Enterprise companies for realistic test data
ENTERPRISE_COMPANIES = [
    'Netflix', 'Google', 'Microsoft', 'Amazon', 'Apple', 'Meta',
    'Salesforce', 'Adobe', 'Slack', 'Zoom', 'Figma', 'Linear',
    'Notion', 'Stripe', 'Spotify', 'Uber', 'Airbnb', 'Tesla',
]


class UserFactory(django.DjangoModelFactory):
    """
    Factory for creating User instances with realistic enterprise data.
    
    Usage Examples:
        # Basic user
        user = UserFactory()
        
        # Admin user
        admin = UserFactory(is_staff=True, is_superuser=True)
    """
    
    class Meta:
        model = User
        # Removed django_get_or_create to avoid field validation issues
    
    # Basic identification - use Sequence to ensure unique emails
    email = factory.Sequence(lambda n: f"user{n}@nexuspm.test")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    
    # Authentication
    password = factory.PostGenerationMethodCall('set_password', 'nexus2024!')
    is_active = True
    is_staff = False
    is_superuser = False
    is_email_verified = True
    
    # Only add fields that exist in the User model
    # We'll skip optional fields that may not exist


class AdminUserFactory(UserFactory):
    """Factory for creating admin users with staff privileges."""
    
    is_staff = True
    is_superuser = True
    email = factory.Sequence(lambda n: f"admin{n}@nexuspm.test")


class CEOUserFactory(UserFactory):
    """Factory for creating C-level executive users."""
    
    is_staff = True  # C-level typically has admin access
    email = factory.Sequence(lambda n: f"ceo{n}@nexuspm.test")


class DeveloperUserFactory(UserFactory):
    """Factory for creating developer users."""
    
    email = factory.Sequence(lambda n: f"dev{n}@nexuspm.test")


class DesignerUserFactory(UserFactory):
    """Factory for creating designer users."""
    
    email = factory.Sequence(lambda n: f"designer{n}@nexuspm.test")


class ManagerUserFactory(UserFactory):
    """Factory for creating management-level users."""
    
    email = factory.Sequence(lambda n: f"manager{n}@nexuspm.test")


class InactiveUserFactory(UserFactory):
    """Factory for creating inactive users."""
    
    is_active = False
    last_login = None
    email = factory.Sequence(lambda n: f"inactive{n}@nexuspm.test")


class UnverifiedUserFactory(UserFactory):
    """Factory for creating unverified users."""
    
    is_email_verified = False
    last_login = None
    date_joined = factory.LazyFunction(timezone.now)
    email = factory.Sequence(lambda n: f"unverified{n}@nexuspm.test")


def create_netflix_team():
    """Create the Netflix team that matches our simulation data."""
    
    # Create specific Netflix users matching our shell simulation
    netflix_users = [
        UserFactory(
            email="reed.hastings@netflix.com",
            first_name="Reed",
            last_name="Hastings", 
            is_staff=True
        ),
        UserFactory(
            email="greg.peters@netflix.com",
            first_name="Greg", 
            last_name="Peters",
            is_staff=True
        ),
        UserFactory(
            email="sarah.connor@netflix.com",
            first_name="Sarah",
            last_name="Connor"
        ),
        UserFactory(
            email="david.wells@netflix.com",
            first_name="David",
            last_name="Wells"
        ),
        UserFactory(
            email="john.doe@netflix.com",
            first_name="John",
            last_name="Doe"
        ),
        UserFactory(
            email="jane.smith@netflix.com", 
            first_name="Jane",
            last_name="Smith"
        ),
        UserFactory(
            email="mike.johnson@netflix.com",
            first_name="Mike", 
            last_name="Johnson"
        ),
        UserFactory(
            email="lisa.wang@netflix.com",
            first_name="Lisa",
            last_name="Wang"
        ),
        UserFactory(
            email="carlos.mendez@netflix.com",
            first_name="Carlos",
            last_name="Mendez"
        ),
        UserFactory(
            email="anna.taylor@netflix.com",
            first_name="Anna",
            last_name="Taylor"
        ),
    ]
    
    return netflix_users


def create_enterprise_team(size=10, company_name=None):
    """Create a realistic enterprise team."""
    
    team = {
        'ceo': CEOUserFactory(),
        'managers': ManagerUserFactory.create_batch(max(1, size // 5)),
        'developers': DeveloperUserFactory.create_batch(max(1, size // 2)),
        'designers': DesignerUserFactory.create_batch(max(1, size // 10)),
        'others': UserFactory.create_batch(max(0, size - (1 + size//5 + size//2 + size//10)))
    }
    
    return team