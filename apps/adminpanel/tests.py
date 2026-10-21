from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.choices import ComplaintReason, ComplaintTargetType, Specialization
from apps.common.models import Complaint
from apps.companies.models import Company
from apps.jobs.models import Job
from apps.specialists.models import SpecialistProfile
from apps.users.models import User, UserRole, UserStatus


class AdminAccessTests(APITestCase):
    def setUp(self):
        self.regular_user = User.objects.create_user(email='u@example.com', password='pass12345', name='U', role=UserRole.EMPLOYER)
        self.admin = User.objects.create_user(email='admin@example.com', password='pass12345', name='Admin', role=UserRole.ADMIN)

    def test_non_admin_cannot_access_dashboard(self):
        self.client.force_authenticate(self.regular_user)
        response = self.client.get('/api/v1/admin/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_access_dashboard(self):
        response = self.client.get('/api/v1/admin/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_access_dashboard(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/v1/admin/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('users', response.data)
        self.assertIn('orders', response.data)
        self.assertIn('turnover', response.data)


class AdminUserManagementTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email='admin@example.com', password='pass12345', name='Admin', role=UserRole.ADMIN)
        self.target = User.objects.create_user(email='target@example.com', password='pass12345', name='Target', role=UserRole.EMPLOYER)

    def test_non_admin_cannot_list_users(self):
        self.client.force_authenticate(self.target)
        response = self.client.get('/api/v1/admin/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_users(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/v1/admin/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 2)

    def test_admin_can_block_and_unblock_user(self):
        self.client.force_authenticate(self.admin)
        block_response = self.client.post(f'/api/v1/admin/users/{self.target.id}/block/')
        self.assertEqual(block_response.status_code, status.HTTP_200_OK)
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, UserStatus.BLOCKED)

        unblock_response = self.client.post(f'/api/v1/admin/users/{self.target.id}/unblock/')
        self.assertEqual(unblock_response.status_code, status.HTTP_200_OK)
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, UserStatus.ACTIVE)


class AdminSpecialistVerificationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email='admin@example.com', password='pass12345', name='Admin', role=UserRole.ADMIN)
        self.spec_user = User.objects.create_user(email='spec@example.com', password='pass12345', name='Spec', role=UserRole.SPECIALIST)
        self.profile = SpecialistProfile.objects.create(user=self.spec_user, specialization=Specialization.SMM_MANAGER)

    def test_non_admin_cannot_verify(self):
        self.client.force_authenticate(self.spec_user)
        response = self.client.post(f'/specialists/{self.profile.id}/verify/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_verify_specialist(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(f'/specialists/{self.profile.id}/verify/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.verified)


class AdminModerationBypassTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email='admin@example.com', password='pass12345', name='Admin', role=UserRole.ADMIN)
        self.employer = User.objects.create_user(email='emp@example.com', password='pass12345', name='Emp', role=UserRole.EMPLOYER)
        self.company = Company.objects.create(user=self.employer, name='Acme')
        self.job = Job.objects.create(company=self.company, title='A', description='d', category=Specialization.SMM_MANAGER)

    def test_admin_can_moderate_job(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(f'/jobs/{self.job.id}/moderate/', {'status': 'closed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'closed')

    def test_non_admin_cannot_moderate_job(self):
        self.client.force_authenticate(self.employer)
        response = self.client.post(f'/jobs/{self.job.id}/moderate/', {'status': 'closed'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_any_job(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f'/jobs/{self.job.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ComplaintTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email='admin@example.com', password='pass12345', name='Admin', role=UserRole.ADMIN)
        self.reporter = User.objects.create_user(email='rep@example.com', password='pass12345', name='Rep', role=UserRole.EMPLOYER)

    def test_user_can_create_complaint(self):
        self.client.force_authenticate(self.reporter)
        response = self.client.post('/complaints/', {
            'target_type': ComplaintTargetType.JOB, 'target_id': 1, 'reason': ComplaintReason.SPAM, 'comment': 'spam job',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Complaint.objects.get().reporter, self.reporter)

    def test_regular_user_only_sees_own_complaints(self):
        Complaint.objects.create(reporter=self.admin, target_type=ComplaintTargetType.JOB, target_id=1, reason=ComplaintReason.SPAM)
        self.client.force_authenticate(self.reporter)
        response = self.client.get('/complaints/')
        self.assertEqual(response.data['count'], 0)

    def test_non_admin_cannot_access_admin_complaints(self):
        self.client.force_authenticate(self.reporter)
        response = self.client.get('/api/v1/admin/complaints/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_resolve_complaint(self):
        complaint = Complaint.objects.create(
            reporter=self.reporter, target_type=ComplaintTargetType.JOB, target_id=1, reason=ComplaintReason.SPAM,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post(f'/api/v1/admin/complaints/{complaint.id}/resolve/', {'moderator_comment': 'handled'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, 'resolved')
        self.assertEqual(complaint.resolved_by, self.admin)
        self.assertIsNotNone(complaint.resolved_at)
