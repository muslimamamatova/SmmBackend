from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company
from apps.users.models import User, UserRole


class CompanyTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='emp@example.com', password='pass12345', name='Emp', role=UserRole.EMPLOYER)
        self.other = User.objects.create_user(email='emp2@example.com', password='pass12345', name='Emp2', role=UserRole.EMPLOYER)

    def test_create_requires_authentication(self):
        response = self.client.post('/companies/', {'name': 'Acme'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_sets_current_user_as_owner(self):
        self.client.force_authenticate(self.user)
        response = self.client.post('/companies/', {'name': 'Acme'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        company = Company.objects.get(pk=response.data['id'])
        self.assertEqual(company.user, self.user)

    def test_list_is_public(self):
        Company.objects.create(user=self.user, name='Acme')
        response = self.client.get('/companies/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_only_owner_can_update(self):
        company = Company.objects.create(user=self.user, name='Acme')
        self.client.force_authenticate(self.other)
        response = self.client.patch(f'/companies/{company.id}/', {'name': 'Hijacked'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_update(self):
        company = Company.objects.create(user=self.user, name='Acme')
        self.client.force_authenticate(self.user)
        response = self.client.patch(f'/companies/{company.id}/', {'name': 'Renamed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        company.refresh_from_db()
        self.assertEqual(company.name, 'Renamed')

    def test_me_endpoint(self):
        Company.objects.create(user=self.user, name='Acme')
        self.client.force_authenticate(self.user)
        response = self.client.get('/companies/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Acme')

    def test_me_endpoint_returns_null_when_no_company(self):
        self.client.force_authenticate(self.other)
        response = self.client.get('/companies/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data)
