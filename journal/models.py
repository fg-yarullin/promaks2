from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import StudentProfile
from school_structure.models import Lesson


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Присутствовал'
        ABSENT = 'ABSENT', 'Отсутствовал'
        ILL = 'ILL', 'Болел'
        LATE = 'LATE', 'Опоздал'

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name='Ученик'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.PROTECT,
        related_name='attendances',
        verbose_name='Урок'
    )
    status = models.CharField(
        max_length=10,
        choices=Status,
        default=Status.PRESENT,
        verbose_name='Статус'
    )
    note = models.TextField(blank=True, verbose_name='Примечание')

    class Meta:
        verbose_name = 'Посещаемость'
        verbose_name_plural = 'Посещаемость'
        unique_together = ['student', 'lesson']
        indexes = [
            models.Index(fields=['student', 'lesson']),  # Уже есть unique_together, но индекс тоже создастся
            models.Index(fields=['lesson', 'status']),  # Для быстрого подсчета отсутствующих на уроке
        ]

    def __str__(self):
        return f'{self.student} - {self.lesson}: {self.get_status_display()}'


class Mark(models.Model):
    class MarkType(models.TextChoices):
        EXAM = 'EXAM', 'Экзамен'
        TEST = 'TEST', 'Контрольная'
        CLASSWORK = 'CLASSWORK', 'Классная работа'
        HOMEWORK = 'HOMEWORK', 'Домашняя работа'
        ORAL = 'ORAL', 'Устный ответ'

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='marks',
        verbose_name='Ученик'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.PROTECT,
        related_name='marks',
        verbose_name='Урок'
    )
    value = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка'
    )
    mark_type = models.CharField(
        max_length=20,
        choices=MarkType,
        default=MarkType.CLASSWORK,
        verbose_name='Тип оценки'
    )
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата выставления')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    teacher = models.ForeignKey(
        'users.TeacherProfile',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Учитель'
    )

    class Meta:
        verbose_name = 'Оценка'
        verbose_name_plural = 'Оценки'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'created_at']),  # Для истории оценок ученика
            models.Index(fields=['lesson', 'mark_type']),
        ]

    def __str__(self):
        return f'{self.student} - {self.value} ({self.get_mark_type_display()})'


class Homework(models.Model):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.PROTECT,
        related_name='homeworks',
        verbose_name='Урок'
    )
    content = models.TextField(verbose_name='Содержание задания')
    attachments = models.FileField(
        upload_to='homework_attachments/',
        blank=True,
        null=True,
        verbose_name='Прикрепленные файлы'
    )
    deadline = models.DateTimeField(verbose_name='Срок выполнения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Домашнее задание'
        verbose_name_plural = 'Домашние задания'
        ordering = ['deadline']
        indexes = [
            models.Index(fields=['lesson', 'deadline']),  # Для поиска актуальных ДЗ по классу
        ]

    def __str__(self):
        return f'ДЗ для {self.lesson.class_group} до {self.deadline}'