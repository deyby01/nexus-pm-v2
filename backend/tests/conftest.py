"""
NexusPM Enterprise - Test Configuration and Shared Fixtures (FINAL FIX)

Fixed database access for django_db_setup fixture.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.core.management import call_command
from faker import Faker
import factory
from typing import Dict, List, Any

# Import existing factories only
from tests.factories.user_factories import UserFactory
from tests.factories.organization_factories import (
    OrganizationFactory, 
    SubscriptionPlanFactory,
    SubscriptionFactory
)
from tests.factories.workspace_factories import WorkspaceFactory

User = get_user_model()
fake = Faker()

# ============================================================================
# DATABASE FIXTURES - FIXED
# ============================================================================

@pytest.fixture(scope='session')
@pytest.mark.django_db
def django_db_setup(django_db_setup):
    """
    Configure the test database for the entire session.
    Creates necessary tables and initial data.
    """
    # The database is already set up by pytest-django
    # We just need to ensure migrations are applied
    pass


@pytest.fixture
def db_clean():
    """
    Ensure database is clean between tests.
    Use this for tests that need complete isolation.
    """
    pass  # pytest-django handles this automatically


# ============================================================================
# USER FIXTURES
# ============================================================================

@pytest.fixture
def user():
    """Create a basic test user."""
    return UserFactory()


@pytest.fixture
def admin_user():
    """Create an admin user for testing administrative functions."""
    return UserFactory(
        is_staff=True,
        is_superuser=True,
        email="admin@nexuspm.test"
    )


@pytest.fixture
def multiple_users():
    """Create multiple users for testing team features."""
    return UserFactory.create_batch(5)


@pytest.fixture
def user_with_profile():
    """Create a user with complete profile information."""
    return UserFactory(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        job_title=fake.job(),
        company=fake.company(),
        bio=fake.text(max_nb_chars=200),
        timezone='America/New_York',
        language='en'
    )


# ============================================================================
# ORGANIZATION FIXTURES  
# ============================================================================

@pytest.fixture
def subscription_plans():
    """Create all standard subscription plans."""
    plans = {}
    
    # Free plan
    plans['free'] = SubscriptionPlanFactory(
        plan_type="free"
    )
    
    # Starter plan
    plans['starter'] = SubscriptionPlanFactory(
        plan_type="starter"
    )
    
    # Professional plan
    plans['professional'] = SubscriptionPlanFactory(
        plan_type="professional"
    )
    
    # Enterprise plan
    plans['enterprise'] = SubscriptionPlanFactory(
        plan_type="enterprise"
    )
    
    return plans


@pytest.fixture
def organization(user, subscription_plans):
    """Create a basic organization with free plan."""
    org = OrganizationFactory(owner=user)
    
    # Create subscription
    SubscriptionFactory(
        organization=org,
        plan=subscription_plans['free']
    )
    
    return org


@pytest.fixture
def enterprise_organization(user, subscription_plans):
    """Create an enterprise organization with full features."""
    org = OrganizationFactory(
        owner=user,
        name="Netflix Inc",
        email="business@netflix.com"
    )
    
    # Create enterprise subscription
    SubscriptionFactory(
        organization=org,
        plan=subscription_plans['enterprise'],
        status='active'
    )
    
    return org


# ============================================================================
# WORKSPACE FIXTURES
# ============================================================================

@pytest.fixture
def workspace(organization, user):
    """Create a basic workspace."""
    return WorkspaceFactory(
        organization=organization,
        created_by=user
    )


@pytest.fixture
def multiple_workspaces(enterprise_organization, user):
    """Create multiple workspaces for testing enterprise features."""
    workspaces = []
    
    workspace_configs = [
        {'name': 'Engineering', 'workspace_type': 'development'},
        {'name': 'Marketing', 'workspace_type': 'marketing'},
        {'name': 'Design', 'workspace_type': 'design'},
        {'name': 'Operations', 'workspace_type': 'operations'},
    ]
    
    for config in workspace_configs:
        workspace = WorkspaceFactory(
            organization=enterprise_organization,
            created_by=user,
            **config
        )
        workspaces.append(workspace)
    
    return workspaces


# ============================================================================
# AUTHENTICATION FIXTURES
# ============================================================================

@pytest.fixture
def authenticated_client(client, user):
    """Create an authenticated test client."""
    client.force_login(user)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Create an authenticated admin test client."""
    client.force_login(admin_user)
    return client


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def mock_time():
    """Mock timezone.now() for consistent time-based testing."""
    from django.utils import timezone
    from unittest.mock import patch
    from datetime import datetime
    
    fixed_time = datetime(2025, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
    
    with patch('django.utils.timezone.now', return_value=fixed_time):
        yield fixed_time


@pytest.fixture
def sample_file():
    """Create a sample file for file upload testing."""
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    return SimpleUploadedFile(
        "test_file.txt",
        b"This is a test file content for NexusPM Enterprise testing.",
        content_type="text/plain"
    )


# ============================================================================
# PERFORMANCE FIXTURES
# ============================================================================

@pytest.fixture
def performance_monitor():
    """Monitor test performance and database queries."""
    from django.test.utils import override_settings
    from django.db import connection
    
    with override_settings(DEBUG=True):
        initial_queries = len(connection.queries)
        yield
        final_queries = len(connection.queries)
        query_count = final_queries - initial_queries
        
        # Log performance metrics
        if query_count > 10:
            print(f"⚠️  High query count: {query_count} queries")


# ============================================================================
# MARKERS AND CONFIGURATION
# ============================================================================

# Configure pytest markers for test categorization
pytest_plugins = [
    'pytest_django',
    'pytest_factoryboy',
    'pytest_mock'
]

# Auto-use fixtures for specific test types
@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Enable database access for all tests automatically.
    This simplifies test writing while maintaining isolation.
    """
    pass


# Test data cleanup
@pytest.fixture(autouse=True, scope='function')
def cleanup_test_data():
    """Ensure test data is cleaned up after each test."""
    yield
    # Cleanup happens automatically with Django's test database handling