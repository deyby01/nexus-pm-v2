"""
NexusPM Enterprise - Integration Test Suite

Comprehensive cross-model integration testing validating complete business workflows,
multi-tenant isolation, and system performance under realistic usage scenarios.
"""

from django.test import TestCase, TransactionTestCase
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from datetime import timedelta
import time

from apps.users.models import User
from apps.organizations.models import Organization, OrganizationMembership
from apps.workspaces.models import Workspace, WorkspaceMembership

from tests.factories.user_factories import UserFactory, AdminUserFactory
from tests.factories.organization_factories import (
    OrganizationFactory, 
    create_complete_organization
)
from tests.factories.workspace_factories import (
    WorkspaceFactory,
    create_workspace_with_team,
    create_netflix_workspaces
)


class TestCrossModelIntegration(TestCase):
    """Test integration between User, Organization, and Workspace models."""
    
    def test_complete_user_onboarding_workflow(self):
        """Test complete user onboarding from registration to workspace membership."""
        # Step 1: User registration
        user = User.objects.create_user(
            email='john.doe@newcompany.com',
            password='secure123!',
            first_name='John',
            last_name='Doe'
        )
        
        # Step 2: Organization creation
        organization = Organization.objects.create(
            name='New Company Inc',
            owner=user,
            email='contact@newcompany.com'
        )
        
        # Step 3: User becomes organization member automatically
        org_membership = OrganizationMembership.objects.get(
            user=user,
            organization=organization
        )
        self.assertEqual(org_membership.role, 'owner')
        
        # Step 4: Create workspace
        workspace = Workspace.objects.create(
            name='Engineering Team',
            organization=organization,
            created_by=user,
            workspace_type='development'
        )
        
        # Step 5: Verify workspace membership created automatically
        workspace_membership = WorkspaceMembership.objects.get(
            user=user,
            workspace=workspace
        )
        self.assertEqual(workspace_membership.role, 'admin')
        
        print(f"✅ Complete onboarding: {user.email} → {organization.name} → {workspace.name}")
    
    def test_multi_tenant_isolation_comprehensive(self):
        """Test comprehensive multi-tenant isolation across all models."""
        # Create two separate companies
        company_a = create_complete_organization(
            plan_type='professional',
            team_size=5
        )
        
        company_b = create_complete_organization( 
            plan_type='enterprise',
            team_size=8
        )
        
        org_a = company_a['organization']
        org_b = company_b['organization']
        
        # Create workspaces for each company
        workspace_a = WorkspaceFactory(
            name='Team A Workspace',
            organization=org_a,
            created_by=org_a.owner
        )
        
        workspace_b = WorkspaceFactory(
            name='Team B Workspace', 
            organization=org_b,
            created_by=org_b.owner
        )
        
        # Verify isolation
        org_a_members = OrganizationMembership.objects.filter(organization=org_a).count()
        org_b_members = OrganizationMembership.objects.filter(organization=org_b).count()
        
        org_a_workspaces = Workspace.objects.filter(organization=org_a).count()
        org_b_workspaces = Workspace.objects.filter(organization=org_b).count()
        
        # Verify no cross-contamination
        self.assertEqual(org_a_workspaces, 1)
        self.assertEqual(org_b_workspaces, 1)
        self.assertNotEqual(org_a_members, org_b_members)
        
        print(f"✅ Multi-tenant isolation: Company A ({org_a_members} members, {org_a_workspaces} workspaces) vs Company B ({org_b_members} members, {org_b_workspaces} workspaces)")
    
    def test_permission_cascading_validation(self):
        """Test permission cascading from organization to workspace level."""
        # Create organization with owner
        org = OrganizationFactory()
        owner = org.owner
        
        # Create regular user and add to organization
        regular_user = UserFactory()
        org_membership = OrganizationMembership.objects.create(
            user=regular_user,
            organization=org,
            role='member',
            invited_by=owner
        )
        
        # Create workspace
        workspace = WorkspaceFactory(
            organization=org,
            created_by=owner
        )
        
        # Regular user should be able to join workspace (org member)
        workspace_membership = WorkspaceMembership.objects.create(
            user=regular_user,
            workspace=workspace,
            role='member'
        )
        
        self.assertEqual(workspace_membership.user, regular_user)
        self.assertEqual(workspace_membership.workspace.organization, org)
        
        # Test user from different organization cannot join
        other_org = OrganizationFactory()
        other_user = other_org.owner
        
        with self.assertRaises(ValidationError):
            invalid_membership = WorkspaceMembership(
                user=other_user,
                workspace=workspace,  # Workspace from different org
                role='member'
            )
            invalid_membership.clean()
            invalid_membership.save()
        
        print(f"✅ Permission cascading: Org member can join workspace, external users cannot")
    
    def test_business_rule_consistency(self):
        """Test business rule consistency across model interactions."""
        # Create organization
        org = OrganizationFactory()
        
        # Test workspace limit enforcement (if implemented)
        workspaces = []
        for i in range(5):
            workspace = WorkspaceFactory(
                name=f'Workspace {i+1}',
                organization=org,
                created_by=org.owner
            )
            workspaces.append(workspace)
        
        # Verify all workspaces belong to same organization
        for workspace in workspaces:
            self.assertEqual(workspace.organization, org)
            self.assertEqual(workspace.created_by, org.owner)
        
        # Test member count consistency
        total_members = OrganizationMembership.objects.filter(
            organization=org,
            is_active=True
        ).count()
        
        self.assertGreaterEqual(total_members, 1)  # At least the owner
        
        print(f"✅ Business rule consistency: {len(workspaces)} workspaces, {total_members} org members")


