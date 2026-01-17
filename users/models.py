# users/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


def get_current_admission_year():
    """Функция для определения текущего учебного года"""
    today = timezone.now().date()
    # Если сентябрь или позже - текущий год, иначе предыдущий
    if today.month >= 9:  # Учебный год начинается в сентябре
        return today.year
    else:
        return today.year - 1


class CustomUser(AbstractUser):
    patronymic = models.CharField(max_length=20, blank=True, null=True, verbose_name='отчество')

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Администратор'
        TEACHER = 'TEACHER', 'Учитель'
        STUDENT = 'STUDENT', 'Ученик'
        PARENT = 'PARENT', 'Родитель'
        EMPTY = 'EMPTY', 'Нет роли'

    role = models.CharField(
        max_length=20,
        choices=Role,
        default=Role.EMPTY,
        verbose_name='Роль'
    )
    email = models.EmailField(unique=True, verbose_name='Email')

    # REQUIRED_FIELDS = ['username', 'role']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.get_full_name()} ({self.get_role_display()})'


class StudentProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name='Пользователь'
    )
    class_group = models.ForeignKey(
        'school_structure.ClassGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name='Класс'
    )

    admission_year = models.PositiveIntegerField(
        verbose_name='Год поступления',
        default=get_current_admission_year
    )


class Meta:
    verbose_name = 'Профиль ученика'
    verbose_name_plural = 'Профили учеников'


def __str__(self):
    class_name = self.class_group.name if self.class_group else "Нет класса"
    return f'{self.user.get_full_name()} - {class_name}'


def save(self, *args, **kwargs):
    """При сохранении убеждаемся, что admission_year установлен"""
    if not self.admission_year:
        self.admission_year = get_current_admission_year()
    super().save(*args, **kwargs)


class TeacherProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        verbose_name='Пользователь'
    )
    subject_areas = models.ManyToManyField(
        'school_structure.Subject',
        related_name='teachers',
        verbose_name='Предметы'
    )
    education = models.TextField(blank=True, verbose_name='Образование')

    class Meta:
        verbose_name = 'Профиль учителя'
        verbose_name_plural = 'Профили учителей'

    def __str__(self):
        return f'{self.user.get_full_name()}'


class ParentProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='parent_profile',
        verbose_name='Пользователь'
    )
    children = models.ManyToManyField(
        StudentProfile,
        related_name='parents',
        verbose_name='Дети'
    )

    class Meta:
        verbose_name = 'Профиль родителя'
        verbose_name_plural = 'Профили родителей'

    def __str__(self):
        return f'{self.user.get_full_name()}'
