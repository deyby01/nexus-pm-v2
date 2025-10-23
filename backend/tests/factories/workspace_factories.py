"""
NexusPM Enterprise - Workspace Factories (BUSINESS RULE COMPLIANT)

Fixed to comply with business rule: User must be organization member before joining workspace.
"""

import factory
from factory import django, fuzzy, SubFactory, LazyAttribute, RelatedFactory
from faker import Faker
from django.utils.text import slugify
from django.utils import timezone
import random

from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.organizations.models import OrganizationMembership
from .user_factories import UserFactory
from .organization_factories import OrganizationFactory

fake = Faker()

# Workspace naming patterns by type (shortened for simplicity)
WORKSPACE_NAMES = {
    'development': ['Engineering', 'Platform', 'Backend', 'Frontend', 'Mobile'],
    'marketing': ['Marketing', 'Growth', 'Digital', 'Content', 'Brand'],
    'design': ['Design', 'UX Research', 'Visual', 'Creative'],
    'sales': ['Sales', 'Enterprise', 'Inside', 'Account Mgmt'],
    'support': ['Support', 'Technical', 'Success', 'Help Desk'],
    'operations': ['Operations', 'Business', 'IT Ops', 'Security'],
    'finance': ['Finance', 'Planning', 'Accounting'],
    'hr': ['HR', 'People Ops', 'Talent'],
    'general': ['General', 'Cross-functional', 'Innovation'],
    'client': ['Client Projects', 'External', 'Consulting']
}

# Color schemes by workspace type
WORKSPACE_COLORS = {
    'development': ['#3B82F6', '#1E40AF', '#2563EB'],
    'marketing': ['#F59E0B', '#D97706', '#B45309'],
    'design': ['#EC4899', '#DB2777', '#BE185D'],
    'sales': ['#10B981', '#059669', '#047857'],
    'support': ['#8B5CF6', '#7C3AED', '#6D28D9'],
    'operations': ['#6B7280', '#4B5563', '#374151'],
    'finance': ['#EF4444', '#DC2626', '#B91C1C'],
    'hr': ['#F97316', '#EA580C', '#C2410C'],
    'general': ['#14B8A6', '#0D9488', '#0F766E'],
    'client': ['#84CC16', '#65A30D', '#4D7C0F'],
}


class WorkspaceFactory(django.DjangoModelFactory):
    """Factory for creating workspaces with business rule compliance."""
    
    class Meta:
        model = Workspace
    
    # Workspace type selection
    workspace_type = factory.LazyAttribute(
        lambda obj: random.choices(
            population=['development', 'marketing', 'design', 'sales', 'support', 
                       'operations', 'finance', 'hr', 'general', 'client'],
            weights=[25, 15, 10, 15, 10, 10, 5, 5, 5, 5],
            k=1
        )[0]
    )
    
    # Name selection
    name = factory.LazyAttribute(
        lambda obj: random.choice(WORKSPACE_NAMES.get(obj.workspace_type, ['General Team']))
    )
    
    # Slug generation
    slug = factory.LazyAttribute(
        lambda obj: slugify(obj.name)[:20]  # Ensure max 20 chars
    )
    
    description = factory.LazyAttribute(
        lambda obj: f"The {obj.name} workspace for collaboration and project management."
    )
    
    # Organization relationship
    organization = SubFactory(OrganizationFactory)
    
    # CRITICAL FIX: Ensure created_by user is organization member
    created_by = factory.LazyAttribute(
        lambda obj: obj.organization.owner  # Use organization owner as creator
    )
    
    # Status and visibility
    status = Workspace.Status.ACTIVE
    is_private = factory.LazyAttribute(
        lambda obj: random.choices(
            population=[True, False],
            weights=[30, 70],
            k=1
        )[0]
    )
    
    # Visual customization
    color = factory.LazyAttribute(
        lambda obj: random.choice(WORKSPACE_COLORS.get(obj.workspace_type, ['#3B82F6']))
    )
    
    icon = factory.LazyAttribute(
        lambda obj: {
            'development': 'code',
            'marketing': 'megaphone', 
            'design': 'palette',
            'sales': 'trending-up',
            'support': 'headphones',
            'operations': 'settings',
            'finance': 'dollar-sign',
            'hr': 'users',
            'general': 'folder',
            'client': 'briefcase'
        }.get(obj.workspace_type, 'folder')
    )
    
    # Simplified settings
    settings = factory.LazyAttribute(lambda obj: {
        'template': obj.workspace_type,
        'time_tracking': obj.workspace_type == 'development',
        'task_statuses': ['To Do', 'In Progress', 'Done']
    })
    
    # Usage tracking
    project_count = 0
    member_count = 1