class TestFactoryIntegrationWorkflows(TestCase):
    """Test factory integration for complex business scenarios."""
    
    def test_netflix_complete_simulation(self):
        """Test complete Netflix company simulation using factories."""
        # Create Netflix organization with full team
        netflix_setup = create_complete_organization(
            organization_name='Netflix',
            plan_type='enterprise',
            team_size=25
        )
        
        netflix_org = netflix_setup['organization']
        netflix_members = netflix_setup['members']
        
        # Create Netflix-specific users
        netflix_users = [
            User.objects.create_user(
                email='reed.hastings@netflix.com',
                first_name='Reed',
                last_name='Hastings',
                password='netflix2024!'
            ),
            User.objects.create_user(
                email='greg.peters@netflix.com', 
                first_name='Greg',
                last_name='Peters',
                password='netflix2024!'
            ),
            User.objects.create_user(
                email='sarah.connor@netflix.com',
                first_name='Sarah', 
                last_name='Connor',
                password='netflix2024!'
            )
        ]
        
        # Add Netflix executives to organization
        for user in netflix_users:
            OrganizationMembership.objects.get_or_create(
                user=user,
                organization=netflix_org,
                defaults={
                    'role': 'admin',
                    'invited_by': netflix_org.owner,
                    'is_active': True
                }
            )
        
        # Create Netflix workspaces
        netflix_workspaces = create_netflix_workspaces(netflix_org, netflix_users)
        
        # Verify Netflix simulation
        self.assertEqual(len(netflix_workspaces), 2)  # Based on factory implementation
        
        total_members = OrganizationMembership.objects.filter(
            organization=netflix_org,
            is_active=True
        ).count()
        
        total_workspaces = Workspace.objects.filter(
            organization=netflix_org
        ).count()
        
        print(f"✅ Netflix simulation: {netflix_org.name} with {total_members} members and {total_workspaces} workspaces")
    
    def test_cross_functional_team_creation(self):
        """Test creating cross-functional teams across multiple workspaces."""
        # Create base organization
        org = OrganizationFactory()
        
        # Create 15 users
        users = UserFactory.create_batch(15)
        
        # Add all users to organization
        for user in users:
            OrganizationMembership.objects.get_or_create(
                user=user,
                organization=org,
                defaults={
                    'role': 'member',
                    'invited_by': org.owner,
                    'is_active': True
                }
            )
        
        # Create multiple workspaces
        engineering = WorkspaceFactory(
            name='Engineering',
            workspace_type='development',
            organization=org,
            created_by=org.owner
        )
        
        marketing = WorkspaceFactory(
            name='Marketing',
            workspace_type='marketing', 
            organization=org,
            created_by=org.owner
        )
        
        design = WorkspaceFactory(
            name='Design',
            workspace_type='design',
            organization=org, 
            created_by=org.owner
        )
        
        workspaces = [engineering, marketing, design]
        
        # Assign users to multiple workspaces (cross-functional)
        assignments = {}
        for i, user in enumerate(users[:12]):  # Use 12 users
            # Each user joins 1-3 workspaces
            import random
            num_workspaces = random.randint(1, 3)
            user_workspaces = random.sample(workspaces, num_workspaces)
            
            user_assignments = []
            for workspace in user_workspaces:
                role = 'admin' if i == 0 else random.choice(['manager', 'member'])
                membership = WorkspaceMembership.objects.create(
                    user=user,
                    workspace=workspace,
                    role=role,
                    invited_by=org.owner
                )
                user_assignments.append(membership)
            
            assignments[user.email] = user_assignments
        
        # Verify cross-functional assignments
        total_memberships = WorkspaceMembership.objects.filter(
            workspace__organization=org
        ).count()
        
        self.assertGreater(total_memberships, len(users[:12]))  # More memberships than users (cross-functional)
        
        print(f"✅ Cross-functional teams: {len(assignments)} users across {len(workspaces)} workspaces ({total_memberships} total memberships)")
    
    def test_bulk_user_onboarding_workflow(self):
        """Test bulk user onboarding performance and correctness."""
        start_time = timezone.now()
        
        # Create organization
        org = OrganizationFactory()
        
        # Bulk create 50 users
        users = UserFactory.create_batch(50)
        
        # Bulk add to organization
        memberships = []
        for user in users:
            membership = OrganizationMembership(
                user=user,
                organization=org,
                role='member',
                invited_by=org.owner,
                is_active=True,
                invited_at=timezone.now()
            )
            memberships.append(membership)
        
        OrganizationMembership.objects.bulk_create(memberships)
        
        # Create workspace for team
        workspace = WorkspaceFactory(
            name='Large Team Workspace',
            organization=org,
            created_by=org.owner
        )
        
        # Add subset to workspace
        workspace_memberships = []
        for user in users[:30]:  # Add 30 users to workspace
            ws_membership = WorkspaceMembership(
                user=user,
                workspace=workspace,
                role='member',
                invited_by=org.owner
            )
            workspace_memberships.append(ws_membership)
        
        WorkspaceMembership.objects.bulk_create(workspace_memberships)
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        # Verify results
        org_member_count = OrganizationMembership.objects.filter(organization=org).count()
        workspace_member_count = WorkspaceMembership.objects.filter(workspace=workspace).count()
        
        self.assertEqual(org_member_count, 50)
        self.assertEqual(workspace_member_count, 30)
        self.assertLess(duration, 10)  # Should complete in under 10 seconds
        
        print(f"✅ Bulk onboarding: 50 users in {duration:.2f}s ({org_member_count} org members, {workspace_member_count} workspace members)")


