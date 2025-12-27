from django.urls import path
from rest_framework.urls import app_name

# from rest_framework_simplejwt.views import TokenRefreshView
# from .api import CustomTokenObtainPairView, UserRegisterView, TeacherDashboardAPI, StudentDashboardAPI, ParentDashboardAPI

from .views import (
    LoginView, LogoutView, RegisterView,
    ProfileView, ProfileUpdateView, ProfileCompleteView,
    TeacherDashboardView, StudentDashboardView,
    ParentDashboardView, AdminDashboardView,
    HomeView,
)

urlpatterns = [
    # API endpoints (JWT)
    # path('api/login/', CustomTokenObtainPairView.as_view(), name='api_login'),
    # path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # path('api/register/', UserRegisterView.as_view(), name='api_register'),
    # path('api/dashboard/teacher/', TeacherDashboardAPI.as_view(), name='api_teacher_dashboard'),
    # path('api/dashboard/student/', StudentDashboardAPI.as_view(), name='api_student_dashboard'),
    # path('api/dashboard/parent/', ParentDashboardAPI.as_view(), name='api_parent_dashboard'),

    # Template views (сессии)
    # path('login/', CustomLoginView.as_view(), name='login'),
    # path('dashboard/teacher/', TeacherDashboardView.as_view(), name='teacher_dashboard'),
    # path('dashboard/student/', StudentDashboardView.as_view(), name='student_dashboard'),
    # # Добавьте остальные...
    # Аутентификация
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),

    # Профиль
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile_update'),
    path('profile/complete/', ProfileCompleteView.as_view(), name='profile_complete'),

    # Дашборды
    path('dashboard/teacher/', TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('dashboard/student/', StudentDashboardView.as_view(), name='student_dashboard'),
    path('dashboard/parent/', ParentDashboardView.as_view(), name='parent_dashboard'),
    path('dashboard/admin/', AdminDashboardView.as_view(), name='admin_dashboard'),

    # Общее
    path('', HomeView.as_view(), name='home'),
]
