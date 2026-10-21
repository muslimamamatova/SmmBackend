from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.choices import FavoriteType, NotificationType
from apps.common.models import Favorite, Notification, Skill
from apps.users.models import User, UserRole


class SkillTests(APITestCase):
    def test_list_skills_is_public(self):
        Skill.objects.create(name='SMM')
        Skill.objects.create(name='SEO')
        response = self.client.get('/skills/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_search_skills(self):
        Skill.objects.create(name='SMM')
        Skill.objects.create(name='SEO')
        response = self.client.get('/skills/', {'search': 'SEO'})
        self.assertEqual(response.data['count'], 1)


class FavoriteTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='fav@example.com', password='pass12345', name='Fav', role=UserRole.EMPLOYER)
        self.client.force_authenticate(self.user)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        response = self.client.get('/favorites/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_and_list_only_own_favorites(self):
        other = User.objects.create_user(email='other@example.com', password='pass12345', name='Other', role=UserRole.EMPLOYER)
        Favorite.objects.create(user=other, object_type=FavoriteType.JOB, object_id=1)

        response = self.client.post('/favorites/', {'object_type': FavoriteType.JOB, 'object_id': 5})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get('/favorites/')
        self.assertEqual(list_response.data['count'], 1)
        self.assertEqual(list_response.data['results'][0]['object_id'], 5)


class NotificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='notif@example.com', password='pass12345', name='Notif', role=UserRole.EMPLOYER)
        self.client.force_authenticate(self.user)

    def test_mark_single_notification_read(self):
        notification = Notification.objects.create(
            user=self.user, type=NotificationType.MESSAGE, title='New message',
        )
        response = self.client.patch(f'/notifications/{notification.id}/', {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_read_all(self):
        Notification.objects.create(user=self.user, type=NotificationType.MESSAGE, title='A')
        Notification.objects.create(user=self.user, type=NotificationType.MESSAGE, title='B')
        response = self.client.post('/notifications/read-all/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)
