"""
API авторизации: регистрация, текущий пользователь, выход.

Вход и обновление токена берутся готовыми из simplejwt — см. apps/users/urls.py.
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.serializers import LogoutSerializer, RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """POST /auth/register — создаёт аккаунт и сразу выдаёт пару JWT-токенов.

    Клиенту не нужно отдельно логиниться после регистрации: в ответе уже есть
    ``access`` (для запросов) и ``refresh`` (для продления сессии).
    """

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]   # регистрация доступна всем

    def create(self, request, *args, **kwargs):
        """Валидирует данные, создаёт пользователя и возвращает его с токенами."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)   # 400 с описанием ошибок
        user = serializer.save()

        # Генерируем refresh-токен; access получается из него.
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /me — профиль текущего пользователя (имя, телефон, аватар)."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Объект для чтения/записи — всегда сам автор запроса.

        Благодаря этому эндпоинт не принимает id и никто не может прочитать
        или изменить чужой профиль.
        """
        return self.request.user


class LogoutView(APIView):
    """POST /auth/logout — отзывает refresh-токен (добавляет его в чёрный список).

    Access-токен короткоживущий и остаётся валидным до истечения срока, а вот
    продлить сессию по отозванному refresh уже не получится.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogoutSerializer   # для отображения тела запроса в Swagger

    def post(self, request):
        """Проверяет и блокирует присланный refresh-токен.

        Возвращает:
            205 — токен успешно отозван;
            400 — токен не передан, повреждён или уже недействителен.
        """
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # blacklist() требует приложения token_blacklist (оно включено
            # в INSTALLED_APPS) и пишет токен в таблицу отозванных.
            RefreshToken(serializer.validated_data['refresh']).blacklist()
        except TokenError:
            # Просроченный, подделанный или уже отозванный токен.
            return Response({'detail': 'invalid token'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_205_RESET_CONTENT)
