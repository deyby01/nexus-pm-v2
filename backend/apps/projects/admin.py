"""
NexusPM Enterprise - Projects & Tasks Admin Configuration (FIXED)

Fixed the form field access issues for JSON fields.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q, Avg
from django.utils import timezone
from django import forms
import logging

from .models import Project, Task, ProjectMembership, TaskDependency

logger = logging.getLogger('nexuspm.projects')


class ProjectAdminForm(forms.ModelForm):
    """Custom form for Project admin with better JSON field handling"""
    class Meta:
        model = Project
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default values and help text for JSON fields
        if not self.instance.pk:  # Only for new projects
            if 'tags' in self.fields:
                self.fields['tags'].initial = []
            if 'settings' in self.fields:
                self.fields['settings'].initial = {}
        
        # Add help text safely
        if 'tags' in self.fields:
            self.fields['tags'].help_text = "Project tags (e.g., ['web', 'mobile', 'urgent']). Leave as [] for no tags."
            self.fields['tags'].required = False
        
        if 'settings' in self.fields:
            self.fields['settings'].help_text = "Project settings JSON. Leave as {} for defaults."
            self.fields['settings'].required = False


class TaskAdminForm(forms.ModelForm):
    """Custom form for Task admin with better JSON field handling"""
    class Meta:
        model = Task
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default values for JSON fields safely
        if not self.instance.pk:  # Only for new tasks
            if 'tags' in self.fields:
                self.fields['tags'].initial = []
        
        # Add help text safely
        if 'tags' in self.fields:
            self.fields['tags'].help_text = "Task tags (e.g., ['frontend', 'bug', 'urgent']). Leave as [] for no tags."
            self.fields['tags'].required = False


class ProjectMembershipInline(admin.TabularInline):
    """Inline editor for project team members"""
    model = ProjectMembership
    extra = 0
    fields = ['user', 'role', 'is_active', 'assigned_by', 'assigned_at']
    readonly_fields = ['assigned_at']


class TaskInline(admin.StackedInline):
    """Inline editor for project tasks"""
    model = Task
    form = TaskAdminForm
    extra = 0
    fields = [
        ('title', 'status', 'priority'),
        ('assignee', 'due_date'),
        ('estimated_hours', 'actual_hours'),
        'description'
    ]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Main admin interface for project management"""
    
    form = ProjectAdminForm
    
    list_display = [
        'project_icon',
        'name',
        'workspace_link',
        'status',
        'priority',
        'progress_bar',
        'project_manager_email',
        'task_count',
        'due_date',
        'days_remaining_display',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'priority', 
        'workspace__workspace_type',
        'workspace__organization',
        'created_at',
        'due_date',
    ]
    
    search_fields = [
        'name',
        'slug',
        'description',
        'workspace__name',
        'project_manager__email',
        'created_by__email'
    ]
    
    readonly_fields = [
        'id',
        'slug',
        'progress_percentage',
        'task_summary',
        'team_summary', 
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('📂 Project Information', {
            'fields': ('name', 'slug', 'description', 'workspace')
        }),
        ('🎯 Management', {
            'fields': ('status', 'priority', 'project_manager', 'created_by')
        }),
        ('📅 Timeline', {
            'fields': ('start_date', 'due_date', 'completed_at'),
        }),
        ('💰 Resources', {
            'fields': ('estimated_hours', 'budget'),
            'classes': ['collapse']
        }),
        ('📊 Progress', {
            'fields': ('progress_percentage', 'task_summary', 'team_summary'),
        }),
        ('🏷️ Organization', {
            'fields': ('tags', 'settings'),
            'classes': ['collapse'],
            'description': 'Tags: Use [] for empty list. Settings: Use {} for defaults.'
        }),
        ('📅 Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ['collapse']
        })
    )
    
    inlines = [ProjectMembershipInline, TaskInline]
    
    actions = ['mark_completed', 'archive_projects', 'calculate_progress']
    
    def get_queryset(self, request):
        """Optimize queries with annotations"""
        return super().get_queryset(request).select_related(
            'workspace', 'workspace__organization', 'project_manager', 'created_by'
        ).prefetch_related(
            'tasks', 'memberships__user'
        ).annotate(
            total_tasks=Count('tasks', filter=Q(tasks__deleted_at__isnull=True)),
            completed_tasks=Count('tasks', filter=Q(
                tasks__deleted_at__isnull=True,
                tasks__status__in=[Task.Status.COMPLETED, Task.Status.VERIFIED]
            ))
        )
    
    def project_icon(self, obj):
        """Display project with priority-based color coding"""
        priority_colors = {
            'low': '#6B7280',      
            'medium': '#3B82F6',    
            'high': '#F59E0B',     
            'urgent': '#EF4444',   
            'critical': '#DC2626'  
        }
        
        color = priority_colors.get(obj.priority, '#3B82F6')
        
        status_icons = {
            'planning': '📋',
            'active': '🚀',
            'on_hold': '⏸️',
            'completed': '✅',
            'cancelled': '❌',
            'archived': '📦'
        }
        
        icon = status_icons.get(obj.status, '📂')
        
        return format_html(
            '<div style="display:flex;align-items:center;">'
            '<div style="width:20px;height:20px;background:{};border-radius:3px;display:flex;align-items:center;justify-content:center;margin-right:8px;font-size:12px;">{}</div>'
            '</div>',
            color,
            icon
        )
    project_icon.short_description = ''
    
    def workspace_link(self, obj):
        """Link to workspace admin"""
        url = reverse('admin:workspaces_workspace_change', args=[obj.workspace.pk])
        return format_html('<a href="{}">{}</a>', url, obj.workspace.name)
    workspace_link.short_description = "Workspace"
    
    def progress_bar(self, obj):
        """Visual progress bar"""
        progress = obj.progress_percentage
        color = '#10B981' if progress >= 80 else '#F59E0B' if progress >= 50 else '#EF4444'
        
        return format_html(
            '<div style="width:100px;background:#E5E7EB;border-radius:10px;height:16px;">'
            '<div style="width:{}%;background:{};border-radius:10px;height:16px;display:flex;align-items:center;justify-content:center;color:white;font-size:10px;font-weight:bold;">{}%</div>'
            '</div>',
            progress, color, progress
        )
    progress_bar.short_description = "Progress"
    
    def project_manager_email(self, obj):
        """Link to project manager"""
        if obj.project_manager:
            url = reverse('admin:users_user_change', args=[obj.project_manager.pk])
            return format_html('<a href="{}">{}</a>', url, obj.project_manager.email)
        return "Unassigned"
    project_manager_email.short_description = "Project Manager"
    
    def task_count(self, obj):
        """Show task count with status breakdown"""
        total = getattr(obj, 'total_tasks', obj.tasks.filter(deleted_at__isnull=True).count())
        completed = getattr(obj, 'completed_tasks', obj.tasks.filter(
            deleted_at__isnull=True,
            status__in=[Task.Status.COMPLETED, Task.Status.VERIFIED]
        ).count())
        
        return f"{completed}/{total} tasks"
    task_count.short_description = "Tasks"
    
    def days_remaining_display(self, obj):
        """Show days until due date with color coding"""
        days = obj.days_remaining
        if days is None:
            return "No due date"
        
        if days < 0:
            return format_html('<span style="color: red;">Overdue by {} days</span>', abs(days))
        elif days == 0:
            return format_html('<span style="color: orange;">Due today</span>')
        elif days <= 7:
            return format_html('<span style="color: orange;">{} days left</span>', days)
        else:
            return f"{days} days left"
    days_remaining_display.short_description = "Due Date"
    
    def task_summary(self, obj):
        """Summary of project tasks"""
        total = obj.tasks.filter(deleted_at__isnull=True).count()
        if total == 0:
            return "No tasks yet"
        
        status_counts = obj.get_task_counts_by_status()
        summary_parts = []
        
        for status_data in status_counts:
            status = status_data['status']
            count = status_data['count']
            summary_parts.append(f"{status}: {count}")
        
        return " | ".join(summary_parts)
    task_summary.short_description = "Task Breakdown"
    
    def team_summary(self, obj):
        """Summary of project team"""
        active_members = obj.memberships.filter(is_active=True).count()
        return f"{active_members} team members"
    team_summary.short_description = "Team Size"


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Admin interface for task management"""
    
    form = TaskAdminForm
    
    list_display = [
        'task_icon',
        'title',
        'project_link',
        'assignee_email',
        'status',
        'priority',
        'due_date',
        'is_overdue_display',
        'estimated_vs_actual',
        'created_by_email'
    ]
    
    list_filter = [
        'status',
        'priority',
        'project__workspace',
        'created_at',
        'due_date'
    ]
    
    search_fields = [
        'title',
        'description',
        'project__name',
        'assignee__email',
        'created_by__email'
    ]
    
    readonly_fields = [
        'id',
        'is_overdue_display',
        'created_at',
        'updated_at',
        'started_at',
        'completed_at'
    ]
    
    fieldsets = (
        ('✅ Task Information', {
            'fields': ('title', 'description', 'acceptance_criteria', 'project')
        }),
        ('🎯 Management', {
            'fields': ('status', 'priority', 'assignee', 'created_by')
        }),
        ('📅 Timeline', {
            'fields': ('due_date', 'started_at', 'completed_at', 'is_overdue_display')
        }),
        ('⏰ Time Tracking', {
            'fields': ('estimated_hours', 'actual_hours'),
        }),
        ('🏷️ Tags', {
            'fields': ('tags',),
            'classes': ['collapse'],
            'description': 'Use [] for no tags, or ["tag1", "tag2"] for multiple tags.'
        }),
        ('📅 Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ['collapse']
        })
    )
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related(
            'project', 'project__workspace', 'assignee', 'created_by'
        )
    
    def task_icon(self, obj):
        """Display task with status-based color"""
        status_colors = {
            'todo': '#6B7280',         
            'in_progress': '#3B82F6',  
            'in_review': '#F59E0B',    
            'blocked': '#EF4444',      
            'completed': '#10B981',    
            'verified': '#059669'      
        }
        
        color = status_colors.get(obj.status, '#6B7280')
        
        priority_indicators = {
            'low': '●',
            'medium': '●●', 
            'high': '●●●',
            'urgent': '🔥',
        }
        
        indicator = priority_indicators.get(obj.priority, '●')
        
        return format_html(
            '<span style="color: {}; font-size: 14px;">{}</span>',
            color, indicator
        )
    task_icon.short_description = ''
    
    def project_link(self, obj):
        """Link to project admin"""
        url = reverse('admin:projects_project_change', args=[obj.project.pk])
        return format_html('<a href="{}">{}</a>', url, obj.project.name)
    project_link.short_description = "Project"
    
    def assignee_email(self, obj):
        """Link to assignee user admin"""
        if obj.assignee:
            url = reverse('admin:users_user_change', args=[obj.assignee.pk])
            return format_html('<a href="{}">{}</a>', url, obj.assignee.email)
        return "Unassigned"
    assignee_email.short_description = "Assignee"
    
    def created_by_email(self, obj):
        """Link to creator user admin"""
        url = reverse('admin:users_user_change', args=[obj.created_by.pk])
        return format_html('<a href="{}">{}</a>', url, obj.created_by.email)
    created_by_email.short_description = "Created By"
    
    def is_overdue_display(self, obj):
        """Show overdue status with visual indicator"""
        if obj.is_overdue:
            return format_html('<span style="color: red; font-weight: bold;">⚠️ OVERDUE</span>')
        elif obj.due_date:
            days_left = (obj.due_date - timezone.now()).days
            if days_left <= 1:
                return format_html('<span style="color: orange;">⏰ Due soon</span>')
        return "On track"
    is_overdue_display.short_description = "Due Status"
    
    def estimated_vs_actual(self, obj):
        """Compare estimated vs actual hours"""
        if obj.estimated_hours and obj.actual_hours:
            if obj.actual_hours > obj.estimated_hours:
                return format_html(
                    '<span style="color: red;">{:.1f}h / {:.1f}h (over)</span>',
                    obj.actual_hours, obj.estimated_hours
                )
            else:
                return format_html(
                    '<span style="color: green;">{:.1f}h / {:.1f}h</span>',
                    obj.actual_hours, obj.estimated_hours
                )
        elif obj.estimated_hours:
            return f"{obj.estimated_hours}h (estimated)"
        elif obj.actual_hours:
            return f"{obj.actual_hours}h (actual)"
        return "No time data"
    estimated_vs_actual.short_description = "Time"


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    """Admin for project team assignments"""
    
    list_display = [
        'user_email',
        'project_name',
        'workspace_name',
        'role',
        'is_active',
        'assigned_at'
    ]
    
    list_filter = [
        'role',
        'is_active',
        'assigned_at',
        'project__status'
    ]
    
    search_fields = [
        'user__email',
        'project__name',
        'project__workspace__name'
    ]
    
    def user_email(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_email.short_description = "User"
    
    def project_name(self, obj):
        url = reverse('admin:projects_project_change', args=[obj.project.pk])
        return format_html('<a href="{}">{}</a>', url, obj.project.name)
    project_name.short_description = "Project"
    
    def workspace_name(self, obj):
        return obj.project.workspace.name
    workspace_name.short_description = "Workspace"


@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    """Admin for managing task dependencies"""
    
    list_display = [
        'from_task_title',
        'dependency_type',
        'to_task_title',
        'created_by_email',
        'created_at'
    ]
    
    list_filter = [
        'dependency_type',
        'created_at'
    ]
    
    search_fields = [
        'from_task__title',
        'to_task__title',
        'from_task__project__name'
    ]
    
    def from_task_title(self, obj):
        url = reverse('admin:projects_task_change', args=[obj.from_task.pk])
        return format_html('<a href="{}">{}</a>', url, obj.from_task.title)
    from_task_title.short_description = "From Task"
    
    def to_task_title(self, obj):
        url = reverse('admin:projects_task_change', args=[obj.to_task.pk])
        return format_html('<a href="{}">{}</a>', url, obj.to_task.title)
    to_task_title.short_description = "To Task"
    
    def created_by_email(self, obj):
        if obj.created_by:
            url = reverse('admin:users_user_change', args=[obj.created_by.pk])
            return format_html('<a href="{}">{}</a>', url, obj.created_by.email)
        return "System"
    created_by_email.short_description = "Created By"