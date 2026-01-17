# users/decorators.py

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from functools import wraps


def role_required(*roles):
    """Декоратор для проверки роли пользователя"""

    def wrapper(user):
        if user.is_authenticated:
            return user.role in roles
        return False

    return user_passes_test(wrapper, login_url='/users/login/')


# Декораторы для конкретных ролей
teacher_required = role_required('TEACHER')
student_required = role_required('STUDENT')
parent_required = role_required('PARENT')
admin_required = role_required('ADMIN')
staff_required = user_passes_test(lambda u: u.is_staff, login_url='/users/login/')


def class_teacher_required(view_func):
    """Декоратор для проверки, что пользователь - классный руководитель данного класса"""

    @wraps(view_func)
    def _wrapped_view(request, class_id, *args, **kwargs):
        from .models import TeacherProfile
        from school_structure.models import ClassGroup

        if not request.user.is_authenticated:
            return redirect('/users/login/')

        if request.user.role != 'TEACHER':
            return redirect('home')

        try:
            teacher_profile = request.user.teacher_profile
            class_group = ClassGroup.objects.get(id=class_id)

            # Проверяем, является ли учитель классным руководителем
            if class_group.classroom_teacher != teacher_profile:
                # Или проверяем, ведет ли он уроки в этом классе
                if not class_group.lessons.filter(teacher=teacher_profile).exists():
                    from django.contrib import messages
                    messages.error(request, 'У вас нет доступа к этому классу')
                    return redirect('users:teacher_dashboard')
        except (TeacherProfile.DoesNotExist, ClassGroup.DoesNotExist):
            return redirect('home')

        return view_func(request, class_id, *args, **kwargs)

    return _wrapped_view


def subject_teacher_required(view_func):
    """Декоратор для проверки, что учитель ведет данный предмет"""

    @wraps(view_func)
    def _wrapped_view(request, subject_id, *args, **kwargs):
        from .models import TeacherProfile
        from school_structure.models import Subject

        if not request.user.is_authenticated:
            return redirect('/users/login/')

        if request.user.role != 'TEACHER':
            return redirect('home')

        try:
            teacher_profile = request.user.teacher_profile
            subject = Subject.objects.get(id=subject_id)

            # Проверяем, ведет ли учитель этот предмет
            if not teacher_profile.subject_areas.filter(id=subject.id).exists():
                # Или проверяем, есть ли у него уроки по этому предмету
                if not teacher_profile.lessons.filter(subject=subject).exists():
                    from django.contrib import messages
                    messages.error(request, 'Вы не преподаете этот предмет')
                    return redirect('users:teacher_dashboard')
        except (TeacherProfile.DoesNotExist, Subject.DoesNotExist):
            return redirect('home')

        return view_func(request, subject_id, *args, **kwargs)

    return _wrapped_view
