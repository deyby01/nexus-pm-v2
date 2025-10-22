from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    """
    Configuration for the Organizations application.
    
    This app handles multi-tenancy and billing for NexusPM Enterprise:
    - Organization management (multi-tenant root entities)  
    - Subscription plans and billing integration
    - Organization membership and user access control
    - Data isolation and security boundaries
    
    Key Concepts:
    - Every organization is completely isolated (no data leakage)
    - Each organization has its own subscription and billing  
    - Users can belong to multiple organizations with different roles
    - All business data is scoped to an organization
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.organizations'
    verbose_name = 'Organizations & Billing'
    
    def ready(self):
        """
        Called when Django starts.
        Import signal handlers for organization lifecycle events.
        """
        import apps.organizations.signals  # noqa