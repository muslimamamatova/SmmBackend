from rest_framework import status
from rest_framework.test import APITestCase

from apps.chat.models import Chat, Message
from apps.common.choices import Specialization
from apps.companies.models import Company
from apps.orders.models import Order
from apps.specialists.models import SpecialistProfile
from apps.users.models import User, UserRole


class ChatTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(email='a@example.com', password='pass12345', name='A', role=UserRole.EMPLOYER)
        self.user_b = User.objects.create_user(email='b@example.com', password='pass12345', name='B', role=UserRole.SPECIALIST)
        self.stranger = User.objects.create_user(email='c@example.com', password='pass12345', name='C', role=UserRole.SPECIALIST)

    def test_create_chat_requires_authentication(self):
        response = self.client.post('/chats/', {'participants': [self.user_b.id]})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_chat_adds_current_user_as_participant(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.post('/chats/', {'participants': [self.user_b.id]})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        chat = Chat.objects.get(pk=response.data['id'])
        self.assertIn(self.user_a, chat.participants.all())
        self.assertIn(self.user_b, chat.participants.all())

    def test_chats_scoped_to_participants(self):
        chat = Chat.objects.create()
        chat.participants.set([self.user_a, self.user_b])
        self.client.force_authenticate(self.stranger)
        response = self.client.get('/chats/')
        self.assertEqual(response.data['count'], 0)

        self.client.force_authenticate(self.user_a)
        response = self.client.get('/chats/')
        self.assertEqual(response.data['count'], 1)

    def test_send_and_list_messages(self):
        chat = Chat.objects.create()
        chat.participants.set([self.user_a, self.user_b])
        self.client.force_authenticate(self.user_a)

        response = self.client.post(f'/chats/{chat.id}/messages/', {'text': 'Hello'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['sender'], self.user_a.id)

        list_response = self.client.get(f'/chats/{chat.id}/messages/')
        self.assertEqual(len(list_response.data), 1)

    def test_mark_read_updates_other_users_messages(self):
        chat = Chat.objects.create()
        chat.participants.set([self.user_a, self.user_b])
        Message.objects.create(chat=chat, sender=self.user_a, text='Hi')

        self.client.force_authenticate(self.user_b)
        response = self.client.post(f'/chats/{chat.id}/read/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        message = chat.messages.first()
        self.assertIsNotNone(message.read_at)

    def test_reuses_existing_chat_for_same_order(self):
        company = Company.objects.create(user=self.user_a, name='Acme')
        specialist = SpecialistProfile.objects.create(user=self.user_b, specialization=Specialization.SMM_MANAGER)
        order = Order.objects.create(company=company, specialist=specialist, price='100.00')

        self.client.force_authenticate(self.user_a)
        first = self.client.post('/chats/', {'participants': [self.user_b.id], 'order': order.id})
        second = self.client.post('/chats/', {'participants': [self.user_b.id], 'order': order.id})
        self.assertEqual(Chat.objects.count(), 1)
        self.assertEqual(first.data['id'], second.data['id'])
