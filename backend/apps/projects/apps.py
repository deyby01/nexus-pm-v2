from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    """
    Configuration for the Projects application.
    
    This app handles the core project management functionality:
    - Project creation, management, and lifecycle
    - Task management with dependencies and workflows
    - Team collaboration within projects
    - Time tracking and progress monitoring
    - File attachments and project assets
    
    Real-World Context:
    Projects are the primary work containers where teams organize and
    execute their initiatives. Each project contains multiple tasks,
    has assigned team members, deadlines, and success criteria.
    
    Examples:
    - Engineering: "Mobile App V3", "API Gateway Upgrade", "Database Migration"
    - Marketing: "Q4 Campaign", "Brand Redesign", "Product Launch"
    - Content: "Stranger Things S5", "Documentary Series", "Animation Project"
    
    Key Business Value:
    - Central hub for team coordination and execution
    - Progress tracking and deadline management
    - Resource allocation and workload balancing
    - Cross-project dependency management
    - ROI measurement and project analytics
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.projects'
    verbose_name = 'Projects & Tasks'
    
    def ready(self):
        """
        Called when Django starts.
        Import signal handlers for project lifecycle events.
        """
        import apps.projects.signals  # noqa