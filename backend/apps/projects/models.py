"""
NexusPM Enterprise - Projects & Tasks Models (FIXED)

Fixed the ManyToMany through_fields issue for Project.team_members.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

User = get_user_model()


class ProjectMembership(models.Model):
    """
    Represents a User's membership in a specific Project.
    
    Provides project-level access control and role management.
    This is more granular than workspace membership.
    """
    
    class Role(models.TextChoices):
        """Project-level roles"""
        LEAD = 'lead', 'Project Lead'      # Project leadership
        MEMBER = 'member', 'Team Member'   # Standard project access  
        REVIEWER = 'reviewer', 'Reviewer'  # Review and approval only
        OBSERVER = 'observer', 'Observer'  # Read-only project access
    
    # Relationships
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='project_memberships',
        help_text="User assigned to this project"
    )
    project = models.ForeignKey(
        'Project',  # Forward reference
        on_delete=models.CASCADE,
        related_name='memberships',
        help_text="Project the user is assigned to"
    )
    
    # Role and status
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        help_text="User's role in this specific project"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this project assignment is active"
    )
    
    # Timeline
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_assignments_made',
        help_text="Who assigned this user to the project"
    )
    
    class Meta:
        db_table = 'projects_membership'
        verbose_name = 'Project Membership'
        verbose_name_plural = 'Project Memberships'  
        unique_together = ['user', 'project']
        indexes = [
            models.Index(fields=['project', 'role']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} → {self.project.name} ({self.role})"


class Project(models.Model):
    """
    Primary work container within workspaces.
    
    Projects represent significant initiatives, features, campaigns,
    or other organized work efforts that require multiple tasks and
    team coordination to complete successfully.
    """
    
    class Status(models.TextChoices):
        """Project lifecycle states"""
        PLANNING = 'planning', 'Planning'         
        ACTIVE = 'active', 'Active'               
        ON_HOLD = 'on_hold', 'On Hold'           
        COMPLETED = 'completed', 'Completed'      
        CANCELLED = 'cancelled', 'Cancelled'      
        ARCHIVED = 'archived', 'Archived'        
    
    class Priority(models.TextChoices):
        """Project priority levels"""
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'  
        URGENT = 'urgent', 'Urgent'
        CRITICAL = 'critical', 'Critical'
    
    # Primary identification
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this project"
    )
    
    # Basic information
    name = models.CharField(
        max_length=200,
        help_text="Project name (e.g., 'Mobile App V3', 'Q4 Marketing Campaign')"
    )
    slug = models.SlugField(
        max_length=200,
        help_text="URL-friendly identifier within the workspace"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of project objectives and scope"
    )
    
    # Hierarchical relationships
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='projects',
        help_text="Workspace this project belongs to"
    )
    
    # Project management fields
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING,
        help_text="Current status of the project"
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text="Project priority level for resource allocation"
    )
    
    # Ownership and assignment
    project_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_projects',
        help_text="User responsible for managing this project"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_projects',
        help_text="User who created this project"
    )
    
    # Timeline and scheduling
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Planned or actual project start date"
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Target completion date for the project"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the project was marked as completed"
    )
    
    # Budget and resource tracking
    estimated_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Estimated total hours for project completion"
    )
    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Project budget in USD"
    )
    
    # Progress tracking (calculated fields)
    progress_percentage = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Project completion percentage (0-100)"
    )
    
    # Team and collaboration - FIXED: specify through_fields
    team_members = models.ManyToManyField(
        User,
        through='ProjectMembership',
        through_fields=('project', 'user'),  # ← FIX: specify the exact fields
        related_name='projects',
        help_text="Users assigned to work on this project"
    )
    
    # Metadata and organization
    tags = models.JSONField(
        default=list,
        help_text="Project tags for categorization and filtering"
    )
    settings = models.JSONField(
        default=dict,
        help_text="Project-specific settings and preferences"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'projects_project'
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
        unique_together = ['workspace', 'slug']  # Slug unique within workspace
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['project_manager']),
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.workspace.name} → {self.name}"
    
    def save(self, *args, **kwargs):
        """Auto-generate slug and validate business rules"""
        # Auto-generate slug from name if not provided
        if not self.slug:
            self.slug = slugify(self.name)
            
            # Ensure slug uniqueness within workspace
            counter = 1
            original_slug = self.slug
            while Project.objects.filter(
                workspace=self.workspace,
                slug=self.slug
            ).exclude(id=self.id).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Enterprise validation for business rules"""
        super().clean()
        
        # Rule 1: Check workspace project limits
        if not self.pk:  # Only for new projects
            org_limits = self.workspace.organization.get_usage_limits()
            current_projects = self.workspace.projects.filter(deleted_at__isnull=True).count()
            
            if current_projects >= org_limits['max_projects_per_workspace']:
                raise ValidationError(
                    f"Workspace '{self.workspace.name}' has reached its project limit "
                    f"of {org_limits['max_projects_per_workspace']}. "
                    f"Upgrade subscription or archive unused projects."
                )
        
        # Rule 2: Dates validation
        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValidationError("Start date cannot be after due date.")
    
    # Business logic methods
    @property
    def is_overdue(self):
        """Check if project is past its due date"""
        if not self.due_date:
            return False
        return timezone.now().date() > self.due_date and self.status not in [
            self.Status.COMPLETED, self.Status.CANCELLED, self.Status.ARCHIVED
        ]
    
    @property
    def days_remaining(self):
        """Calculate days until due date"""
        if not self.due_date:
            return None
        delta = self.due_date - timezone.now().date()
        return delta.days
    
    def get_active_tasks(self):
        """Get all active tasks for this project"""
        return self.tasks.filter(deleted_at__isnull=True)
    
    def get_task_counts_by_status(self):
        """Get task counts grouped by status for progress tracking"""
        return self.get_active_tasks().values('status').annotate(
            count=models.Count('id')
        )
    
    def calculate_progress_percentage(self):
        """Calculate project progress based on completed tasks"""
        active_tasks = self.get_active_tasks()
        total_tasks = active_tasks.count()
        
        if total_tasks == 0:
            return 0
        
        completed_tasks = active_tasks.filter(
            status__in=[Task.Status.COMPLETED, Task.Status.VERIFIED]
        ).count()
        
        progress = round((completed_tasks / total_tasks) * 100)
        
        # Update the cached field
        if self.progress_percentage != progress:
            self.progress_percentage = progress
            self.save(update_fields=['progress_percentage'])
        
        return progress
    
    def can_user_access(self, user):
        """Check if user can access this project"""
        return self.workspace.can_user_access(user)
    
    def soft_delete(self):
        """Soft delete project and related tasks"""
        self.deleted_at = timezone.now()
        self.status = self.Status.ARCHIVED
        self.save(update_fields=['deleted_at', 'status'])
        
        # Soft delete all tasks in this project
        self.tasks.filter(deleted_at__isnull=True).update(
            deleted_at=timezone.now()
        )


