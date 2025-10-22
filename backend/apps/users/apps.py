from django.apps import AppConfig


class UsersConfig(AppConfig):
    """
    Configuration for the Users application.
    
    This app handles all user-related functionality including:
    - Custom user model with email authentication
    - User profiles and preferences
    - User management and administration
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'User Management'
    
    def ready(self):
        """
        Called when Django starts.
        Import signal handlers here.
        """
        import apps.users.signals  # noqa