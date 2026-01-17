# authentication.py

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()


class EmailOrUsernameBackend(AuthenticationForm):
    """
    Кастомный бэкенд аутентификации по email ИЛИ username.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        try:
            # Ищем пользователя по email или username
            user = User.objects.get(
                Q(email__iexact=username) | Q(username__iexact=username)
            )
        except User.DoesNotExist:
            # Возвращаем None, если пользователь не найден
            # Django попробует следующий бэкенд
            return None
        except User.MultipleObjectsReturned:
            # Если нашли несколько пользователей, берем первого
            user = User.objects.filter(
                Q(email__iexact=username) | Q(username__iexact=username)
            ).first()

        # Проверяем пароль
        if user and user.check_password(password):
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
