from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.choices import Specialization
from apps.companies.models import Company
from apps.orders.models import Order, Review
from apps.specialists.models import SpecialistProfile
from apps.users.models import User, UserRole


class SpecialistProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='spec@example.com', password='pass12345', name='Spec', role=UserRole.SPECIALIST)
        self.other = User.objects.create_user(email='spec2@example.com', password='pass12345', name='Spec2', role=UserRole.SPECIALIST)

    def test_create_requires_authentication(self):
        response = self.client.post('/specialists/', {'specialization': Specialization.SMM_MANAGER})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_sets_current_user(self):
        self.client.force_authenticate(self.user)
        response = self.client.post('/specialists/', {'specialization': Specialization.SMM_MANAGER})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        profile = SpecialistProfile.objects.get(pk=response.data['id'])
        self.assertEqual(profile.user, self.user)

    def test_filter_by_specialization(self):
        SpecialistProfile.objects.create(user=self.user, specialization=Specialization.SMM_MANAGER)
        SpecialistProfile.objects.create(user=self.other, specialization=Specialization.COPYWRITER)
        response = self.client.get('/specialists/', {'specialization': Specialization.COPYWRITER})
        self.assertEqual(response.data['count'], 1)

    def test_only_owner_can_update(self):
        profile = SpecialistProfile.objects.create(user=self.user, specialization=Specialization.SMM_MANAGER)
        self.client.force_authenticate(self.other)
        response = self.client.patch(f'/specialists/{profile.id}/', {'bio': 'hacked'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_me_endpoint(self):
        SpecialistProfile.objects.create(user=self.user, specialization=Specialization.SMM_MANAGER)
        self.client.force_authenticate(self.user)
        response = self.client.get('/specialists/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['specialization'], Specialization.SMM_MANAGER)

    def test_reviews_endpoint_is_public(self):
        profile = SpecialistProfile.objects.create(user=self.user, specialization=Specialization.SMM_MANAGER)
        employer = User.objects.create_user(email='emp@example.com', password='pass12345', name='Emp', role=UserRole.EMPLOYER)
        company = Company.objects.create(user=employer, name='Acme')
        order = Order.objects.create(company=company, specialist=profile, price='100.00', status='completed')
        Review.objects.create(
            order=order, author=employer, recipient=self.user, rating=5,
            quality_rating=5, timeliness_rating=5, communication_rating=5, compliance_rating=5,
        )
        response = self.client.get(f'/specialists/{profile.id}/reviews/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
