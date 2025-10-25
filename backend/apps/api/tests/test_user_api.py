"""
NexusPM API - User API Tests

Basic tests for user API endpoints functionality.
Enterprise testing approach for API validation.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User
from tests.factories.user_factories import UserFactory


class UserAPITestCase(APITestCase):
    """Base test case for User API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = UserFactory()
        self.admin_user = UserFactory(is_staff=True)
    
    def authenticate(self, user=None):
        """Authenticate user for API requests."""
        if user is None:
            user = self.user
        
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')


class UserRegistrationTests(UserAPITestCase):
    """Test user registration endpoints."""
    
    def test_user_registration_success(self):
        """Test successful user registration."""
        url = reverse('api:v1:users:user-register')
        data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'strongpassword123!',
            'password_confirm': 'strongpassword123!',
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        self.assertEqual(response.data['user']['email'], 'newuser@example.com')
        
        # Verify user was created in database
        self.assertTrue(
            User.objects.filter(email='newuser@example.com').exists()
        )
    
    def test_user_registration_password_mismatch(self):
        """Test registration with password mismatch."""
        url = reverse('api:v1:users:user-register')
        data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'strongpassword123!',
            'password_confirm': 'differentpassword123!',
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', response.data)
    
    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email."""
        url = reverse('api:v1:users:user-register')
        data = {
            'email': self.user.email,  # Existing user email
            'first_name': 'New',
            'last_name': 'User',
            'password': 'strongpassword123!',
            'password_confirm': 'strongpassword123!',
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)


class UserAuthenticationTests(UserAPITestCase):
    """Test user authentication endpoints."""
    
    def test_user_login_success(self):
        """Test successful user login."""
        # Set a known password
        self.user.set_password('testpassword123!')
        self.user.save()
        
        url = reverse('api:v1:users:user-login')
        data = {
            'email': self.user.email,
            'password': 'testpassword123!',
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
    
    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        url = reverse('api:v1:users:user-login')
        data = {
            'email': self.user.email,
            'password': 'wrongpassword',
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_token_refresh(self):
        """Test JWT token refresh."""
        refresh = RefreshToken.for_user(self.user)
        
        url = reverse('api:v1:users:token-refresh')
        data = {
            'refresh': str(refresh),
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)


class UserProfileTests(UserAPITestCase):
    """Test user profile endpoints."""
    
    def test_get_current_user(self):
        """Test getting current authenticated user."""
        self.authenticate()
        
        url = reverse('api:v1:users:current-user')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
    
    def test_get_current_user_unauthenticated(self):
        """Test getting current user without authentication."""
        url = reverse('api:v1:users:current-user')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_user_profile(self):
        """Test updating user profile."""
        self.authenticate()
        
        url = reverse('api:v1:users:user-detail', kwargs={'pk': self.user.pk})
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')
        self.assertEqual(response.data['last_name'], 'Name')
        
        # Verify in database
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
    
    def test_update_other_user_profile_forbidden(self):
        """Test updating another user's profile (should fail)."""
        other_user = UserFactory()
        self.authenticate()
        
        url = reverse('api:v1:users:user-detail', kwargs={'pk': other_user.pk})
        data = {
            'first_name': 'Hacked',
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UserListTests(UserAPITestCase):
    """Test user list endpoints."""
    
    def test_list_users_authenticated(self):
        """Test listing users as authenticated user."""
        self.authenticate()
        
        url = reverse('api:v1:users:user-list-create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_list_users_unauthenticated(self):
        """Test listing users without authentication."""
        url = reverse('api:v1:users:user-list-create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_user_as_admin(self):
        """Test creating user as admin."""
        self.authenticate(self.admin_user)
        
        url = reverse('api:v1:users:user-list-create')
        data = {
            'email': 'adminuser@example.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'password': 'strongpassword123!',
            'password_confirm': 'strongpassword123!',
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_create_user_as_regular_user_forbidden(self):
        """Test creating user as regular user (should fail)."""
        self.authenticate()
        
        url = reverse('api:v1:users:user-list-create')
        data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'strongpassword123!',
            'password_confirm': 'strongpassword123!',
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PasswordChangeTests(UserAPITestCase):
    """Test password change functionality."""
    
    def test_password_change_success(self):
        """Test successful password change."""
        # Set current password
        self.user.set_password('oldpassword123!')
        self.user.save()
        self.authenticate()
        
        url = reverse('api:v1:users:password-change')
        data = {
            'old_password': 'oldpassword123!',
            'new_password': 'newpassword123!',
            'new_password_confirm': 'newpassword123!',
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123!'))
    
    def test_password_change_wrong_old_password(self):
        """Test password change with wrong old password."""
        self.user.set_password('correctpassword123!')
        self.user.save()
        self.authenticate()
        
        url = reverse('api:v1:users:password-change')
        data = {
            'old_password': 'wrongpassword123!',
            'new_password': 'newpassword123!',
            'new_password_confirm': 'newpassword123!',
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('old_password', response.data)