"""
NexusPM API - User Serializers

Enterprise-grade user serialization for REST API endpoints.
Handles user data transformation, validation, and nested relationships.
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.users.models import User
from apps.organizations.models import OrganizationMembership


class UserSerializer(serializers.ModelSerializer):
    """
    Standard user serializer for profile information.
    Used for displaying user data across the platform.
    """
    full_name = serializers.SerializerMethodField()
    organizations_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'email', 
            'first_name',
            'last_name',
            'full_name',           # SerializerMethodField
            'is_active',
            'date_joined',
            'last_login',
            'organizations_count', # SerializerMethodField
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
    
    def get_full_name(self, obj):
        """Get user's full name."""
        return f"{obj.first_name} {obj.last_name}".strip()
    
    def get_organizations_count(self, obj):
        """Get count of organizations user belongs to."""
        return OrganizationMembership.objects.filter(
            user=obj, 
            is_active=True
        ).count()


class UserDetailSerializer(UserSerializer):
    """
    Detailed user serializer with additional information.
    Used for user profile pages and detailed views.
    """
    organizations = serializers.SerializerMethodField()
    
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + [
            'organizations',
        ]
    
    def get_organizations(self, obj):
        """Get user's organization memberships."""
        memberships = OrganizationMembership.objects.filter(
            user=obj, 
            is_active=True
        ).select_related('organization')
        
        return [{
            'id': membership.organization.id,
            'name': membership.organization.name,
            'slug': membership.organization.slug,
            'role': membership.role,
            'joined_at': membership.created_at
        } for membership in memberships]


class UserCreateSerializer(serializers.ModelSerializer):
    """
    User creation serializer with password validation.
    Used for user registration endpoints.
    """
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'email',
            'first_name', 
            'last_name',
            'password',
            'password_confirm',
        ]
    
    def validate_email(self, value):
        """Validate email uniqueness."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value
    
    def validate_password(self, value):
        """Validate password strength."""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Password confirmation does not match.'
            })
        return attrs
    
    def create(self, validated_data):
        """Create user with validated data."""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    User update serializer for profile modifications.
    Used for user profile update endpoints.
    """
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
        ]
    
    def update(self, instance, validated_data):
        """Update user profile information."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class PasswordChangeSerializer(serializers.Serializer):
    """
    Password change serializer for authenticated users.
    Used for password change endpoints.
    """
    old_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate_old_password(self, value):
        """Validate current password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                'Current password is incorrect.'
            )
        return value
    
    def validate_new_password(self, value):
        """Validate new password strength."""
        try:
            validate_password(value, user=self.context['request'].user)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, attrs):
        """Validate new password confirmation."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Password confirmation does not match.'
            })
        return attrs
    
    def save(self):
        """Update user password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """
    User login serializer for authentication.
    Used for login endpoints with JWT token generation.
    """
    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate user credentials."""
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError(
                    'Unable to log in with provided credentials.'
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    'User account is disabled.'
                )
            
            attrs['user'] = user
            return attrs
        
        raise serializers.ValidationError(
            'Must include "email" and "password".'
        )