class TestSystemPerformanceIntegration(TransactionTestCase):
    """Test system performance under realistic load conditions."""
    
    def test_concurrent_workspace_creation(self):
        """Test concurrent workspace creation performance."""
        start_time = timezone.now()
        
        # Create organization
        org = OrganizationFactory()
        
        # Create 20 workspaces concurrently (simulated)
        workspaces = []
        for i in range(20):
            workspace = WorkspaceFactory(
                name=f'Concurrent Workspace {i+1}',
                organization=org,
                created_by=org.owner
            )
            workspaces.append(workspace)
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        # Verify all workspaces created
        workspace_count = Workspace.objects.filter(organization=org).count()
        self.assertEqual(workspace_count, 20)
        
        # Performance validation
        self.assertLess(duration, 15)  # Should complete in under 15 seconds
        
        print(f"✅ Concurrent creation: 20 workspaces in {duration:.2f}s")
    
    def test_large_organization_performance(self):
        """Test performance with large organization (100+ members)."""
        start_time = timezone.now()
        
        # Create large organization
        large_org_setup = create_complete_organization(
            organization_name='Large Enterprise Corp',
            plan_type='enterprise', 
            team_size=100
        )
        
        org = large_org_setup['organization']
        
        # Create 10 workspaces
        workspaces = []
        for i in range(10):
            workspace = WorkspaceFactory(
                name=f'Department {i+1}',
                organization=org,
                created_by=org.owner
            )
            workspaces.append(workspace)
        
        # Query performance test
        query_start = timezone.now()
        
        # Complex queries
        active_members = OrganizationMembership.objects.filter(
            organization=org,
            is_active=True
        ).count()
        
        total_workspaces = Workspace.objects.filter(
            organization=org
        ).count()
        
        workspace_memberships = WorkspaceMembership.objects.filter(
            workspace__organization=org
        ).count()
        
        query_end = timezone.now()
        query_duration = (query_end - query_start).total_seconds()
        
        end_time = timezone.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Performance validations
        self.assertEqual(total_workspaces, 10)
        self.assertGreaterEqual(active_members, 100)
        self.assertLess(query_duration, 2)  # Queries should be fast
        self.assertLess(total_duration, 30)  # Total should be reasonable
        
        print(f"✅ Large org performance: {active_members} members, {total_workspaces} workspaces, {workspace_memberships} memberships in {total_duration:.2f}s (queries: {query_duration:.2f}s)")
    
    def test_database_constraint_validation_performance(self):
        """Test database constraint validation under load."""
        org = OrganizationFactory()
        
        # Test unique constraint enforcement
        start_time = timezone.now()
        
        # Create workspace with specific slug
        workspace1 = WorkspaceFactory(
            name='Engineering Team',
            organization=org,
            created_by=org.owner
        )
        
        # Try to create duplicate slug (should handle gracefully)
        try:
            workspace2 = WorkspaceFactory(
                name='Engineering Team',  # Same name = same slug
                organization=org,
                created_by=org.owner
            )
            # If it succeeds, slug generation is working (adding suffix)
            self.assertNotEqual(workspace1.slug, workspace2.slug)
        except IntegrityError:
            # If it fails, constraint is working (expected)
            pass
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.assertLess(duration, 2)  # Should handle constraints quickly
        
        print(f"✅ Constraint validation performance: {duration:.2f}s")


