# users/view.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.generic import View, TemplateView, UpdateView
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.db.models import Count, Avg, Q
from datetime import datetime, timedelta
import calendar

from .forms import EmailOrUsernameAuthenticationForm, UserRegistrationForm, StudentProfileForm, TeacherProfileForm
from .models import CustomUser, StudentProfile, TeacherProfile, ParentProfile
from school_structure.models import Lesson, ClassGroup, Subject, Quarter, AcademicYear
from journal.models import Mark, Attendance, Homework

from .decorators import (
    role_required, teacher_required, student_required,
    parent_required, admin_required, staff_required
)


# ==================== ДЕКОРАТОРЫ ДЛЯ ПРОВЕРКИ РОЛЕЙ ====================

# def role_required(*roles):
#     """Декоратор для проверки роли пользователя"""
#
#     def wrapper(user):
#         if user.is_authenticated:
#             return user.role in roles
#         return False
#
#     return user_passes_test(wrapper, login_url='/users/login/')
#
#
# teacher_required = role_required('TEACHER')
# student_required = role_required('STUDENT')
# parent_required = role_required('PARENT')
# admin_required = role_required('ADMIN')
# staff_required = user_passes_test(lambda u: u.is_staff, login_url='/users/login/')


# ==================== VIEWS АУТЕНТИФИКАЦИИ ====================

class LoginView(View):
    template_name = 'users/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(self.get_redirect_url(request.user))
        form = EmailOrUsernameAuthenticationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = EmailOrUsernameAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.get_full_name()}!')

            # Редирект в зависимости от роли
            redirect_url = self.get_redirect_url(user)
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect(redirect_url)

        return render(request, self.template_name, {'form': form})

    def get_redirect_url(self, user):
        """Определяем URL для редиректа по роли"""
        role_redirects = {
            'TEACHER': 'users:teacher_dashboard',
            'STUDENT': 'users:student_dashboard',
            'PARENT': 'users:parent_dashboard',
            'ADMIN': 'users:admin_dashboard',
            'EMPTY': 'users:profile_complete',  # Если роль не выбрана
        }
        return reverse_lazy(role_redirects.get(user.role, 'home'))


class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.info(request, 'Вы успешно вышли из системы')
        return redirect('users:home')


class RegisterView(View):
    template_name = 'users/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        form = UserRegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect(self.get_redirect_url(user))

        return render(request, self.template_name, {'form': form})

    def get_redirect_url(self, user):
        if user.role == 'EMPTY':
            return reverse_lazy('profile_complete')
        return reverse_lazy(f'{user.role.lower()}_dashboard')


# ==================== VIEWS ПРОФИЛЯ ====================

@method_decorator([login_required], name='dispatch')
class ProfileView(TemplateView):
    template_name = 'users/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Определяем форму в зависимости от роли
        if user.role == 'STUDENT' and hasattr(user, 'student_profile'):
            context['profile_form'] = StudentProfileForm(instance=user.student_profile)
        elif user.role == 'TEACHER' and hasattr(user, 'teacher_profile'):
            context['profile_form'] = TeacherProfileForm(instance=user.teacher_profile)

        return context


@method_decorator([login_required], name='dispatch')
class ProfileUpdateView(View):
    def post(self, request):
        user = request.user
        success = False

        if user.role == 'STUDENT' and hasattr(user, 'student_profile'):
            form = StudentProfileForm(request.POST, instance=user.student_profile)
            if form.is_valid():
                form.save()
                success = True
        elif user.role == 'TEACHER' and hasattr(user, 'teacher_profile'):
            form = TeacherProfileForm(request.POST, instance=user.teacher_profile)
            if form.is_valid():
                form.save()
                success = True

        if success:
            messages.success(request, 'Профиль успешно обновлен')
        else:
            messages.error(request, 'Ошибка при обновлении профиля')

        return redirect('profile')


# ==================== DASHBOARD VIEWS ====================