class Task(models.Model):
    """
    Individual work items within projects.
    
    Tasks represent the atomic units of work that team members
    complete to achieve project objectives.
    """
    
    class Status(models.TextChoices):
        """Task lifecycle states for Kanban-style workflows"""
        TODO = 'todo', 'To Do'                    
        IN_PROGRESS = 'in_progress', 'In Progress' 
        IN_REVIEW = 'in_review', 'In Review'      
        BLOCKED = 'blocked', 'Blocked'            
        COMPLETED = 'completed', 'Completed'      
        VERIFIED = 'verified', 'Verified'         
    
    class Priority(models.TextChoices):
        """Task priority levels for work prioritization"""
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'
    
    # Primary identification
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this task"
    )
    
    # Basic information
    title = models.CharField(
        max_length=200,
        help_text="Brief, descriptive task title"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the work to be done"
    )
    acceptance_criteria = models.TextField(
        blank=True,
        help_text="Specific criteria that define when this task is complete"
    )
    
    # Hierarchical relationships
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text="Project this task belongs to"
    )
    
    # Task management
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.TODO,
        help_text="Current status of the task"
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text="Task priority level"
    )
    
    # Assignment and ownership
    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        help_text="User assigned to complete this task"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_tasks',
        help_text="User who created this task"
    )
    
    # Timeline and scheduling
    due_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this task should be completed"
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When work on this task actually began"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this task was marked as completed"
    )
    
    # Time and effort tracking
    estimated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated hours required to complete this task"
    )
    actual_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Actual hours spent on this task"
    )
    
    # Task dependencies
    depends_on = models.ManyToManyField(
        'self',
        through='TaskDependency',
        symmetrical=False,
        related_name='dependent_tasks',
        help_text="Tasks that must be completed before this task can start"
    )
    
    # Metadata
    tags = models.JSONField(
        default=list,
        help_text="Task tags for categorization and filtering"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'projects_task'
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['assignee', 'status']),
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-priority', 'due_date', 'created_at']
    
    def __str__(self):
        return f"{self.project.name} → {self.title}"
    
    def save(self, *args, **kwargs):
        """Override save to update timestamps and trigger calculations"""
        # Update status timestamps
        if self.status == self.Status.IN_PROGRESS and not self.started_at:
            self.started_at = timezone.now()
        elif self.status in [self.Status.COMPLETED, self.Status.VERIFIED] and not self.completed_at:
            self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    # Business logic methods
    @property
    def is_overdue(self):
        """Check if task is past its due date"""
        if not self.due_date:
            return False
        return timezone.now() > self.due_date and self.status not in [
            self.Status.COMPLETED, self.Status.VERIFIED
        ]
    
    @property
    def is_blocked(self):
        """Check if task is blocked by dependencies"""
        if self.status == self.Status.BLOCKED:
            return True
        
        # Check if any dependencies are incomplete
        blocking_tasks = self.depends_on.filter(
            deleted_at__isnull=True
        ).exclude(
            status__in=[self.Status.COMPLETED, self.Status.VERIFIED]
        )
        
        return blocking_tasks.exists()
    
    def get_blocking_tasks(self):
        """Get tasks that are blocking this task"""
        return self.depends_on.filter(
            deleted_at__isnull=True
        ).exclude(
            status__in=[self.Status.COMPLETED, self.Status.VERIFIED]
        )
    
    def can_start(self):
        """Check if task can be started (no blocking dependencies)"""
        return not self.is_blocked
    
    def soft_delete(self):
        """Soft delete task"""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])


