from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.choices import ApplicationStatus, Specialization
from apps.companies.models import Company
from apps.jobs.models import Application, Job
from apps.specialists.models import SpecialistProfile
from apps.users.models import User, UserRole


class JobTests(APITestCase):
    def setUp(self):
        self.employer = User.objects.create_user(email='emp@example.com', password='pass12345', name='Emp', role=UserRole.EMPLOYER)
        self.company = Company.objects.create(user=self.employer, name='Acme')
        self.other_employer = User.objects.create_user(email='emp2@example.com', password='pass12345', name='Emp2', role=UserRole.EMPLOYER)

    def test_create_requires_authentication(self):
        response = self.client.post('/jobs/', {'title': 'SMM job', 'description': 'desc', 'category': Specialization.SMM_MANAGER})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_attaches_current_company(self):
        self.client.force_authenticate(self.employer)
        response = self.client.post('/jobs/', {'title': 'SMM job', 'description': 'desc', 'category': Specialization.SMM_MANAGER})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        job = Job.objects.get(pk=response.data['id'])
        self.assertEqual(job.company, self.company)

    def test_filter_by_category(self):
        Job.objects.create(company=self.company, title='A', description='d', category=Specialization.SMM_MANAGER)
        Job.objects.create(company=self.company, title='B', description='d', category=Specialization.COPYWRITER)
        response = self.client.get('/jobs/', {'category': Specialization.COPYWRITER})
        self.assertEqual(response.data['count'], 1)

    def test_only_owner_company_can_update(self):
        job = Job.objects.create(company=self.company, title='A', description='d', category=Specialization.SMM_MANAGER)
        self.client.force_authenticate(self.other_employer)
        response = self.client.patch(f'/jobs/{job.id}/', {'title': 'Hijacked'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ApplicationTests(APITestCase):
    def setUp(self):
        self.employer = User.objects.create_user(email='emp@example.com', password='pass12345', name='Emp', role=UserRole.EMPLOYER)
        self.company = Company.objects.create(user=self.employer, name='Acme')
        self.job = Job.objects.create(company=self.company, title='SMM job', description='d', category=Specialization.SMM_MANAGER)

        self.specialist_user = User.objects.create_user(email='spec@example.com', password='pass12345', name='Spec', role=UserRole.SPECIALIST)
        self.specialist = SpecialistProfile.objects.create(user=self.specialist_user, specialization=Specialization.SMM_MANAGER)

    def test_specialist_can_apply(self):
        self.client.force_authenticate(self.specialist_user)
        response = self.client.post(f'/jobs/{self.job.id}/applications/', {'message': 'Hi', 'price': '100.00'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Application.objects.filter(job=self.job, specialist=self.specialist).exists())

    def test_employer_can_list_applications_for_own_job(self):
        Application.objects.create(job=self.job, specialist=self.specialist, message='Hi')
        self.client.force_authenticate(self.employer)
        response = self.client.get(f'/jobs/{self.job.id}/applications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_other_employer_cannot_list_applications(self):
        Application.objects.create(job=self.job, specialist=self.specialist, message='Hi')
        other = User.objects.create_user(email='other@example.com', password='pass12345', name='Other', role=UserRole.EMPLOYER)
        self.client.force_authenticate(other)
        response = self.client.get(f'/jobs/{self.job.id}/applications/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employer_can_accept_application(self):
        application = Application.objects.create(job=self.job, specialist=self.specialist, message='Hi')
        self.client.force_authenticate(self.employer)
        response = self.client.post(f'/applications/{application.id}/accept/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.ACCEPTED)

    def test_specialist_cannot_accept_own_application(self):
        application = Application.objects.create(job=self.job, specialist=self.specialist, message='Hi')
        self.client.force_authenticate(self.specialist_user)
        response = self.client.post(f'/applications/{application.id}/accept/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_specialist_can_withdraw(self):
        application = Application.objects.create(job=self.job, specialist=self.specialist, message='Hi')
        self.client.force_authenticate(self.specialist_user)
        response = self.client.post(f'/applications/{application.id}/withdraw/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.WITHDRAWN)

    def test_application_list_scoped_to_participants(self):
        application = Application.objects.create(job=self.job, specialist=self.specialist, message='Hi')
        stranger = User.objects.create_user(email='stranger@example.com', password='pass12345', name='Stranger', role=UserRole.EMPLOYER)
        self.client.force_authenticate(stranger)
        response = self.client.get('/applications/')
        self.assertEqual(response.data['count'], 0)

        self.client.force_authenticate(self.specialist_user)
        response = self.client.get('/applications/')
        self.assertEqual(response.data['count'], 1)