@method_decorator([login_required, teacher_required], name='dispatch')
class TeacherDashboardView(TemplateView):
    template_name = 'dashboard/teacher.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher_profile

        # Текущая дата и период
        today = datetime.now().date()
        current_week = today.isocalendar()[1]

        # Ближайшие уроки (на 7 дней вперед)
        upcoming_lessons = Lesson.objects.filter(
            teacher=teacher,
            date__range=[today, today + timedelta(days=7)]
        ).select_related('subject', 'class_group').order_by('date', 'lesson_number')[:10]

        # Уроки на сегодня
        today_lessons = Lesson.objects.filter(
            teacher=teacher,
            date=today
        ).select_related('subject', 'class_group').order_by('lesson_number')

        # Классы, которые ведет учитель
        classes = ClassGroup.objects.filter(
            lessons__teacher=teacher
        ).distinct().annotate(
            student_count=Count('students'),
            lesson_count=Count('lessons', filter=Q(lessons__teacher=teacher))
        )

        # Последние выставленные оценки
        recent_marks = Mark.objects.filter(
            teacher=teacher
        ).select_related('student__user', 'lesson__subject').order_by('-created_at')[:5]

        # Домашние задания к проверке
        homework_to_check = Homework.objects.filter(
            lesson__teacher=teacher,
            deadline__lt=datetime.now()
        ).select_related('lesson__subject', 'lesson__class_group').order_by('deadline')[:5]

        # Статистика
        marks_this_month = Mark.objects.filter(
            teacher=teacher,
            created_at__month=today.month,
            created_at__year=today.year
        ).count()

        context.update({
            'teacher': teacher,
            'upcoming_lessons': upcoming_lessons,
            'today_lessons': today_lessons,
            'classes': classes,
            'recent_marks': recent_marks,
            'homework_to_check': homework_to_check,
            'stats': {
                'total_classes': classes.count(),
                'marks_this_month': marks_this_month,
                'today_lessons_count': today_lessons.count(),
            },
            'today': today,
        })
        return context


@method_decorator([login_required, student_required], name='dispatch')
class StudentDashboardView(TemplateView):
    template_name = 'dashboard/student.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile

        # Текущая дата
        today = datetime.now().date()

        # Расписание на сегодня
        schedule_today = Lesson.objects.filter(
            class_group=student.class_group,
            date=today
        ).select_related('subject', 'teacher__user').order_by('lesson_number')

        # Расписание на завтра
        tomorrow = today + timedelta(days=1)
        schedule_tomorrow = Lesson.objects.filter(
            class_group=student.class_group,
            date=tomorrow
        ).select_related('subject', 'teacher__user').order_by('lesson_number')

        # Последние оценки (последние 10)
        recent_marks = Mark.objects.filter(
            student=student
        ).select_related('lesson__subject', 'teacher__user').order_by('-created_at')[:10]

        # Средние баллы по предметам
        subject_grades = Mark.objects.filter(
            student=student
        ).values(
            'lesson__subject__title'
        ).annotate(
            avg_grade=Avg('value'),
            count=Count('id')
        ).order_by('lesson__subject__title')

        # Ближайшие домашние задания
        upcoming_homework = Homework.objects.filter(
            lesson__class_group=student.class_group,
            deadline__gt=datetime.now()
        ).select_related('lesson__subject').order_by('deadline')[:5]

        # Посещаемость за текущий месяц
        month_start = today.replace(day=1)
        month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        monthly_attendance = Attendance.objects.filter(
            student=student,
            lesson__date__range=[month_start, month_end]
        ).values('status').annotate(count=Count('id'))

        context.update({
            'student': student,
            'schedule_today': schedule_today,
            'schedule_tomorrow': schedule_tomorrow,
            'recent_marks': recent_marks,
            'subject_grades': subject_grades,
            'upcoming_homework': upcoming_homework,
            'monthly_attendance': monthly_attendance,
            'today': today,
            'tomorrow': tomorrow,
        })
        return context


