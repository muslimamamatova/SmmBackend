from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.choices import Specialization
from apps.portfolio.models import Portfolio
from apps.specialists.models import SpecialistProfile
from apps.users.models import User, UserRole


class PortfolioTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='pspec@example.com', password='pass12345', name='PSpec', role=UserRole.SPECIALIST)
        self.profile = SpecialistProfile.objects.create(user=self.user, specialization=Specialization.CONTENT_CREATOR)
        self.other = User.objects.create_user(email='pspec2@example.com', password='pass12345', name='PSpec2', role=UserRole.SPECIALIST)
        self.other_profile = SpecialistProfile.objects.create(user=self.other, specialization=Specialization.CONTENT_CREATOR)

    def test_create_requires_authentication(self):
        response = self.client.post('/portfolio/', {'title': 'Case', 'category': Specialization.CONTENT_CREATOR})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_attaches_current_specialist(self):
        self.client.force_authenticate(self.user)
        response = self.client.post('/portfolio/', {'title': 'Case', 'category': Specialization.CONTENT_CREATOR})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = Portfolio.objects.get(pk=response.data['id'])
        self.assertEqual(item.specialist, self.profile)

    def test_retrieve_increments_views(self):
        item = Portfolio.objects.create(specialist=self.profile, title='Case', category=Specialization.CONTENT_CREATOR)
        self.client.get(f'/portfolio/{item.id}/')
        self.client.get(f'/portfolio/{item.id}/')
        item.refresh_from_db()
        self.assertEqual(item.views_count, 2)

    def test_like_toggle(self):
        item = Portfolio.objects.create(specialist=self.other_profile, title='Case', category=Specialization.CONTENT_CREATOR)
        self.client.force_authenticate(self.user)

        like_response = self.client.post(f'/portfolio/{item.id}/like/')
        self.assertEqual(like_response.status_code, status.HTTP_200_OK)
        self.assertTrue(like_response.data['liked'])
        item.refresh_from_db()
        self.assertEqual(item.likes_count, 1)

        unlike_response = self.client.post(f'/portfolio/{item.id}/like/')
        self.assertFalse(unlike_response.data['liked'])
        item.refresh_from_db()
        self.assertEqual(item.likes_count, 0)

    def test_only_owner_can_edit(self):
        item = Portfolio.objects.create(specialist=self.other_profile, title='Case', category=Specialization.CONTENT_CREATOR)
        self.client.force_authenticate(self.user)
        response = self.client.patch(f'/portfolio/{item.id}/', {'title': 'Hijacked'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