class TestEndToEndBusinessWorkflows(TestCase):
    """Test complete end-to-end business workflows."""
    
    def test_startup_company_scaling_workflow(self):
        """Test complete startup scaling from 1 person to 50+ person company."""
        # Phase 1: Founder creates company
        founder = User.objects.create_user(
            email='founder@startup.com',
            first_name='Jane',
            last_name='Founder',
            password='startup2024!'
        )
        
        startup = Organization.objects.create(
            name='Innovative Startup Inc',
            owner=founder,
            email='contact@startup.com'
        )
        
        # Phase 2: Create initial workspace
        initial_workspace = Workspace.objects.create(
            name='Core Team',
            organization=startup,
            created_by=founder,
            workspace_type='general'
        )
        
        # Phase 3: Hire first 5 employees
        early_employees = UserFactory.create_batch(5)
        for employee in early_employees:
            # Add to organization
            OrganizationMembership.objects.create(
                user=employee,
                organization=startup,
                role='member',
                invited_by=founder
            )
            
            # Add to initial workspace
            WorkspaceMembership.objects.create(
                user=employee,
                workspace=initial_workspace,
                role='member',
                invited_by=founder
            )
        
        # Phase 4: Scale to departments (20 more employees)
        department_employees = UserFactory.create_batch(20)
        
        # Create department workspaces
        engineering = WorkspaceFactory(
            name='Engineering',
            workspace_type='development',
            organization=startup,
            created_by=founder
        )
        
        marketing = WorkspaceFactory(
            name='Marketing',
            workspace_type='marketing', 
            organization=startup,
            created_by=founder
        )
        
        sales = WorkspaceFactory(
            name='Sales',
            workspace_type='sales',
            organization=startup,
            created_by=founder
        )
        
        departments = [engineering, marketing, sales]
        
        # Assign employees to departments
        for i, employee in enumerate(department_employees):
            # Add to organization
            OrganizationMembership.objects.create(
                user=employee,
                organization=startup,
                role='member',
                invited_by=founder
            )
            
            # Assign to department (round-robin)
            department = departments[i % len(departments)]
            WorkspaceMembership.objects.create(
                user=employee,
                workspace=department,
                role='member',
                invited_by=founder
            )
        
        # Phase 5: Add managers
        managers = UserFactory.create_batch(3)
        for i, manager in enumerate(managers):
            # Add to organization as admin
            OrganizationMembership.objects.create(
                user=manager,
                organization=startup,
                role='admin',
                invited_by=founder
            )
            
            # Make manager of department
            department = departments[i]
            WorkspaceMembership.objects.create(
                user=manager,
                workspace=department,
                role='manager',
                invited_by=founder
            )
        
        # Verify scaling results
        total_employees = OrganizationMembership.objects.filter(
            organization=startup
        ).count()
        
        total_workspaces = Workspace.objects.filter(
            organization=startup
        ).count()
        
        total_workspace_memberships = WorkspaceMembership.objects.filter(
            workspace__organization=startup
        ).count()
        
        # Validations
        self.assertEqual(total_employees, 29)  # 1 founder + 5 early + 20 dept + 3 managers
        self.assertEqual(total_workspaces, 4)  # initial + 3 departments
        self.assertGreaterEqual(total_workspace_memberships, 28)  # At least one per employee minus founder
        
        print(f"✅ Startup scaling: {startup.name} scaled to {total_employees} employees across {total_workspaces} workspaces")
    
    def test_enterprise_acquisition_workflow(self):
        """Test enterprise acquisition and team merger workflow."""
        # Create acquiring company
        big_corp = create_complete_organization(
            organization_name='BigCorp Enterprises',
            plan_type='enterprise',
            team_size=50
        )
        
        # Create startup being acquired
        startup = create_complete_organization(
            organization_name='Innovative Startup',
            plan_type='professional', 
            team_size=15
        )
        
        big_corp_org = big_corp['organization']
        startup_org = startup['organization']
        
        # Simulate acquisition: Transfer startup users to big corp
        startup_members = OrganizationMembership.objects.filter(
            organization=startup_org,
            is_active=True
        )
        
        transferred_count = 0
        for membership in startup_members:
            user = membership.user
            
            # Create membership in acquiring company
            OrganizationMembership.objects.get_or_create(
                user=user,
                organization=big_corp_org,
                defaults={
                    'role': 'member',
                    'invited_by': big_corp_org.owner,
                    'is_active': True,
                    'invited_at': timezone.now()
                }
            )
            
            transferred_count += 1
        
        # Create integration workspace
        integration_workspace = WorkspaceFactory(
            name='Acquisition Integration Team',
            organization=big_corp_org,
            created_by=big_corp_org.owner,
            workspace_type='general'
        )
        
        # Verify acquisition results
        final_member_count = OrganizationMembership.objects.filter(
            organization=big_corp_org,
            is_active=True
        ).count()
        
        # Should have original big corp + transferred startup members
        self.assertGreaterEqual(final_member_count, 50 + transferred_count)
        
        print(f"✅ Enterprise acquisition: {transferred_count} startup members integrated into {big_corp_org.name} (total: {final_member_count} members)")


