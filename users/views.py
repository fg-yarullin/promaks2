# users/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import View, TemplateView, UpdateView
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.db.models import Count, Avg, Q, Sum, Max, Min
from datetime import datetime, timedelta
import calendar
import math

from .decorators import role_required, teacher_required, student_required, parent_required, admin_required
from .forms import EmailOrUsernameAuthenticationForm, UserRegistrationForm, StudentProfileForm, TeacherProfileForm
from .models import CustomUser, StudentProfile, TeacherProfile, ParentProfile
from school_structure.models import Lesson, ClassGroup, Subject, Quarter, AcademicYear
from journal.models import StudentMark, Attendance, Homework, QuarterlyGrade, YearlyGrade, GradeColumn


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

        try:
            current_quarter = Quarter.objects.get(is_current=True)
        except Quarter.DoesNotExist:
            current_quarter = None

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

        # Последние выставленные оценки (новые)
        recent_marks = StudentMark.objects.filter(
            teacher=teacher
        ).select_related(
            'student__user',
            'lesson_grade_column__lesson__subject',
            'lesson_grade_column__grade_column'
        ).order_by('-created_at')[:5]

        # Домашние задания к проверке
        homework_to_check = Homework.objects.filter(
            lesson__teacher=teacher,
            deadline__lt=datetime.now()
        ).select_related('lesson__subject', 'lesson__class_group').order_by('deadline')[:5]

        # Статистика (новые оценки)
        marks_this_month = StudentMark.objects.filter(
            teacher=teacher,
            created_at__month=today.month,
            created_at__year=today.year
        ).count()

        # Рассчитываем общую статистику по классам
        class_stats = []
        for class_group in classes:
            # Количество оценок в классе
            marks_count = StudentMark.objects.filter(
                teacher=teacher,
                student__class_group=class_group
            ).count()

            # Средний балл в классе
            avg_grade = StudentMark.objects.filter(
                teacher=teacher,
                student__class_group=class_group
            ).aggregate(avg=Avg('value'))['avg']

            class_stats.append({
                'class': class_group,
                'marks_count': marks_count,
                'avg_grade': round(avg_grade, 2) if avg_grade else None
            })

        context.update({
            'teacher': teacher,
            'upcoming_lessons': upcoming_lessons,
            'today_lessons': today_lessons,
            'classes': classes,
            'recent_marks': recent_marks,
            'homework_to_check': homework_to_check,
            'class_stats': class_stats,
            'stats': {
                'total_classes': classes.count(),
                'marks_this_month': marks_this_month,
                'today_lessons_count': today_lessons.count(),
            },
            'today': today,
            'current_quarter': current_quarter,
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

        # Получаем текущую четверть
        try:
            current_quarter = Quarter.objects.get(is_current=True)
        except Quarter.DoesNotExist:
            current_quarter = None

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

        # Последние оценки (новые)
        recent_marks = StudentMark.objects.filter(
            student=student
        ).select_related(
            'lesson_grade_column__lesson__subject',
            'teacher__user',
            'lesson_grade_column__grade_column'
        ).order_by('-created_at')[:10]

        # Средние баллы по предметам (новые)
        subject_grades = StudentMark.objects.filter(
            student=student
        ).values(
            'lesson_grade_column__lesson__subject__title'
        ).annotate(
            avg_grade=Avg('value'),
            count=Count('id')
        ).order_by('lesson_grade_column__lesson__subject__title')

        # Рассчитываем четвертные оценки
        quarterly_grades = []
        if current_quarter:
            for subject in Subject.objects.filter(
                    lessons__class_group=student.class_group
            ).distinct():
                q_grade = QuarterlyGrade.objects.filter(
                    student=student,
                    subject=subject,
                    quarter=current_quarter
                ).first()

                if q_grade and q_grade.grade:
                    quarterly_grades.append({
                        'subject': subject,
                        'grade': q_grade.grade,
                        'calculated': q_grade.calculated_grade
                    })

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

        # Общая статистика успеваемости
        total_marks = StudentMark.objects.filter(student=student).count()
        avg_all = StudentMark.objects.filter(student=student).aggregate(avg=Avg('value'))['avg']

        context.update({
            'student': student,
            'schedule_today': schedule_today,
            'schedule_tomorrow': schedule_tomorrow,
            'recent_marks': recent_marks,
            'subject_grades': subject_grades,
            'quarterly_grades': quarterly_grades,
            'upcoming_homework': upcoming_homework,
            'monthly_attendance': monthly_attendance,
            'total_marks': total_marks,
            'avg_all': round(avg_all, 2) if avg_all else None,
            'today': today,
            'tomorrow': tomorrow,
            'current_quarter': current_quarter,
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
            # Последние оценки ребенка (новые)
            recent_marks = StudentMark.objects.filter(
                student=child
            ).select_related(
                'lesson_grade_column__lesson__subject',
                'lesson_grade_column__grade_column'
            ).order_by('-created_at')[:5]

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

            # Четвертные оценки (новые)
            quarterly_grades = QuarterlyGrade.objects.filter(
                student=child
            ).select_related('subject', 'quarter').order_by('quarter__number')[:4]

            # Общая успеваемость
            avg_grade = StudentMark.objects.filter(
                student=child
            ).aggregate(avg=Avg('value'))['avg']

            children_data.append({
                'child': child,
                'recent_marks': recent_marks,
                'attendance_stats': attendance_stats,
                'today_lessons': today_lessons,
                'quarterly_grades': quarterly_grades,
                'avg_grade': round(avg_grade, 2) if avg_grade else None,
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
        new_marks_today = StudentMark.objects.filter(created_at__date=today).count()

        # Последние действия
        recent_users = CustomUser.objects.all().order_by('-date_joined')[:5]
        recent_marks = StudentMark.objects.all().select_related(
            'student__user',
            'teacher__user',
            'lesson_grade_column__lesson__subject'
        ).order_by('-created_at')[:5]

        # Учебный год и четверть
        try:
            academic_year = AcademicYear.objects.get(is_current=True)
            current_quarter = Quarter.objects.get(is_current=True)
        except (AcademicYear.DoesNotExist, Quarter.DoesNotExist):
            academic_year = None
            current_quarter = None

        # Статистика по успеваемости
        grade_stats = StudentMark.objects.aggregate(
            total_marks=Count('id'),
            avg_grade=Avg('value'),
            max_grade=Max('value'),
            min_grade=Min('value')
        )

        # Статистика по классам
        class_stats = ClassGroup.objects.annotate(
            student_count=Count('students'),
            mark_count=Count('students__student_marks')
        ).order_by('-mark_count')[:5]

        context.update({
            'stats': {
                'total_users': total_users,
                'total_students': total_students,
                'total_teachers': total_teachers,
                'total_parents': total_parents,
                'new_users_today': new_users_today,
                'new_marks_today': new_marks_today,
                'total_marks': grade_stats['total_marks'],
                'avg_grade': round(grade_stats['avg_grade'], 2) if grade_stats['avg_grade'] else None,
            },
            'recent_users': recent_users,
            'recent_marks': recent_marks,
            'academic_year': academic_year.year if academic_year else 'Не установлен',
            'current_quarter': current_quarter.name if current_quarter else 'Не установлена',
            'class_stats': class_stats,
        })
        return context


# ==================== ДОПОЛНИТЕЛЬНЫЕ VIEWS ====================

@method_decorator([login_required, teacher_required], name='dispatch')
class TeacherGradesView(TemplateView):
    """Просмотр всех оценок учителя"""
    template_name = 'teacher/teacher_grades.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher_profile

        # Фильтры
        class_id = self.request.GET.get('class_id')
        subject_id = self.request.GET.get('subject_id')
        quarter_id = self.request.GET.get('quarter_id')
        student_id = self.request.GET.get('student_id')

        # Базовый запрос
        marks = StudentMark.objects.filter(teacher=teacher).select_related(
            'student__user',
            'lesson_grade_column__lesson__subject',
            'lesson_grade_column__lesson__class_group',
            'lesson_grade_column__lesson__quarter',
            'lesson_grade_column__grade_column'
        ).order_by('-created_at')

        # Применяем фильтры
        if class_id:
            marks = marks.filter(lesson_grade_column__lesson__class_group_id=class_id)

        if subject_id:
            marks = marks.filter(lesson_grade_column__lesson__subject_id=subject_id)

        if quarter_id:
            marks = marks.filter(lesson_grade_column__lesson__quarter_id=quarter_id)

        if student_id:
            marks = marks.filter(student_id=student_id)

        # Получаем доступные фильтры
        classes = ClassGroup.objects.filter(lessons__teacher=teacher).distinct()
        subjects = Subject.objects.filter(lessons__teacher=teacher).distinct()
        quarters = Quarter.objects.filter(
            lessons__teacher=teacher
        ).distinct().order_by('-start_date')

        # Статистика
        total_marks = marks.count()
        avg_grade = marks.aggregate(avg=Avg('value'))['avg']

        context.update({
            'marks': marks,
            'classes': classes,
            'subjects': subjects,
            'quarters': quarters,
            'total_marks': total_marks,
            'avg_grade': round(avg_grade, 2) if avg_grade else None,
            'filters': {
                'class_id': class_id,
                'subject_id': subject_id,
                'quarter_id': quarter_id,
                'student_id': student_id,
            }
        })
        return context


@method_decorator([login_required, student_required], name='dispatch')
class StudentGradesView(TemplateView):
    """Просмотр всех оценок ученика"""
    template_name = 'users/student_grades.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile

        # Фильтры
        subject_id = self.request.GET.get('subject_id')
        quarter_id = self.request.GET.get('quarter_id')

        # Базовый запрос
        marks = StudentMark.objects.filter(student=student).select_related(
            'teacher__user',
            'lesson_grade_column__lesson__subject',
            'lesson_grade_column__lesson__quarter',
            'lesson_grade_column__grade_column'
        ).order_by('-created_at')

        # Применяем фильтры
        if subject_id:
            marks = marks.filter(lesson_grade_column__lesson__subject_id=subject_id)

        if quarter_id:
            marks = marks.filter(lesson_grade_column__lesson__quarter_id=quarter_id)

        # Получаем предметы и четверти
        subjects = Subject.objects.filter(
            lessons__class_group=student.class_group
        ).distinct()

        quarters = Quarter.objects.filter(
            lessons__class_group=student.class_group
        ).distinct().order_by('-start_date')

        # Рассчитываем статистику по предметам
        subject_stats = []
        for subject in subjects:
            subject_marks = marks.filter(lesson_grade_column__lesson__subject=subject)
            avg = subject_marks.aggregate(avg=Avg('value'))['avg']
            count = subject_marks.count()

            if count > 0:
                subject_stats.append({
                    'subject': subject,
                    'avg_grade': round(avg, 2) if avg else None,
                    'marks_count': count,
                    'last_grade': subject_marks.first().value if subject_marks.exists() else None
                })

        # Четвертные оценки
        quarterly_grades = QuarterlyGrade.objects.filter(
            student=student
        ).select_related('subject', 'quarter').order_by('quarter__number')

        # Годовые оценки
        yearly_grades = YearlyGrade.objects.filter(
            student=student
        ).select_related('subject', 'academic_year').order_by('academic_year__year')

        context.update({
            'marks': marks,
            'subjects': subjects,
            'quarters': quarters,
            'subject_stats': subject_stats,
            'quarterly_grades': quarterly_grades,
            'yearly_grades': yearly_grades,
            'filters': {
                'subject_id': subject_id,
                'quarter_id': quarter_id,
            }
        })
        return context


@method_decorator([login_required], name='dispatch')
class GradeStatisticsView(TemplateView):
    """Статистика успеваемости"""
    template_name = 'users/grade_statistics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.role == 'TEACHER':
            teacher = user.teacher_profile
            context['is_teacher'] = True

            # Статистика по классам
            class_stats = []
            classes = ClassGroup.objects.filter(lessons__teacher=teacher).distinct()

            for class_group in classes:
                marks = StudentMark.objects.filter(
                    teacher=teacher,
                    student__class_group=class_group
                )

                stats = marks.aggregate(
                    total=Count('id'),
                    avg=Avg('value'),
                    max=Max('value'),
                    min=Min('value')
                )

                # Распределение оценок
                grade_distribution = marks.values('value').annotate(
                    count=Count('id')
                ).order_by('value')

                class_stats.append({
                    'class': class_group,
                    'stats': stats,
                    'grade_distribution': grade_distribution,
                })

            context['class_stats'] = class_stats

        elif user.role == 'STUDENT':
            student = user.student_profile
            context['is_student'] = True

            # Прогресс по предметам
            subjects = Subject.objects.filter(
                lessons__class_group=student.class_group
            ).distinct()

            subject_progress = []
            for subject in subjects:
                marks = StudentMark.objects.filter(
                    student=student,
                    lesson_grade_column__lesson__subject=subject
                ).order_by('created_at')

                if marks.exists():
                    # Рассчитываем прогресс
                    dates = [mark.created_at.date() for mark in marks]
                    grades = [mark.value for mark in marks]

                    # Рассчитываем скользящее среднее
                    moving_avg = []
                    for i in range(len(grades)):
                        window = grades[max(0, i - 2):i + 1]
                        moving_avg.append(sum(window) / len(window))

                    subject_progress.append({
                        'subject': subject,
                        'marks_count': marks.count(),
                        'avg_grade': marks.aggregate(avg=Avg('value'))['avg'],
                        'dates': dates,
                        'grades': grades,
                        'moving_avg': moving_avg,
                    })

            context['subject_progress'] = subject_progress

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