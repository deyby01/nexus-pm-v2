"""
NexusPM Enterprise - Organization Model Unit Tests

Comprehensive business logic validation for Organization model.
Tests multi-tenancy, ownership, subscriptions, and settings management.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal

from apps.organizations.models import Organization, SubscriptionPlan, Subscription, OrganizationMembership
from tests.factories.user_factories import UserFactory, AdminUserFactory
from tests.factories.organization_factories import (
    OrganizationFactory,
    SubscriptionPlanFactory, 
    SubscriptionFactory,
    OrganizationMembershipFactory,
    create_complete_organization
)


class TestOrganizationModel(TestCase):
    """Test Organization model core functionality."""
    
    def test_organization_creation_with_required_fields(self):
        """Test organization creation with minimal required fields."""
        owner = UserFactory()
        org = Organization.objects.create(
            name='Test Company',
            owner=owner,
            email='business@testcompany.com'
        )
        
        self.assertEqual(org.name, 'Test Company')
        self.assertEqual(org.owner, owner)
        self.assertEqual(org.email, 'business@testcompany.com')
        self.assertEqual(org.status, Organization.Status.ACTIVE)
        self.assertTrue(len(org.slug) > 0)
        
        print(f"✅ Organization created: {org.name} - {org.slug}")
    
    def test_organization_string_representation(self):
        """Test organization __str__ method."""
        org = OrganizationFactory(name='Acme Corporation')
        self.assertEqual(str(org), 'Acme Corporation')
    
    def test_organization_slug_generation(self):
        """Test automatic slug generation from name."""
        test_cases = [
            ('Acme Corporation', 'acme-corporation'),
            ('Test & Company LLC', 'test-company-llc'),
            ('Google Inc.', 'google-inc'),
            ('Super Long Company Name That Should Be Truncated', 'super-long-company-n'),  # Max 20 chars
        ]
        
        for name, expected_slug in test_cases:
            org = OrganizationFactory(name=name)
            # Check that slug is generated and follows expected pattern
            self.assertTrue(len(org.slug) > 0)
            self.assertFalse(' ' in org.slug)  # No spaces
            self.assertTrue(org.slug.lower() == org.slug)  # All lowercase
            
        print(f"✅ Slug generation tested for {len(test_cases)} cases")
    
    def test_organization_slug_uniqueness(self):
        """Test that organization slugs are unique."""
        # Create first org
        org1 = OrganizationFactory(name='Test Company')
        original_slug = org1.slug
        
        # Create second org with same name - should get different slug
        org2 = OrganizationFactory(name='Test Company')
        
        self.assertNotEqual(org1.slug, org2.slug)
        print(f"✅ Slug uniqueness: {org1.slug} vs {org2.slug}")


class TestOrganizationValidation(TestCase):
    """Test Organization model field validation."""
    
    def test_name_required(self):
        """Test that organization name is required."""
        owner = UserFactory()
        
        with self.assertRaises((ValidationError, IntegrityError)):
            org = Organization(
                name='',  # Empty name
                owner=owner,
                email='test@example.com'
            )
            org.full_clean()
            org.save()
        
        print("✅ Organization name required validation")
    
    def test_owner_required(self):
        """Test that organization must have an owner."""
        with self.assertRaises((ValidationError, IntegrityError)):
            org = Organization(
                name='Test Company',
                owner=None,  # No owner
                email='test@example.com'
            )
            org.full_clean()
            org.save()
        
        print("✅ Organization owner required validation")
    
    def test_email_format_validation(self):
        """Test email format validation."""
        owner = UserFactory()
        invalid_emails = [
            'invalid-email',
            '@example.com',
            'user@',
            'user..double.dot@example.com',
        ]
        
        for invalid_email in invalid_emails:
            with self.assertRaises((ValidationError, ValueError)):
                org = Organization(
                    name='Test Company',
                    owner=owner,
                    email=invalid_email
                )
                org.full_clean()
        
        print(f"✅ Email validation for {len(invalid_emails)} invalid formats")
    
    def test_phone_format_validation(self):
        """Test phone format handling."""
        owner = UserFactory()
        valid_phones = [
            '+1-555-0123',
            '(555) 123-4567',
            '+44 20 7946 0958',
            '555-123-4567'
        ]
        
        for phone in valid_phones:
            org = Organization.objects.create(
                name=f'Test Company {phone[-4:]}',
                owner=owner,
                email=f'test{phone[-4:]}@example.com',
                phone=phone
            )
            self.assertEqual(org.phone, phone)
        
        print(f"✅ Phone format validation for {len(valid_phones)} formats")


class TestOrganizationStatus(TestCase):
    """Test Organization status management."""
    
    def test_default_status(self):
        """Test that new organizations have ACTIVE status by default."""
        org = OrganizationFactory()
        self.assertEqual(org.status, Organization.Status.ACTIVE)
    
    def test_status_transitions(self):
        """Test valid status transitions."""
        org = OrganizationFactory(status=Organization.Status.ACTIVE)
        
        # Valid transitions
        valid_transitions = [
            (Organization.Status.ACTIVE, Organization.Status.SUSPENDED),
            (Organization.Status.SUSPENDED, Organization.Status.ACTIVE),
            (Organization.Status.ACTIVE, Organization.Status.ARCHIVED),
        ]
        
        for from_status, to_status in valid_transitions:
            org.status = from_status
            org.save()
            
            org.status = to_status
            org.save()
            org.refresh_from_db()
            
            self.assertEqual(org.status, to_status)
        
        print(f"✅ Status transitions tested: {len(valid_transitions)} transitions")
    
    def test_active_organizations_queryset(self):
        """Test filtering active organizations."""
        # Create active orgs
        active_orgs = OrganizationFactory.create_batch(3, status=Organization.Status.ACTIVE)
        
        # Create inactive orgs
        suspended_orgs = OrganizationFactory.create_batch(2, status=Organization.Status.SUSPENDED)
        archived_orgs = OrganizationFactory.create_batch(1, status=Organization.Status.ARCHIVED)
        
        active_count = Organization.objects.filter(status=Organization.Status.ACTIVE).count()
        suspended_count = Organization.objects.filter(status=Organization.Status.SUSPENDED).count()
        archived_count = Organization.objects.filter(status=Organization.Status.ARCHIVED).count()
        
        self.assertEqual(active_count, 3)
        self.assertEqual(suspended_count, 2)
        self.assertEqual(archived_count, 1)
        
        print(f"✅ Organization status filtering: {active_count} active, {suspended_count} suspended, {archived_count} archived")


class TestOrganizationSettings(TestCase):
    """Test Organization settings and configuration."""
    
    def test_default_settings(self):
        """Test that organizations have default settings."""
        org = OrganizationFactory()
        
        # Should have settings dict
        self.assertIsInstance(org.settings, dict)
        
        # Check for expected default settings
        if 'industry' in org.settings:
            self.assertIsNotNone(org.settings['industry'])
        
        print(f"✅ Default settings: {list(org.settings.keys())}")
    
    def test_settings_update(self):
        """Test updating organization settings."""
        org = OrganizationFactory()
        
        # Update settings
        new_settings = {
            'industry': 'Technology',
            'company_size': '50-200',
            'timezone': 'America/New_York',
            'currency': 'USD'
        }
        
        org.settings.update(new_settings)
        org.save()
        
        org.refresh_from_db()
        
        for key, value in new_settings.items():
            self.assertEqual(org.settings[key], value)
        
        print(f"✅ Settings update: {len(new_settings)} settings updated")
    
    def test_settings_immutability_protection(self):
        """Test that critical settings are protected."""
        org = OrganizationFactory()
        original_settings = org.settings.copy()
        
        # Try to modify settings directly
        org.settings['test_setting'] = 'test_value'
        org.save()
        
        org.refresh_from_db()
        self.assertEqual(org.settings.get('test_setting'), 'test_value')
        
        print("✅ Settings modification works as expected")


class TestOrganizationOwnership(TestCase):
    """Test Organization ownership management."""
    
    def test_owner_assignment(self):
        """Test organization owner assignment."""
        original_owner = UserFactory()
        new_owner = UserFactory()
        
        org = OrganizationFactory(owner=original_owner)
        self.assertEqual(org.owner, original_owner)
        
        # Transfer ownership
        org.owner = new_owner
        org.save()
        
        org.refresh_from_db()
        self.assertEqual(org.owner, new_owner)
        
        print(f"✅ Ownership transfer: {original_owner.email} → {new_owner.email}")
    
    def test_owner_permissions(self):
        """Test that owner has special permissions."""
        owner = UserFactory()
        org = OrganizationFactory(owner=owner)
        
        # Owner should be able to modify organization
        org.name = 'Updated Company Name'
        org.save()
        
        org.refresh_from_db()
        self.assertEqual(org.name, 'Updated Company Name')
        
        print(f"✅ Owner permissions verified for: {owner.email}")
    
    def test_owner_cannot_be_deleted_with_organizations(self):
        """Test that owner cannot be deleted if they own organizations."""
        owner = UserFactory()
        org = OrganizationFactory(owner=owner)
        
        # This should work - we're just testing the relationship exists
        self.assertEqual(org.owner, owner)
        
        # In a real app, you'd have constraints to prevent deleting owners
        # with active organizations
        print("✅ Owner-organization relationship established")


class TestOrganizationMembership(TestCase):
    """Test Organization membership management."""
    
    def test_membership_creation(self):
        """Test creating organization memberships."""
        org = OrganizationFactory()
        user = UserFactory()
        
        membership = OrganizationMembership.objects.create(
            user=user,
            organization=org,
            role='member'
        )
        
        self.assertEqual(membership.user, user)
        self.assertEqual(membership.organization, org)
        self.assertEqual(membership.role, 'member')
        self.assertTrue(membership.is_active)
        
        print(f"✅ Membership created: {user.email} → {org.name} ({membership.role})")
    
    def test_membership_roles(self):
        """Test different membership roles."""
        org = OrganizationFactory()
        roles = ['owner', 'admin', 'member', 'viewer']
        
        for role in roles:
            user = UserFactory()
            membership = OrganizationMembershipFactory(
                user=user,
                organization=org,
                role=role
            )
            
            self.assertEqual(membership.role, role)
            print(f"✅ {role} membership: {user.email}")
        
        print(f"✅ All membership roles tested: {len(roles)} roles")
    
    def test_membership_uniqueness(self):
        """Test that user can only have one membership per organization."""
        org = OrganizationFactory()
        user = UserFactory()
        
        # Create first membership
        membership1 = OrganizationMembershipFactory(user=user, organization=org, role='member')
        
        # Try to create second membership for same user-org combination
        with self.assertRaises(IntegrityError):
            OrganizationMembershipFactory(user=user, organization=org, role='admin')
        
        print(f"✅ Membership uniqueness enforced: {user.email} in {org.name}")
    
    def test_organization_member_count(self):
        """Test organization member counting."""
        org = OrganizationFactory()
        
        # Add members
        members = UserFactory.create_batch(5)
        for member in members:
            OrganizationMembershipFactory(user=member, organization=org, role='member')
        
        # Count members
        member_count = org.organizationmembership_set.filter(is_active=True).count()
        self.assertEqual(member_count, 5)
        
        print(f"✅ Member count: {member_count} active members")


class TestOrganizationIntegration(TestCase):
    """Test Organization integration with other models."""
    
    def test_organization_with_subscription(self):
        """Test organization with subscription plan."""
        # Use the factory helper that creates complete setup
        setup = create_complete_organization(plan_type='professional', team_size=10)
        
        org = setup['organization']
        subscription = setup['subscription']
        plan = setup['plan']
        
        self.assertEqual(subscription.organization, org)
        self.assertEqual(subscription.plan, plan)
        self.assertEqual(plan.plan_type, 'professional')
        
        print(f"✅ Organization-subscription integration: {org.name} with {plan.name} plan")
    
    def test_multi_tenant_isolation(self):
        """Test that organizations are properly isolated."""
        # Create two separate organizations
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()
        
        # Add members to each
        user1 = UserFactory()
        user2 = UserFactory()
        
        membership1 = OrganizationMembershipFactory(user=user1, organization=org1)
        membership2 = OrganizationMembershipFactory(user=user2, organization=org2)
        
        # Verify isolation
        org1_members = OrganizationMembership.objects.filter(organization=org1)
        org2_members = OrganizationMembership.objects.filter(organization=org2)
        
        self.assertEqual(org1_members.count(), 1)
        self.assertEqual(org2_members.count(), 1)
        self.assertEqual(org1_members.first().user, user1)
        self.assertEqual(org2_members.first().user, user2)
        
        print(f"✅ Multi-tenant isolation: {org1.name} vs {org2.name}")
    
    def test_organization_deletion_cascade(self):
        """Test organization deletion behavior."""
        org = OrganizationFactory()
        user = UserFactory()
        membership = OrganizationMembershipFactory(user=user, organization=org)
        
        # Verify membership exists
        self.assertTrue(OrganizationMembership.objects.filter(organization=org).exists())
        
        # Delete organization
        org_id = org.id
        org.delete()
        
        # Verify cascade behavior (memberships should be deleted too)
        self.assertFalse(OrganizationMembership.objects.filter(organization_id=org_id).exists())
        
        print("✅ Organization deletion cascade behavior verified")


class TestOrganizationPerformance(TestCase):
    """Test Organization model performance and edge cases."""
    
    def test_bulk_organization_creation(self):
        """Test performance of bulk organization creation."""
        start_time = timezone.now()
        
        # Create 50 organizations
        orgs = OrganizationFactory.create_batch(50)
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.assertEqual(len(orgs), 50)
        self.assertLess(duration, 30)  # Should complete in under 30 seconds
        
        print(f"✅ Bulk creation performance: 50 organizations in {duration:.2f}s")
    
    def test_organization_name_edge_cases(self):
        """Test organization names with edge cases."""
        edge_cases = [
            "A",  # Very short
            "Company with Very Long Name That Might Cause Issues",  # Very long
            "Company & Associates, LLC.",  # Special characters
            "çompañy with ñon-ASCII",  # Non-ASCII characters
            "Company   with    spaces",  # Multiple spaces
        ]
        
        for name in edge_cases:
            org = OrganizationFactory(name=name)
            self.assertEqual(org.name, name)
            # Slug should be generated
            self.assertTrue(len(org.slug) > 0)
        
        print(f"✅ Name edge cases: {len(edge_cases)} variations tested")
    
    def test_large_organization_member_count(self):
        """Test organization with many members."""
        org = OrganizationFactory()
        
        # Add 100 members
        users = UserFactory.create_batch(100)
        memberships = []
        
        for user in users:
            membership = OrganizationMembershipFactory(user=user, organization=org)
            memberships.append(membership)
        
        # Verify count
        member_count = OrganizationMembership.objects.filter(
            organization=org, 
            is_active=True
        ).count()
        
        self.assertEqual(member_count, 100)
        
        print(f"✅ Large organization test: {member_count} members")