# users/urls.py
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Аутентификация
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),

    # Профиль
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/update/', views.ProfileUpdateView.as_view(), name='profile_update'),
    path('profile/complete/', views.ProfileCompleteView.as_view(), name='profile_complete'),

    # Дашборды
    path('dashboard/teacher/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('dashboard/student/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('dashboard/parent/', views.ParentDashboardView.as_view(), name='parent_dashboard'),
    path('dashboard/admin/', views.AdminDashboardView.as_view(), name='admin_dashboard'),

    # Новые URL для оценок
    path('teacher/grades/', views.TeacherGradesView.as_view(), name='teacher_grades'),
    path('student/grades/', views.StudentGradesView.as_view(), name='student_grades'),
    path('grades/statistics/', views.GradeStatisticsView.as_view(), name='grade_statistics'),

    # Главная страница
    path('', views.HomeView.as_view(), name='home'),
]