from django.apps import AppConfig


class WorkspacesConfig(AppConfig):
    """
    Configuration for the Workspaces application.
    
    This app handles team-level organization within companies:
    - Workspace management (team containers within organizations)
    - Project grouping and team collaboration boundaries
    - Workspace-level permissions and access control  
    - Team-specific settings and customization
    
    Real-World Context:
    In enterprise environments, workspaces represent departments, teams, 
    or project groups that need isolation within the same organization.
    
    Examples:
    - Netflix Org → Content Team Workspace, Engineering Workspace
    - Startup Org → Frontend Team Workspace, Backend Team Workspace
    - Agency Org → Client A Workspace, Client B Workspace
    
    Key Benefits:
    - Granular access control (team-level permissions)
    - Project organization and categorization
    - Team-specific workflows and settings
    - Resource allocation and usage tracking per team
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.workspaces'
    verbose_name = 'Workspaces & Teams'
    
    def ready(self):
        """
        Called when Django starts.
        Import signal handlers for workspace lifecycle events.
        """
        import apps.workspaces.signals  # noqa