class BusinessRuleCompliantWorkspaceMembershipFactory(django.DjangoModelFactory):
    """Factory for creating workspace memberships with business rule compliance."""
    
    class Meta:
        model = WorkspaceMembership
    
    user = SubFactory(UserFactory)
    workspace = SubFactory(WorkspaceFactory)
    
    role = factory.LazyAttribute(
        lambda obj: random.choices(
            population=['admin', 'manager', 'member', 'contributor', 'viewer'],
            weights=[10, 15, 60, 10, 5],
            k=1
        )[0]
    )
    
    is_active = True
    invited_by = factory.LazyAttribute(lambda obj: obj.workspace.created_by)
    invited_at = factory.LazyFunction(
        lambda: fake.past_datetime(start_date='-60d', tzinfo=timezone.utc)
    )

    @factory.post_generation
    def ensure_organization_membership(self, create, extracted, **kwargs):
        """Ensure user is organization member before workspace membership."""
        if create:
            # Create organization membership if it doesn't exist
            OrganizationMembership.objects.get_or_create(
                user=self.user,
                organization=self.workspace.organization,
                defaults={
                    'role': 'member',
                    'invited_by': self.workspace.organization.owner,
                    'is_active': True
                }
            )


# Alias for backward compatibility
WorkspaceMembershipFactory = BusinessRuleCompliantWorkspaceMembershipFactory


# Specialized workspace factories
class DevelopmentWorkspaceFactory(WorkspaceFactory):
    """Factory for development/engineering workspaces."""
    
    workspace_type = 'development'
    name = factory.fuzzy.FuzzyChoice(WORKSPACE_NAMES['development'])
    is_private = True


class MarketingWorkspaceFactory(WorkspaceFactory):
    """Factory for marketing workspaces."""
    
    workspace_type = 'marketing'
    name = factory.fuzzy.FuzzyChoice(WORKSPACE_NAMES['marketing'])
    is_private = False


class DesignWorkspaceFactory(WorkspaceFactory):
    """Factory for design workspaces."""
    
    workspace_type = 'design'
    name = factory.fuzzy.FuzzyChoice(WORKSPACE_NAMES['design'])


# Utility functions
def create_workspace_with_team(workspace_type='development', team_size=8, organization=None):
    """Create a workspace with a complete team structure (business rule compliant)."""
    if not organization:
        organization = OrganizationFactory()
    
    # Use organization owner as creator (already organization member)
    creator = organization.owner
    
    # Create workspace
    workspace = WorkspaceFactory(
        workspace_type=workspace_type,
        organization=organization,
        created_by=creator
    )
    
    # Create team members
    team_members = {'creator': creator}
    
    # Create additional users as organization members first
    additional_users = UserFactory.create_batch(team_size - 1)
    
    for user in additional_users:
        # Make them organization members first
        OrganizationMembership.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={
                'role': 'member',
                'invited_by': creator,
                'is_active': True
            }
        )
        
        # Then create workspace membership
        role = random.choice(['manager', 'member', 'contributor'])
        WorkspaceMembershipFactory(
            user=user,
            workspace=workspace,
            role=role,
            invited_by=creator
        )
    
    team_members['additional_users'] = additional_users
    
    # Update workspace member count
    workspace.member_count = team_size
    workspace.save()
    
    return {
        'workspace': workspace,
        'organization': organization,
        'team_members': team_members,
        'total_members': team_size
    }


def create_netflix_workspaces(netflix_org, netflix_users):
    """Create Netflix workspaces matching our simulation data."""
    # All Netflix users should already be organization members
    
    # Find key Netflix team members
    reed_hastings = next(u for u in netflix_users if u.email == "reed.hastings@netflix.com")
    
    # Create workspaces with organization owner as creator
    workspaces = {}
    
    workspaces['content'] = WorkspaceFactory(
        name='Content Production',
        workspace_type='general',
        description='Original series and films production management',
        color='#E50914',
        is_private=False,
        organization=netflix_org,
        created_by=reed_hastings  # Organization owner
    )
    
    workspaces['engineering'] = WorkspaceFactory(
        name='Engineering Platform', 
        workspace_type='development',
        description='Core platform development and infrastructure',
        color='#3B82F6',
        is_private=True,
        organization=netflix_org,
        created_by=reed_hastings  # Organization owner
    )
    
    return workspaces