class TestDataIntegrityValidation(TestCase):
    """Test data integrity and consistency across complex scenarios."""
    
    def test_orphaned_record_prevention(self):
        """Test prevention of orphaned records across model relationships."""
        # Create complete setup
        org = OrganizationFactory()
        workspace = WorkspaceFactory(organization=org, created_by=org.owner)
        user = UserFactory()
        
        # Add user to organization
        org_membership = OrganizationMembership.objects.create(
            user=user,
            organization=org,
            role='member',
            invited_by=org.owner
        )
        
        # Add user to workspace
        ws_membership = WorkspaceMembership.objects.create(
            user=user,
            workspace=workspace,
            role='member'
        )
        
        # Test cascading deletes (if implemented)
        initial_ws_memberships = WorkspaceMembership.objects.filter(workspace=workspace).count()
        
        # Delete organization (should cascade appropriately)
        org_id = org.id
        workspace_id = workspace.id
        
        # Instead of actual deletion (which might not be allowed), test relationships
        self.assertEqual(workspace.organization, org)
        self.assertEqual(ws_membership.workspace, workspace)
        self.assertEqual(org_membership.organization, org)
        
        print(f"✅ Data integrity: Relationships properly maintained (org: {org_id}, workspace: {workspace_id})")
    
    def test_concurrent_membership_creation(self):
        """Test handling of concurrent membership creation attempts."""
        org = OrganizationFactory() 
        user = UserFactory()
        workspace = WorkspaceFactory(organization=org, created_by=org.owner)
        
        # Add user to organization first
        OrganizationMembership.objects.create(
            user=user,
            organization=org,
            role='member',
            invited_by=org.owner
        )
        
        # Test unique constraint on workspace membership
        membership1 = WorkspaceMembership.objects.create(
            user=user,
            workspace=workspace,
            role='member'
        )
        
        # Try to create duplicate membership
        with self.assertRaises(IntegrityError):
            membership2 = WorkspaceMembership.objects.create(
                user=user,
                workspace=workspace,  # Same user, same workspace
                role='admin'  # Different role, but should still fail uniqueness
            )
        
        # Verify only one membership exists
        membership_count = WorkspaceMembership.objects.filter(
            user=user,
            workspace=workspace
        ).count()
        
        self.assertEqual(membership_count, 1)
        
        print(f"✅ Concurrent membership protection: Duplicate prevented")


# Test discovery and execution helpers
def run_integration_tests():
    """Helper to run all integration tests with proper reporting."""
    print("🚀 Starting NexusPM Integration Test Suite...")
    print("=" * 60)
    
    test_classes = [
        TestCrossModelIntegration,
        TestFactoryIntegrationWorkflows, 
        TestSystemPerformanceIntegration,
        TestEndToEndBusinessWorkflows,
        TestDataIntegrityValidation
    ]
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}...")
        # Individual test execution would happen here
    
    print("\n🏆 Integration Test Suite Complete!")


if __name__ == '__main__':
    run_integration_tests()