@method_decorator([login_required, parent_required], name='dispatch')
class ParentDashboardView(TemplateView):
    template_name = 'dashboard/parent.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parent = self.request.user.parent_profile

        # Получаем всех детей
        children = parent.children.all().select_related('user', 'class_group')

        children_data = []
        for child in children:
            # Последние оценки ребенка
            recent_marks = Mark.objects.filter(
                student=child
            ).select_related('lesson__subject').order_by('-created_at')[:5]

            # Посещаемость за последнюю неделю
            week_ago = datetime.now().date() - timedelta(days=7)
            attendance_stats = Attendance.objects.filter(
                student=child,
                lesson__date__gte=week_ago
            ).aggregate(
                present=Count('id', filter=Q(status='PRESENT')),
                absent=Count('id', filter=Q(status='ABSENT')),
                ill=Count('id', filter=Q(status='ILL')),
                late=Count('id', filter=Q(status='LATE'))
            )

            # Ближайшие уроки на сегодня
            today_lessons = Lesson.objects.filter(
                class_group=child.class_group,
                date=datetime.now().date()
            ).select_related('subject').order_by('lesson_number')

            children_data.append({
                'child': child,
                'recent_marks': recent_marks,
                'attendance_stats': attendance_stats,
                'today_lessons': today_lessons,
            })

        context.update({
            'parent': parent,
            'children_data': children_data,
            'total_children': children.count(),
        })
        return context


@method_decorator([login_required, admin_required], name='dispatch')
class AdminDashboardView(TemplateView):
    template_name = 'dashboard/admin.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Общая статистика
        total_users = CustomUser.objects.count()
        total_students = StudentProfile.objects.count()
        total_teachers = TeacherProfile.objects.count()
        total_parents = ParentProfile.objects.count()

        # Активность сегодня
        today = datetime.now().date()
        new_users_today = CustomUser.objects.filter(date_joined__date=today).count()
        new_marks_today = Mark.objects.filter(created_at__date=today).count()

        # Последние действия
        recent_users = CustomUser.objects.all().order_by('-date_joined')[:5]
        recent_marks = Mark.objects.all().select_related('student__user', 'teacher__user').order_by('-created_at')[:5]
        academic_year = AcademicYear.objects.get(is_current=True)

        context.update({
            'stats': {
                'total_users': total_users,
                'total_students': total_students,
                'total_teachers': total_teachers,
                'total_parents': total_parents,
                'new_users_today': new_users_today,
                'new_marks_today': new_marks_today,
            },
            'recent_users': recent_users,
            'recent_marks': recent_marks,
            'academic_year': academic_year.year,
        })
        return context


# ==================== ОБЩИЕ VIEWS ====================

class HomeView(TemplateView):
    template_name = 'home.html'

    def get(self, request):
        if request.user.is_authenticated:
            # Редирект на дашборд по роли
            role = request.user.role
            if role == 'TEACHER':
                return redirect('users:teacher_dashboard')
            elif role == 'STUDENT':
                return redirect('users:student_dashboard')
            elif role == 'PARENT':
                return redirect('users:parent_dashboard')
            elif role == 'ADMIN':
                return redirect('users:admin_dashboard')

        return render(request, self.template_name)


@method_decorator([login_required], name='dispatch')
class ProfileCompleteView(TemplateView):
    """Страница для завершения профиля, если роль EMPTY"""
    template_name = 'users/profile_complete.html'

    def get(self, request):
        if request.user.role != 'EMPTY':
            return redirect('home')
        return super().get(request)

    def post(self, request):
        role = request.POST.get('role')
        if role in dict(CustomUser.Role.choices):
            request.user.role = role
            request.user.save()
            messages.success(request, 'Роль успешно выбрана')
            return redirect(f'{role.lower()}_dashboard')

        messages.error(request, 'Неверная роль')
        return self.get(request)
