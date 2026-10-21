from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.choices import OrderStatus, Specialization
from apps.companies.models import Company
from apps.orders.models import Order, Review
from apps.specialists.models import SpecialistProfile
from apps.users.models import User, UserRole


class OrderTests(APITestCase):
    def setUp(self):
        self.employer = User.objects.create_user(email='emp@example.com', password='pass12345', name='Emp', role=UserRole.EMPLOYER)
        self.company = Company.objects.create(user=self.employer, name='Acme')
        self.specialist_user = User.objects.create_user(email='spec@example.com', password='pass12345', name='Spec', role=UserRole.SPECIALIST)
        self.specialist = SpecialistProfile.objects.create(user=self.specialist_user, specialization=Specialization.SMM_MANAGER)
        self.stranger = User.objects.create_user(email='stranger@example.com', password='pass12345', name='Stranger', role=UserRole.EMPLOYER)

    def test_only_company_can_create_order(self):
        self.client.force_authenticate(self.specialist_user)
        response = self.client.post('/orders/', {'specialist': self.specialist.id, 'price': '150.00'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_can_create_order(self):
        self.client.force_authenticate(self.employer)
        response = self.client.post('/orders/', {'specialist': self.specialist.id, 'price': '150.00'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(pk=response.data['id'])
        self.assertEqual(order.company, self.company)
        self.assertEqual(order.status, OrderStatus.NEW)

    def test_orders_scoped_to_participants(self):
        Order.objects.create(company=self.company, specialist=self.specialist, price='150.00')
        self.client.force_authenticate(self.stranger)
        response = self.client.get('/orders/')
        self.assertEqual(response.data['count'], 0)

        self.client.force_authenticate(self.specialist_user)
        response = self.client.get('/orders/')
        self.assertEqual(response.data['count'], 1)

    def test_full_order_lifecycle(self):
        order = Order.objects.create(company=self.company, specialist=self.specialist, price='150.00')

        self.client.force_authenticate(self.specialist_user)
        response = self.client.post(f'/orders/{order.id}/accept/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.ACCEPTED)

        response = self.client.post(f'/orders/{order.id}/start/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.IN_PROGRESS)
        self.assertIsNotNone(order.started_at)

        response = self.client.post(f'/orders/{order.id}/submit/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.REVIEW)

        self.client.force_authenticate(self.employer)
        response = self.client.post(f'/orders/{order.id}/complete/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.COMPLETED)
        self.assertIsNotNone(order.completed_at)
        self.specialist.refresh_from_db()
        self.assertEqual(self.specialist.orders_count, 1)

    def test_invalid_transition_rejected(self):
        order = Order.objects.create(company=self.company, specialist=self.specialist, price='150.00')
        self.client.force_authenticate(self.specialist_user)
        response = self.client.post(f'/orders/{order.id}/start/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_review_requires_completed_order(self):
        order = Order.objects.create(company=self.company, specialist=self.specialist, price='150.00')
        self.client.force_authenticate(self.employer)
        response = self.client.post(f'/orders/{order.id}/review/', {
            'rating': 5, 'quality_rating': 5, 'timeliness_rating': 5,
            'communication_rating': 5, 'compliance_rating': 5,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_review_after_completion(self):
        order = Order.objects.create(
            company=self.company, specialist=self.specialist, price='150.00', status=OrderStatus.COMPLETED,
        )
        self.client.force_authenticate(self.employer)
        response = self.client.post(f'/orders/{order.id}/review/', {
            'rating': 5, 'quality_rating': 5, 'timeliness_rating': 5,
            'communication_rating': 5, 'compliance_rating': 5, 'text': 'Great work',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review = Review.objects.get(order=order)
        self.assertEqual(review.author, self.employer)
        self.assertEqual(review.recipient, self.specialist_user)

        duplicate = self.client.post(f'/orders/{order.id}/review/', {
            'rating': 4, 'quality_rating': 4, 'timeliness_rating': 4,
            'communication_rating': 4, 'compliance_rating': 4,
        })
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)


class ReviewModerationTests(APITestCase):
    def setUp(self):
        employer = User.objects.create_user(email='emp@example.com', password='pass12345', name='Emp', role=UserRole.EMPLOYER)
        company = Company.objects.create(user=employer, name='Acme')
        specialist_user = User.objects.create_user(email='spec@example.com', password='pass12345', name='Spec', role=UserRole.SPECIALIST)
        specialist = SpecialistProfile.objects.create(user=specialist_user, specialization=Specialization.SMM_MANAGER)
        order = Order.objects.create(company=company, specialist=specialist, price='100.00', status=OrderStatus.COMPLETED)
        self.review = Review.objects.create(
            order=order, author=employer, recipient=specialist_user, rating=1,
            quality_rating=1, timeliness_rating=1, communication_rating=1, compliance_rating=1, text='abuse',
        )
        self.admin = User.objects.create_user(email='admin@example.com', password='pass12345', name='Admin', role=UserRole.ADMIN)
        self.employer = employer

    def test_reviews_list_is_public(self):
        response = self.client.get('/reviews/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_non_admin_cannot_delete_review(self):
        self.client.force_authenticate(self.employer)
        response = self.client.delete(f'/reviews/{self.review.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_review(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f'/reviews/{self.review.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Review.objects.filter(pk=self.review.id).exists())
