"""
NexusPM Enterprise - Workspace Factories (FIXED)

Fixed FuzzyChoice weights compatibility issue.
"""

import factory
from factory import django, fuzzy, SubFactory, LazyAttribute, RelatedFactory
from faker import Faker
from django.utils.text import slugify
import random

from apps.workspaces.models import Workspace, WorkspaceMembership
from .user_factories import UserFactory
from .organization_factories import OrganizationFactory

fake = Faker()

# Workspace naming patterns by type
WORKSPACE_NAMES = {
    'development': [
        'Engineering Team', 'Platform Engineering', 'Backend Development',
        'Frontend Development', 'Mobile Development', 'DevOps Team',
        'Infrastructure Team', 'API Development', 'Core Engineering'
    ],
    'marketing': [
        'Marketing Team', 'Growth Marketing', 'Digital Marketing',
        'Content Marketing', 'Brand Marketing', 'Product Marketing',
        'Marketing Operations', 'Demand Generation', 'Field Marketing'
    ],
    'design': [
        'Design Team', 'Product Design', 'UX Research', 'Visual Design',
        'Brand Design', 'Design Systems', 'User Experience',
        'Creative Team', 'Design Operations'
    ],
    'sales': [
        'Sales Team', 'Enterprise Sales', 'Inside Sales', 'Sales Development',
        'Account Management', 'Sales Operations', 'Channel Partners',
        'Customer Success', 'Revenue Operations'
    ],
    'support': [
        'Customer Support', 'Technical Support', 'Customer Success',
        'Help Desk', 'Customer Care', 'Support Engineering',
        'Customer Operations', 'Success Team', 'Client Services'
    ],
    'operations': [
        'Operations Team', 'Business Operations', 'IT Operations',
        'Security Operations', 'Data Operations', 'Platform Operations',
        'Corporate Operations', 'Strategic Operations', 'Operational Excellence'
    ],
    'finance': [
        'Finance Team', 'Corporate Finance', 'Financial Planning',
        'Accounting Team', 'Revenue Operations', 'Business Finance',
        'Financial Analysis', 'Treasury Team', 'Controller Office'
    ],
    'hr': [
        'Human Resources', 'People Operations', 'Talent Acquisition',
        'People Team', 'HR Business Partners', 'Talent Development',
        'Employee Experience', 'People Analytics', 'Culture Team'
    ],
    'general': [
        'General Team', 'Cross-functional Team', 'Innovation Lab',
        'Strategic Initiatives', 'Special Projects', 'Task Force',
        'Working Group', 'Committee', 'Core Team'
    ],
    'client': [
        'Client Projects', 'External Projects', 'Consulting Team',
        'Professional Services', 'Client Delivery', 'Implementation Team',
        'Customer Projects', 'Service Delivery', 'Client Success'
    ]
}

# Color schemes by workspace type
WORKSPACE_COLORS = {
    'development': ['#3B82F6', '#1E40AF', '#2563EB', '#1D4ED8'],
    'marketing': ['#F59E0B', '#D97706', '#B45309', '#92400E'],
    'design': ['#EC4899', '#DB2777', '#BE185D', '#9D174D'],
    'sales': ['#10B981', '#059669', '#047857', '#065F46'],
    'support': ['#8B5CF6', '#7C3AED', '#6D28D9', '#5B21B6'],
    'operations': ['#6B7280', '#4B5563', '#374151', '#1F2937'],
    'finance': ['#EF4444', '#DC2626', '#B91C1C', '#991B1B'],
    'hr': ['#F97316', '#EA580C', '#C2410C', '#9A3412'],
    'general': ['#14B8A6', '#0D9488', '#0F766E', '#115E59'],
    'client': ['#84CC16', '#65A30D', '#4D7C0F', '#365314'],
}


