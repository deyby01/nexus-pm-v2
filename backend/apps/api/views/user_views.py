"""
NexusPM API - User Views

Enterprise-grade API views for user management.
Implements CRUD operations, authentication, and profile management.
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import login
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.users.models import User
from apps.organizations.models import OrganizationMembership
from ..serializers.user_serializers import (
    UserSerializer,
    UserDetailSerializer, 
    UserCreateSerializer,
    UserUpdateSerializer,
    PasswordChangeSerializer,
    LoginSerializer
)
from ..permissions.user_permissions import (
    IsUserOrReadOnly,
    IsAdminOrOwner,
    CanManageUsers
)


class UserListCreateView(generics.ListCreateAPIView):
    """
    List all users or create a new user.
    
    GET: Returns paginated list of users (admin only for full list)
    POST: Create new user account
    """
    queryset = User.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated, CanManageUsers]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        
        # Admin users see all users
        if self.request.user.is_staff:
            return queryset
        
        # Regular users only see users in their organizations
        # FIXED: Use direct OrganizationMembership query instead of reverse relation
        user_org_ids = OrganizationMembership.objects.filter(
            user=self.request.user,
            is_active=True
        ).values_list('organization_id', flat=True)
        
        return queryset.filter(
            organization_memberships__organization_id__in=user_org_ids,
            organization_memberships__is_active=True
        ).distinct()

    
    @extend_schema(
        summary="List users",
        description="Get paginated list of users. Admin users see all users, regular users see organization members.",
        responses={
            200: UserSerializer(many=True),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Create user",
        description="Create a new user account. Admin only.",
        request=UserCreateSerializer,
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description="Validation errors"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied"),
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a user instance.
    
    GET: Get user profile details
    PUT/PATCH: Update user profile (owner only)
    DELETE: Delete user account (admin only)
    """
    queryset = User.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated, IsUserOrReadOnly]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserDetailSerializer
    
    @extend_schema(
        summary="Get user details",
        description="Retrieve detailed user profile information",
        responses={
            200: UserDetailSerializer,
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="User not found"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Update user profile",
        description="Update user profile information. Users can only update their own profiles.",
        request=UserUpdateSerializer,
        responses={
            200: UserDetailSerializer,
            400: OpenApiResponse(description="Validation errors"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="User not found"),
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class CurrentUserView(APIView):
    """
    Get current authenticated user information.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Get current user",
        description="Get the currently authenticated user's profile information",
        responses={
            200: UserDetailSerializer,
            401: OpenApiResponse(description="Authentication required"),
        }
    )
    def get(self, request):
        """Get current user profile."""
        serializer = UserDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data)


class PasswordChangeView(APIView):
    """
    Change user password.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Change password",
        description="Change the current user's password",
        request=PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Validation errors"),
            401: OpenApiResponse(description="Authentication required"),
        }
    )
    def post(self, request):
        """Change user password."""
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Password changed successfully.'
            }, status=status.HTTP_200_OK)
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class UserRegisterView(APIView):
    """
    User registration endpoint.
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        summary="Register user",
        description="Create a new user account",
        request=UserCreateSerializer,
        responses={
            201: OpenApiResponse(description="User created successfully"),
            400: OpenApiResponse(description="Validation errors"),
        }
    )
    def post(self, request):
        """Register a new user."""
        serializer = UserCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            return Response({
                'message': 'User created successfully.',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(access_token),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view with user information.
    """
    
    @extend_schema(
        summary="Login user",
        description="Authenticate user and get JWT tokens",
        responses={
            200: OpenApiResponse(description="Login successful"),
            401: OpenApiResponse(description="Invalid credentials"),
        }
    )
    def post(self, request, *args, **kwargs):
        """Login user and return JWT tokens with user info."""
        serializer = LoginSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Log the user in
            login(request, user)
            
            return Response({
                'message': 'Login successful.',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(access_token),
                }
            }, status=status.HTTP_200_OK)
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="Logout user",
    description="Logout the current user and blacklist refresh token",
    responses={
        200: OpenApiResponse(description="Logout successful"),
        401: OpenApiResponse(description="Authentication required"),
    }
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """
    Logout user and blacklist refresh token.
    """
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({
            'message': 'Logout successful.'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Invalid token.'
        }, status=status.HTTP_400_BAD_REQUEST)