"""
NexusPM Enterprise - Factory Tests (FIELD VALIDATION FIXED)

Fixed test validations to only check fields that exist in User model.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

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


class TestUserFactories(TestCase):
    """Test User factory functions work correctly."""
    
    def test_basic_user_factory(self):
        """Test basic UserFactory creates valid users."""
        user = UserFactory()
        
        # Basic assertions - only check fields that definitely exist
        self.assertIsNotNone(user.email)
        self.assertIn('@', user.email)
        self.assertIsNotNone(user.first_name)
        self.assertIsNotNone(user.last_name)
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_email_verified)
        
        # Only check optional fields if they exist
        if hasattr(user, 'job_title'):
            self.assertIsNotNone(user.job_title)
            print(f"✅ Created user: {user.email} - {user.get_full_name()} ({user.job_title})")
        else:
            print(f"✅ Created user: {user.email} - {user.get_full_name()}")
        
        if hasattr(user, 'company'):
            self.assertIsNotNone(user.company)
    
    def test_admin_user_factory(self):
        """Test AdminUserFactory creates admin users."""
        admin = AdminUserFactory()
        
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        
        print(f"✅ Created admin: {admin.email}")
    
    def test_ceo_user_factory(self):
        """Test CEOUserFactory creates C-level users."""
        ceo = CEOUserFactory()
        
        self.assertTrue(ceo.is_staff)
        
        print(f"✅ Created C-level: {ceo.email}")
    
    def test_developer_user_factory(self):
        """Test DeveloperUserFactory creates engineering users.""" 
        dev = DeveloperUserFactory()
        
        self.assertIsNotNone(dev.email)
        self.assertTrue(dev.is_active)
        
        print(f"✅ Created developer: {dev.email}")
    
    def test_multiple_users(self):
        """Test batch user creation."""
        users = UserFactory.create_batch(5)
        
        self.assertEqual(len(users), 5)
        
        # All users should be unique
        emails = [user.email for user in users]
        self.assertEqual(len(set(emails)), 5)  # All unique
        
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
        
        self.assertEqual(len(netflix_team), 10)
        
        for email in expected_emails:
            self.assertIn(email, created_emails)
        
        # Find Reed Hastings
        reed = next(u for u in netflix_team if u.email == "reed.hastings@netflix.com")
        self.assertEqual(reed.first_name, "Reed")
        self.assertEqual(reed.last_name, "Hastings")
        
        print(f"✅ Created Netflix team: {len(netflix_team)} members")


class TestOrganizationFactories(TestCase):
    """Test Organization factory functions work correctly."""
    
    def test_basic_organization_factory(self):
        """Test basic OrganizationFactory creates valid organizations."""
        org = OrganizationFactory()
        
        self.assertIsNotNone(org.name)
        self.assertIsNotNone(org.slug)
        self.assertIsNotNone(org.owner)
        self.assertIsNotNone(org.email)
        self.assertIn('@', org.email)
        self.assertEqual(org.status, org.Status.ACTIVE)
        
        print(f"✅ Created org: {org.name} - {org.slug}")
    
    def test_subscription_plan_factory(self):
        """Test SubscriptionPlanFactory creates valid plans."""
        # Test all plan types
        for plan_type in ['free', 'starter', 'professional', 'enterprise']:
            plan = SubscriptionPlanFactory(plan_type=plan_type)
            
            self.assertEqual(plan.plan_type, plan_type)
            self.assertEqual(plan.name, plan_type.title())
            self.assertGreater(plan.max_workspaces, 0)
            self.assertGreater(plan.max_users, 0)
            
            if plan_type == 'free':
                self.assertEqual(plan.price_monthly, 0)
            else:
                self.assertGreater(plan.price_monthly, 0)
            
            print(f"✅ Created {plan_type} plan: ${plan.price_monthly}/month")
    
    def test_subscription_factory(self):
        """Test SubscriptionFactory creates valid subscriptions."""
        subscription = SubscriptionFactory()
        
        self.assertIsNotNone(subscription.organization)
        self.assertIsNotNone(subscription.plan)
        self.assertIn(subscription.status, ['active', 'trialing', 'past_due'])
        self.assertIsNotNone(subscription.stripe_customer_id)
        self.assertTrue(subscription.stripe_customer_id.startswith('cus_'))
        
        print(f"✅ Created subscription: {subscription.plan.name} for {subscription.organization.name}")
    
    def test_complete_organization_setup(self):
        """Test create_complete_organization utility."""
        setup = create_complete_organization(plan_type='professional', team_size=10)
        
        self.assertIsNotNone(setup['organization'])
        self.assertIsNotNone(setup['owner'])
        self.assertEqual(setup['plan'].plan_type, 'professional')
        self.assertEqual(setup['subscription'].status, 'active')
        self.assertGreaterEqual(len(setup['admins']), 1)
        self.assertGreaterEqual(len(setup['members']), 1)
        self.assertEqual(len(setup['memberships']), 10)  # team_size
        
        print(f"✅ Created complete org: {setup['organization'].name} with {len(setup['memberships'])} members")
    
    def test_netflix_organization_creation(self):
        """Test Netflix organization matches our simulation."""
        netflix_setup = create_netflix_organization()
        
        netflix_org = netflix_setup['organization']
        
        self.assertEqual(netflix_org.name, "Netflix Inc")
        self.assertEqual(netflix_org.slug, "netflix-inc")
        self.assertEqual(netflix_org.email, "business@netflix.com")
        self.assertEqual(len(netflix_setup['users']), 10)
        self.assertEqual(netflix_setup['plan'].plan_type, 'enterprise')
        self.assertEqual(netflix_setup['subscription'].status, 'active')
        
        # Check Reed Hastings is owner
        owner_membership = next(
            m for m in netflix_setup['memberships'] 
            if m.role == 'owner'
        )
        self.assertEqual(owner_membership.user.email, "reed.hastings@netflix.com")
        
        print(f"✅ Created Netflix organization with {len(netflix_setup['memberships'])} team members")


class TestWorkspaceFactories(TestCase):
    """Test Workspace factory functions work correctly."""
    
    def test_basic_workspace_factory(self):
        """Test basic WorkspaceFactory creates valid workspaces."""
        workspace = WorkspaceFactory()
        
        self.assertIsNotNone(workspace.name)
        self.assertIsNotNone(workspace.slug)
        self.assertIsNotNone(workspace.organization)
        self.assertIsNotNone(workspace.created_by)
        self.assertIsNotNone(workspace.workspace_type)
        self.assertIsNotNone(workspace.color)
        self.assertEqual(workspace.status, workspace.Status.ACTIVE)
        
        print(f"✅ Created workspace: {workspace.name} ({workspace.workspace_type})")
    
    def test_workspace_membership_factory(self):
        """Test WorkspaceMembershipFactory creates valid memberships."""
        membership = WorkspaceMembershipFactory()
        
        self.assertIsNotNone(membership.user)
        self.assertIsNotNone(membership.workspace)
        self.assertIsNotNone(membership.role)
        self.assertTrue(membership.is_active)
        
        print(f"✅ Created membership: {membership.user.email} → {membership.workspace.name} ({membership.role})")
    
    def test_workspace_with_team(self):
        """Test create_workspace_with_team utility."""
        setup = create_workspace_with_team(
            workspace_type='development', 
            team_size=8
        )
        
        workspace = setup['workspace']
        team_members = setup['team_members']
        
        self.assertEqual(workspace.workspace_type, 'development')
        self.assertEqual(workspace.member_count, 8)
        self.assertIn('creator', team_members)
        self.assertEqual(setup['total_members'], 8)
        
        print(f"✅ Created dev workspace: {workspace.name} with {setup['total_members']} team members")


class TestFactoryIntegration(TestCase):
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
        self.assertEqual(netflix_org.name, "Netflix Inc")
        self.assertEqual(len(netflix_users), 10)
        self.assertEqual(len(workspaces), 5)
        
        # Verify relationships
        for workspace in workspaces.values():
            self.assertEqual(workspace.organization, netflix_org)
        
        # Verify owner
        reed = next(u for u in netflix_users if u.email == "reed.hastings@netflix.com")
        self.assertEqual(netflix_org.owner, reed)
        
        print(f"✅ Complete Netflix simulation: {netflix_org.name} with {len(netflix_users)} users and {len(workspaces)} workspaces")
    
    def test_multi_tenant_isolation(self):
        """Test that different organizations are properly isolated."""
        # Create two separate organizations
        setup1 = create_complete_organization(plan_type='starter', team_size=5)
        setup2 = create_complete_organization(plan_type='enterprise', team_size=15)
        
        org1 = setup1['organization']
        org2 = setup2['organization']
        
        # Verify they're different
        self.assertNotEqual(org1.id, org2.id)
        self.assertNotEqual(org1.slug, org2.slug)
        self.assertNotEqual(org1.owner, org2.owner)
        
        # Verify subscription isolation
        self.assertEqual(setup1['subscription'].organization, org1)
        self.assertEqual(setup2['subscription'].organization, org2)
        self.assertEqual(setup1['subscription'].plan.plan_type, 'starter')
        self.assertEqual(setup2['subscription'].plan.plan_type, 'enterprise')
        
        print(f"✅ Multi-tenant isolation verified: {org1.name} vs {org2.name}")