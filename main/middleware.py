from django.shortcuts import redirect
from django.urls import reverse


class RoleRedirectMiddleware:
    """Middleware для автоматического перенаправления по ролям"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Проверяем, если пользователь залогинен и находится на главной странице
        if request.user.is_authenticated and request.path == '/':
            # Редирект на соответствующий дашборд
            role = request.user.role
            if role != 'EMPTY':
                redirect_urls = {
                    'TEACHER': 'users:teacher_dashboard',
                    'STUDENT': 'users:student_dashboard',
                    'PARENT': 'users:parent_dashboard',
                    'ADMIN': 'users:admin_dashboard',
                }

                if role in redirect_urls:
                    return redirect(redirect_urls[role])

        return response