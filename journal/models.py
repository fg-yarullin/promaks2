# journal/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.aggregates import Avg

from users.models import StudentProfile
from school_structure.models import Lesson, AcademicYear, Subject, Quarter


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


class QuarterlyGrade(models.Model):
    """Четвертная оценка"""
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='quarterly_grades',
        verbose_name='Ученик'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='quarterly_grades',
        verbose_name='Предмет'
    )
    quarter = models.ForeignKey(
        Quarter,
        on_delete=models.CASCADE,
        related_name='quarterly_grades',
        verbose_name='Четверть'
    )
    grade = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка за четверть'
    )
    calculated_grade = models.FloatField(
        verbose_name='Расчетный балл',
        help_text='Средний балл по текущим оценкам'
    )
    is_finalized = models.BooleanField(
        default=False,
        verbose_name='Оценка утверждена'
    )
    finalized_by = models.ForeignKey(
        'users.TeacherProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Утвердил'
    )
    finalized_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата утверждения')
    comment = models.TextField(blank=True, verbose_name='Комментарий')

    class Meta:
        verbose_name = 'Четвертная оценка'
        verbose_name_plural = 'Четвертные оценки'
        unique_together = ['student', 'subject', 'quarter']
        indexes = [
            models.Index(fields=['student', 'quarter']),
            models.Index(fields=['subject', 'quarter']),
        ]

    def __str__(self):
        return f'{self.student} - {self.subject} ({self.quarter}): {self.grade}'

    def save(self, *args, **kwargs):
        # Автоматически рассчитываем средний балл
        if not self.calculated_grade:
            marks = Mark.objects.filter(
                student=self.student,
                lesson__subject=self.subject,
                lesson__quarter=self.quarter
            )
            avg = marks.aggregate(avg=Avg('value'))['avg']
            self.calculated_grade = round(avg, 2) if avg else 0
        super().save(*args, **kwargs)


class YearlyGrade(models.Model):
    """Годовая оценка"""
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='yearly_grades',
        verbose_name='Ученик'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='yearly_grades',
        verbose_name='Предмет'
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='yearly_grades',
        verbose_name='Учебный год'
    )
    grade = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Годовая оценка'
    )
    calculation_method = models.CharField(
        max_length=20,
        choices=[
            ('AVERAGE', 'Среднее арифметическое'),
            ('WEIGHTED', 'Взвешенное среднее'),
            ('MANUAL', 'Ручной ввод'),
        ],
        default='AVERAGE',
        verbose_name='Метод расчета'
    )
    quarterly_grades = models.ManyToManyField(
        QuarterlyGrade,
        blank=True,
        verbose_name='Четвертные оценки',
        help_text='Оценки за четверти, использованные для расчета'
    )
    is_finalized = models.BooleanField(default=False, verbose_name='Оценка утверждена')
    finalized_by = models.ForeignKey(
        'users.TeacherProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Утвердил'
    )
    finalized_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата утверждения')
    comment = models.TextField(blank=True, verbose_name='Комментарий')

    class Meta:
        verbose_name = 'Годовая оценка'
        verbose_name_plural = 'Годовые оценки'
        unique_together = ['student', 'subject', 'academic_year']
        indexes = [
            models.Index(fields=['student', 'academic_year']),
            models.Index(fields=['subject', 'academic_year']),
        ]

    def __str__(self):
        return f'{self.student} - {self.subject} ({self.academic_year}): {self.grade}'

    def calculate_from_quarters(self):
        """Рассчитывает годовую оценку на основе четвертных"""
        quarters = self.quarterly_grades.all()
        if quarters.exists():
            avg = quarters.aggregate(avg=Avg('grade'))['avg'] - 0.1
            # Округляем по правилам (2.6 -> 3, 2.5 -> 2)
            return round(avg)
        return None
