"""
NexusPM Enterprise - Factory Tests (FIXED DATABASE ACCESS)

Tests to verify that our Factory Boy factories work correctly
and generate realistic data as expected.

Fixed database access for pytest-django compatibility.
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

# Mark all test classes for database access
pytestmark = pytest.mark.django_db

from tests.factories.user_factories import (
    UserFactory, 
    AdminUserFactory, 
    CEOUserFactory,
    DeveloperUserFactory,
    create_netflix_team
)
from tests.factories.organization_factories import (
    OrganizationFactory,
    SubscriptionPlanFactory,
    SubscriptionFactory,
    create_complete_organization,
    create_netflix_organization
)
from tests.factories.workspace_factories import (
    WorkspaceFactory,
    WorkspaceMembershipFactory,
    create_workspace_with_team,
    create_netflix_workspaces
)

User = get_user_model()


@pytest.mark.django_db
class TestUserFactories:
    """Test User factory functions work correctly."""
    
    def test_basic_user_factory(self):
        """Test basic UserFactory creates valid users."""
        user = UserFactory()
        
        # Basic assertions
        assert user.email is not None
        assert '@' in user.email
        assert user.first_name is not None
        assert user.last_name is not None
        assert user.is_active is True
        assert user.is_email_verified is True
        
        # Professional info
        assert user.job_title is not None
        assert user.company is not None
        
        print(f"✅ Created user: {user.email} - {user.get_full_name()} ({user.job_title})")
    
    def test_admin_user_factory(self):
        """Test AdminUserFactory creates admin users."""
        admin = AdminUserFactory()
        
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.job_title in ['CTO', 'VP of Engineering', 'Engineering Director', 'System Administrator']
        
        print(f"✅ Created admin: {admin.email} - {admin.job_title}")
    
    def test_ceo_user_factory(self):
        """Test CEOUserFactory creates C-level users."""
        ceo = CEOUserFactory()
        
        assert ceo.job_title in ['CEO', 'CTO', 'CFO', 'CPO', 'CMO']
        assert ceo.is_staff is True
        
        print(f"✅ Created C-level: {ceo.email} - {ceo.job_title}")
    
    def test_developer_user_factory(self):
        """Test DeveloperUserFactory creates engineering users.""" 
        dev = DeveloperUserFactory()
        
        engineering_titles = [
            'Senior Software Engineer', 'Software Engineer', 'Junior Developer',
            'Frontend Developer', 'Backend Developer', 'Full Stack Developer',
            'DevOps Engineer', 'Mobile Developer', 'QA Engineer'
        ]
        
        assert dev.job_title in engineering_titles
        
        print(f"✅ Created developer: {dev.email} - {dev.job_title}")
    
    def test_multiple_users(self):
        """Test batch user creation."""
        users = UserFactory.create_batch(5)
        
        assert len(users) == 5
        
        # All users should be unique
        emails = [user.email for user in users]
        assert len(set(emails)) == 5  # All unique
        
        print(f"✅ Created {len(users)} unique users")
    
    def test_netflix_team_creation(self):
        """Test Netflix team matches our simulation."""
        netflix_team = create_netflix_team()
        
        expected_emails = [
            "reed.hastings@netflix.com",
            "greg.peters@netflix.com", 
            "sarah.connor@netflix.com",
            "david.wells@netflix.com",
            "john.doe@netflix.com",
            "jane.smith@netflix.com",
            "mike.johnson@netflix.com",
            "lisa.wang@netflix.com",
            "carlos.mendez@netflix.com",
            "anna.taylor@netflix.com"
        ]
        
        created_emails = [user.email for user in netflix_team]
        
        assert len(netflix_team) == 10
        assert all(email in created_emails for email in expected_emails)
        
        # Find Reed Hastings
        reed = next(u for u in netflix_team if u.email == "reed.hastings@netflix.com")
        assert reed.job_title == "CEO & Co-founder"
        assert reed.company == "Netflix"
        
        print(f"✅ Created Netflix team: {len(netflix_team)} members")


@pytest.mark.django_db
class TestOrganizationFactories:
    """Test Organization factory functions work correctly."""
    
    def test_basic_organization_factory(self):
        """Test basic OrganizationFactory creates valid organizations."""
        org = OrganizationFactory()
        
        assert org.name is not None
        assert org.slug is not None
        assert org.owner is not None
        assert org.email is not None
        assert '@' in org.email
        assert org.status == org.Status.ACTIVE
        
        print(f"✅ Created org: {org.name} - {org.slug}")
    
    def test_subscription_plan_factory(self):
        """Test SubscriptionPlanFactory creates valid plans."""
        # Test all plan types
        for plan_type in ['free', 'starter', 'professional', 'enterprise']:
            plan = SubscriptionPlanFactory(plan_type=plan_type)
            
            assert plan.plan_type == plan_type
            assert plan.name == plan_type.title()
            assert plan.max_workspaces > 0
            assert plan.max_users > 0
            
            if plan_type == 'free':
                assert plan.price_monthly == 0
            else:
                assert plan.price_monthly > 0
            
            print(f"✅ Created {plan_type} plan: ${plan.price_monthly}/month")
    
    def test_subscription_factory(self):
        """Test SubscriptionFactory creates valid subscriptions."""
        subscription = SubscriptionFactory()
        
        assert subscription.organization is not None
        assert subscription.plan is not None
        assert subscription.status in ['active', 'trialing', 'past_due']
        assert subscription.stripe_customer_id is not None
        assert subscription.stripe_customer_id.startswith('cus_')
        
        print(f"✅ Created subscription: {subscription.plan.name} for {subscription.organization.name}")
    
    def test_complete_organization_setup(self):
        """Test create_complete_organization utility."""
        setup = create_complete_organization(plan_type='professional', team_size=10)
        
        assert setup['organization'] is not None
        assert setup['owner'] is not None
        assert setup['plan'].plan_type == 'professional'
        assert setup['subscription'].status == 'active'
        assert len(setup['admins']) >= 1
        assert len(setup['members']) >= 1
        assert len(setup['memberships']) == 10  # team_size
        
        print(f"✅ Created complete org: {setup['organization'].name} with {len(setup['memberships'])} members")
    
    def test_netflix_organization_creation(self):
        """Test Netflix organization matches our simulation."""
        netflix_setup = create_netflix_organization()
        
        netflix_org = netflix_setup['organization']
        
        assert netflix_org.name == "Netflix Inc"
        assert netflix_org.slug == "netflix-inc"
        assert netflix_org.email == "business@netflix.com"
        assert len(netflix_setup['users']) == 10
        assert netflix_setup['plan'].plan_type == 'enterprise'
        assert netflix_setup['subscription'].status == 'active'
        
        # Check Reed Hastings is owner
        owner_membership = next(
            m for m in netflix_setup['memberships'] 
            if m.role == 'owner'
        )
        assert owner_membership.user.email == "reed.hastings@netflix.com"
        
        print(f"✅ Created Netflix organization with {len(netflix_setup['memberships'])} team members")


@pytest.mark.django_db
class TestWorkspaceFactories:
    """Test Workspace factory functions work correctly."""
    
    def test_basic_workspace_factory(self):
        """Test basic WorkspaceFactory creates valid workspaces."""
        workspace = WorkspaceFactory()
        
        assert workspace.name is not None
        assert workspace.slug is not None
        assert workspace.organization is not None
        assert workspace.created_by is not None
        assert workspace.workspace_type is not None
        assert workspace.color is not None
        assert workspace.status == workspace.Status.ACTIVE
        
        print(f"✅ Created workspace: {workspace.name} ({workspace.workspace_type})")
    
    def test_workspace_membership_factory(self):
        """Test WorkspaceMembershipFactory creates valid memberships."""
        membership = WorkspaceMembershipFactory()
        
        assert membership.user is not None
        assert membership.workspace is not None
        assert membership.role is not None
        assert membership.is_active is True
        
        print(f"✅ Created membership: {membership.user.email} → {membership.workspace.name} ({membership.role})")
    
    def test_workspace_with_team(self):
        """Test create_workspace_with_team utility."""
        setup = create_workspace_with_team(
            workspace_type='development', 
            team_size=8
        )
        
        workspace = setup['workspace']
        team_members = setup['team_members']
        
        assert workspace.workspace_type == 'development'
        assert workspace.member_count == 8
        assert 'creator' in team_members
        assert setup['total_members'] == 8
        
        print(f"✅ Created dev workspace: {workspace.name} with {setup['total_members']} team members")
    
    def test_netflix_workspaces_creation(self):
        """Test Netflix workspaces match our simulation."""
        # First create Netflix organization and users
        netflix_setup = create_netflix_organization()
        netflix_org = netflix_setup['organization']
        netflix_users = netflix_setup['users']
        
        # Create Netflix workspaces
        workspaces = create_netflix_workspaces(netflix_org, netflix_users)
        
        expected_workspaces = [
            'content', 'engineering', 'data_science', 'marketing', 'executive'
        ]
        
        assert len(workspaces) == 5
        assert all(ws_name in workspaces for ws_name in expected_workspaces)
        
        # Check specific workspace properties
        engineering = workspaces['engineering']
        assert engineering.name == 'Engineering Platform'
        assert engineering.workspace_type == 'development'
        assert engineering.is_private is True
        assert engineering.color == '#3B82F6'
        
        print(f"✅ Created {len(workspaces)} Netflix workspaces")


@pytest.mark.django_db
class TestFactoryIntegration:
    """Test factories work together in complex scenarios."""
    
    def test_complete_netflix_simulation(self):
        """Test complete Netflix setup matches our shell simulation."""
        # Create complete Netflix setup
        netflix_setup = create_netflix_organization()
        netflix_org = netflix_setup['organization']
        netflix_users = netflix_setup['users']
        
        # Create workspaces
        workspaces = create_netflix_workspaces(netflix_org, netflix_users)
        
        # Verify complete integration
        assert netflix_org.name == "Netflix Inc"
        assert len(netflix_users) == 10
        assert len(workspaces) == 5
        
        # Verify relationships
        for workspace in workspaces.values():
            assert workspace.organization == netflix_org
        
        # Verify owner
        reed = next(u for u in netflix_users if u.email == "reed.hastings@netflix.com")
        assert netflix_org.owner == reed
        
        print(f"✅ Complete Netflix simulation: {netflix_org.name} with {len(netflix_users)} users and {len(workspaces)} workspaces")
    
    def test_multi_tenant_isolation(self):
        """Test that different organizations are properly isolated."""
        # Create two separate organizations
        setup1 = create_complete_organization(plan_type='starter', team_size=5)
        setup2 = create_complete_organization(plan_type='enterprise', team_size=15)
        
        org1 = setup1['organization']
        org2 = setup2['organization']
        
        # Verify they're different
        assert org1.id != org2.id
        assert org1.slug != org2.slug
        assert org1.owner != org2.owner
        
        # Verify subscription isolation
        assert setup1['subscription'].organization == org1
        assert setup2['subscription'].organization == org2
        assert setup1['subscription'].plan.plan_type == 'starter'
        assert setup2['subscription'].plan.plan_type == 'enterprise'
        
        print(f"✅ Multi-tenant isolation verified: {org1.name} vs {org2.name}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])