class TaskDependency(models.Model):
    """
    Represents blocking relationships between tasks.
    
    Critical for project flow management - ensures tasks are
    completed in the correct order and identifies bottlenecks.
    """
    
    class DependencyType(models.TextChoices):
        """Types of task dependencies"""
        BLOCKS = 'blocks', 'Blocks'                    
        SUBTASK = 'subtask', 'Subtask'                
        RELATED = 'related', 'Related'                 
    
    # Relationships
    from_task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='outgoing_dependencies',
        help_text="Task that creates the dependency"
    )
    to_task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='incoming_dependencies', 
        help_text="Task that depends on the from_task"
    )
    
    # Dependency details
    dependency_type = models.CharField(
        max_length=10,
        choices=DependencyType.choices,
        default=DependencyType.BLOCKS,
        help_text="Type of dependency relationship"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who created this dependency"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'projects_task_dependency'
        verbose_name = 'Task Dependency'
        verbose_name_plural = 'Task Dependencies'
        unique_together = ['from_task', 'to_task', 'dependency_type']
    
    def __str__(self):
        return f"{self.from_task.title} {self.dependency_type} {self.to_task.title}"
    
    def clean(self):
        """Prevent circular dependencies"""
        super().clean()
        
        # Rule 1: Task cannot depend on itself
        if self.from_task == self.to_task:
            raise ValidationError("Task cannot depend on itself.")
        
        # Rule 2: Both tasks must be in same project
        if hasattr(self, 'from_task') and hasattr(self, 'to_task'):
            if self.from_task.project != self.to_task.project:
                raise ValidationError(
                    "Task dependencies must be within the same project."
                )