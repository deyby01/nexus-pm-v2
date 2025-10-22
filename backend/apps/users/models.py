"""
NexusPM Enterprise - User Models

This module contains the core user model and related entities for the
NexusPM Enterprise platform. Following Clean Architecture principles,
this model serves as the foundation for authentication, authorization,
and user management across the entire platform.

Architecture:
- Custom User model inheriting from AbstractUser
- UUID primary keys for security and distribution
- Email-based authentication (no usernames)
- Rich user profiles with preferences
- Soft delete capability for data retention
- Timezone-aware operations
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom manager for User model with enterprise-grade query methods.
    
    Provides convenient methods for common user operations while
    maintaining performance and security best practices.
    """
    
    def get_queryset(self):
        """Exclude soft-deleted users by default"""
        return super().get_queryset().filter(deleted_at__isnull=True)
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_email_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)
    
    def active_users(self):
        """Get all active, non-deleted users"""
        return self.get_queryset().filter(is_active=True)
    
    def verified_users(self):
        """Get all users with verified email addresses"""
        return self.get_queryset().filter(is_email_verified=True)
    
    def by_organization(self, organization_id):
        """Get users belonging to a specific organization"""
        return self.get_queryset().filter(
            memberships__workspace__organization_id=organization_id
        ).distinct()
    
    def search(self, query):
        """
        Search users by name or email.
        Uses database indexes for performance.
        """
        return self.get_queryset().filter(
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query) |
            models.Q(email__icontains=query)
        )
    
    def with_deleted(self):
        """Include soft-deleted users in queries (for admin/audit purposes)"""
        return super().get_queryset()


class User(AbstractUser):
    """
    Custom User model for NexusPM Enterprise.
    
    Key Features:
    - Email-based authentication (no username required)
    - UUID primary key for security and scalability
    - Rich user profile with preferences
    - Timezone support for global users
    - Soft delete for data retention
    - Avatar support for better UX
    
    Business Rules:
    - Email must be unique across the platform
    - Users can belong to multiple organizations
    - Profile data is optional but recommended for better UX
    - Deleted users retain audit trail via soft delete
    """
    
    # Primary identification
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for this user"
    )
    
    # Authentication fields (email-based)
    email = models.EmailField(
        unique=True,
        help_text="Primary email address used for authentication"
    )
    
    # Profile information
    first_name = models.CharField(
        max_length=50,
        help_text="User's first name"
    )
    last_name = models.CharField(
        max_length=50, 
        help_text="User's last name"
    )
    
    # Avatar and visual identity
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/',
        null=True,
        blank=True,
        help_text="User's profile picture"
    )
    
    # User preferences and localization
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="User's preferred timezone for dates and times"
    )
    language = models.CharField(
        max_length=10,
        default='en',
        choices=[
            ('en', 'English'),
            ('es', 'Español'),
            ('fr', 'Français'),
            ('de', 'Deutsch'),
            ('pt', 'Português'),
        ],
        help_text="User's preferred language for the interface"
    )
    date_format = models.CharField(
        max_length=20,
        default='YYYY-MM-DD',
        choices=[
            ('YYYY-MM-DD', '2025-10-22'),
            ('MM/DD/YYYY', '10/22/2025'),
            ('DD/MM/YYYY', '22/10/2025'),
            ('DD-MM-YYYY', '22-10-2025'),
        ],
        help_text="User's preferred date format"
    )
    
    # Professional information
    job_title = models.CharField(
        max_length=100,
        blank=True,
        help_text="User's job title or role"
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be in format: '+999999999'. Up to 15 digits allowed."
        )],
        help_text="User's contact phone number"
    )
    
    # Account status and verification
    is_email_verified = models.BooleanField(
        default=False,
        help_text="Whether the user's email address has been verified"
    )
    email_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the email was verified"
    )
    
    # Security and tracking
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the user's last login"
    )
    failed_login_attempts = models.PositiveSmallIntegerField(
        default=0,
        help_text="Number of consecutive failed login attempts"
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Account locked until this datetime due to failed logins"
    )
    
    # Timestamps (following enterprise audit patterns)
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this user account was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this user account was last updated"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this user account was soft deleted"
    )
    
    # Override default fields from AbstractUser
    username = models.CharField(
        max_length=150,
        unique=True,
        help_text="Internal username (auto-generated from email)"
    )
    
    # Custom manager
    objects = UserManager()
    
    # Configure email as the login field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'users_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
            models.Index(fields=['last_login']),
            models.Index(fields=['is_active', 'deleted_at']),
        ]
    
    def __str__(self):
        """String representation prioritizing full name over email"""
        full_name = self.get_full_name()
        return full_name if full_name.strip() else self.email
    
    def save(self, *args, **kwargs):
        """
        Override save to auto-generate username from email.
        This maintains AbstractUser compatibility while using email auth.
        """
        if not self.username:
            # Generate username from email (before @)
            base_username = self.email.split('@')[0]
            username = base_username
            counter = 1
            
            # Ensure username uniqueness
            while User.objects.filter(username=username).exclude(id=self.id).exists():
                username = f"{base_username}{counter}"
                counter += 1
                
            self.username = username
        
        super().save(*args, **kwargs)
    
    # Business logic methods
    def get_full_name(self):
        """
        Return the user's full name with proper spacing.
        Override to handle edge cases better.
        """
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else ""
    
    def get_short_name(self):
        """Return the user's first name"""
        return self.first_name
    
    def is_account_locked(self):
        """Check if account is temporarily locked due to failed login attempts"""
        if self.locked_until:
            return timezone.now() < self.locked_until
        return False
    
    def unlock_account(self):
        """Unlock the account and reset failed login attempts"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])
    
    def soft_delete(self):
        """
        Soft delete the user account.
        This preserves audit trails while making the account inaccessible.
        """
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=['deleted_at', 'is_active'])
    
    def restore(self):
        """Restore a soft-deleted user account"""
        self.deleted_at = None
        self.is_active = True
        self.save(update_fields=['deleted_at', 'is_active'])
    
    @property
    def display_name(self):
        """
        Get the best display name for the user.
        Priority: Full Name > Email > Username
        """
        full_name = self.get_full_name()
        if full_name:
            return full_name
        return self.email
    
    @property
    def initials(self):
        """Get user initials for avatar placeholders"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return self.first_name[0].upper()
        else:
            return self.email[0].upper()