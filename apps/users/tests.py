from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User, UserRole


class AuthTests(APITestCase):
    def test_register_creates_user_and_returns_tokens(self):
        response = self.client.post(reverse('auth-register'), {
            'email': 'specialist@example.com',
            'password': 'StrongPass123',
            'name': 'Anna',
            'role': UserRole.SPECIALIST,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(User.objects.filter(email='specialist@example.com').exists())

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(email='dup@example.com', password='StrongPass123', name='Dup', role=UserRole.EMPLOYER)
        response = self.client.post(reverse('auth-register'), {
            'email': 'dup@example.com',
            'password': 'StrongPass123',
            'name': 'Dup2',
            'role': UserRole.EMPLOYER,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_returns_tokens(self):
        User.objects.create_user(email='login@example.com', password='StrongPass123', name='Login', role=UserRole.EMPLOYER)
        response = self.client.post(reverse('auth-login'), {
            'email': 'login@example.com',
            'password': 'StrongPass123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        user = User.objects.create_user(email='me@example.com', password='StrongPass123', name='Me', role=UserRole.EMPLOYER)
        self.client.force_authenticate(user)
        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'me@example.com')

    def test_logout_blacklists_refresh_token(self):
        user = User.objects.create_user(email='out@example.com', password='StrongPass123', name='Out', role=UserRole.EMPLOYER)
        login = self.client.post(reverse('auth-login'), {'email': 'out@example.com', 'password': 'StrongPass123'})
        refresh = login.data['refresh']

        self.client.force_authenticate(user)
        response = self.client.post(reverse('auth-logout'), {'refresh': refresh})
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        refresh_response = self.client.post(reverse('auth-refresh'), {'refresh': refresh})
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