class WorkspaceFactory(django.DjangoModelFactory):
    """Factory for creating workspaces with realistic team configurations."""
    
    class Meta:
        model = Workspace
        django_get_or_create = ('organization', 'slug')
    
    # Basic information - Use LazyAttribute with weighted choice
    workspace_type = factory.LazyAttribute(
        lambda obj: fake.choices(
            elements=['development', 'marketing', 'design', 'sales', 'support', 
                     'operations', 'finance', 'hr', 'general', 'client'],
            weights=[25, 15, 10, 15, 10, 10, 5, 5, 5, 5],
            length=1
        )[0]
    )
    
    name = factory.LazyAttribute(
        lambda obj: fake.choice(WORKSPACE_NAMES.get(obj.workspace_type, ['General Team']))
    )
    
    slug = factory.LazyAttribute(
        lambda obj: slugify(obj.name)
    )
    
    description = factory.LazyAttribute(
        lambda obj: f"The {obj.name} is responsible for {fake.sentence(nb_words=8)} "
                   f"and collaborates closely with other teams to achieve company objectives."
    )
    
    # Organizational relationship
    organization = SubFactory(OrganizationFactory)
    created_by = SubFactory(UserFactory)
    
    # Status and visibility
    status = Workspace.Status.ACTIVE
    is_private = factory.LazyAttribute(
        lambda obj: fake.choices(
            elements=[True, False],
            weights=[30, 70],
            length=1
        )[0]
    )
    
    # Visual customization
    color = factory.LazyAttribute(
        lambda obj: fake.choice(WORKSPACE_COLORS.get(obj.workspace_type, ['#3B82F6']))
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
    
    # Settings based on workspace type
    settings = factory.LazyAttribute(lambda obj: {
        'development': {
            'default_project_template': 'agile_scrum',
            'enable_time_tracking': True,
            'enable_code_integration': True,
            'default_task_statuses': ['Backlog', 'In Progress', 'Code Review', 'Testing', 'Done'],
            'sprint_length': 14,
            'story_points_enabled': True
        },
        'marketing': {
            'default_project_template': 'campaign',
            'enable_asset_management': True,
            'enable_approval_workflows': True,
            'default_task_statuses': ['Ideas', 'Planning', 'In Progress', 'Review', 'Published'],
            'campaign_tracking': True,
            'content_calendar': True
        },
        'design': {
            'default_project_template': 'design_sprint',
            'enable_asset_management': True,
            'enable_version_control': True,
            'default_task_statuses': ['Concept', 'Design', 'Review', 'Approved', 'Delivered'],
            'design_system_integration': True,
            'feedback_tools': True
        }
    }.get(obj.workspace_type, {
        'default_project_template': 'general',
        'enable_time_tracking': False,
        'default_task_statuses': ['To Do', 'In Progress', 'Done'],
    }))
    
    # Usage tracking
    project_count = 0
    member_count = 1


class WorkspaceMembershipFactory(django.DjangoModelFactory):
    """Factory for creating workspace memberships."""
    
    class Meta:
        model = WorkspaceMembership
    
    user = SubFactory(UserFactory)
    workspace = SubFactory(WorkspaceFactory)
    
    # Use LazyAttribute with weighted choice
    role = factory.LazyAttribute(
        lambda obj: fake.choices(
            elements=['admin', 'manager', 'member', 'contributor', 'viewer'],
            weights=[10, 15, 60, 10, 5],
            length=1
        )[0]
    )
    
    is_active = True
    
    # Invitation data
    invited_by = SubFactory(UserFactory)
    invited_at = factory.LazyFunction(
        lambda: fake.past_datetime(start_date='-60d', tzinfo=timezone.utc)
    )


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


class ClientWorkspaceFactory(WorkspaceFactory):
    """Factory for client project workspaces."""
    
    workspace_type = 'client'
    name = factory.fuzzy.FuzzyChoice(WORKSPACE_NAMES['client'])
    is_private = True


# Utility functions for complex scenarios
def create_workspace_with_team(workspace_type='development', team_size=8, organization=None):
    """Create a workspace with a complete team structure."""
    if not organization:
        organization = OrganizationFactory()
    
    # Create workspace creator (will be admin)
    creator = UserFactory()
    
    # Create workspace
    workspace = WorkspaceFactory(
        workspace_type=workspace_type,
        organization=organization,
        created_by=creator
    )
    
    # Create team members
    team_members = {'creator': creator}
    
    # Simple team structure without weights
    admin_count = 1
    manager_count = max(1, team_size // 5)  
    member_count = max(1, team_size - admin_count - manager_count)
    
    # Create managers
    if manager_count > 0:
        managers = UserFactory.create_batch(manager_count)
        for manager in managers:
            WorkspaceMembershipFactory(
                user=manager,
                workspace=workspace,
                role='manager',
                invited_by=creator
            )
        team_members['managers'] = managers
    
    # Create members
    if member_count > 0:
        members = UserFactory.create_batch(member_count)
        for member in members:
            WorkspaceMembershipFactory(
                user=member,
                workspace=workspace,
                role='member',
                invited_by=creator
            )
        team_members['members'] = members
    
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
    # Find key Netflix team members
    reed_hastings = next(u for u in netflix_users if u.email == "reed.hastings@netflix.com")
    greg_peters = next(u for u in netflix_users if u.email == "greg.peters@netflix.com") 
    sarah_connor = next(u for u in netflix_users if u.email == "sarah.connor@netflix.com")
    lisa_wang = next(u for u in netflix_users if u.email == "lisa.wang@netflix.com")
    carlos_mendez = next(u for u in netflix_users if u.email == "carlos.mendez@netflix.com")
    
    # Create workspaces
    workspaces = {}
    
    # Content Production Workspace
    workspaces['content'] = WorkspaceFactory(
        name='Content Production',
        workspace_type='general',
        description='Original series and films production management',
        color='#E50914',
        is_private=False,
        organization=netflix_org,
        created_by=sarah_connor
    )
    
    # Engineering Platform Workspace
    workspaces['engineering'] = WorkspaceFactory(
        name='Engineering Platform', 
        workspace_type='development',
        description='Core platform development and infrastructure',
        color='#3B82F6',
        is_private=True,
        organization=netflix_org,
        created_by=greg_peters
    )
    
    # Data Science & ML Workspace
    workspaces['data_science'] = WorkspaceFactory(
        name='Data Science & ML',
        workspace_type='general',
        description='Recommendation algorithms and data analytics', 
        color='#10B981',
        is_private=True,
        organization=netflix_org,
        created_by=lisa_wang
    )
    
    # Marketing & Growth Workspace
    workspaces['marketing'] = WorkspaceFactory(
        name='Marketing & Growth',
        workspace_type='marketing',
        description='Global marketing campaigns and user acquisition',
        color='#F59E0B',
        is_private=False,
        organization=netflix_org,
        created_by=carlos_mendez
    )
    
    # Executive Operations Workspace
    workspaces['executive'] = WorkspaceFactory(
        name='Executive Operations',
        workspace_type='operations',
        description='C-level strategic initiatives and company operations',
        color='#8B5CF6',
        is_private=True,
        organization=netflix_org,
        created_by=reed_hastings
    )
    
    return workspaces


def create_cross_functional_team(organization, users):
    """Create workspaces where users have memberships across multiple teams."""
    # Create multiple workspaces
    engineering = DevelopmentWorkspaceFactory(organization=organization)
    marketing = MarketingWorkspaceFactory(organization=organization) 
    design = DesignWorkspaceFactory(organization=organization)
    
    workspaces = [engineering, marketing, design]
    assignments = {}
    
    # Assign users to multiple workspaces with different roles
    for i, user in enumerate(users[:10]):
        user_assignments = []
        
        # Each user is in 1-3 workspaces
        num_workspaces = random.randint(1, min(3, len(workspaces)))
        user_workspaces = random.sample(workspaces, num_workspaces)
        
        for workspace in user_workspaces:
            # Assign appropriate role
            if i == 0:
                role = 'admin'
            elif i <= 2:
                role = 'manager'
            else:
                role = random.choice(['member', 'contributor'])
            
            membership = WorkspaceMembershipFactory(
                user=user,
                workspace=workspace,
                role=role,
                invited_by=users[0]
            )
            user_assignments.append(membership)
        
        assignments[user.email] = user_assignments
    
    return {
        'workspaces': workspaces,
        'assignments': assignments,
        'organization': organization
    }