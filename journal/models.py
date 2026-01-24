# journal/models.py
from django.utils import timezone
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


class GradeType(models.Model):
    """Тип оценки (Устный ответ, Домашняя работа и т.д.)"""
    title = models.CharField(max_length=100, verbose_name='Название типа')
    short_title = models.CharField(max_length=20, verbose_name='Короткое название')
    weight = models.FloatField(
        default=1.0,
        verbose_name='Вес оценки',
        help_text='Используется для расчета средневзвешенного балла'
    )
    color = models.CharField(
        max_length=20,
        default='#007bff',
        verbose_name='Цвет в интерфейсе'
    )
    description = models.TextField(blank=True, verbose_name='Описание')
    is_default = models.BooleanField(default=False, verbose_name='Тип по умолчанию')
    order = models.IntegerField(default=0, verbose_name='Порядок отображения')

    class Meta:
        verbose_name = 'Тип оценки'
        verbose_name_plural = 'Типы оценок'
        ordering = ['order', 'title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Если отмечаем как тип по умолчанию, снимаем флаг с других
        if self.is_default:
            GradeType.objects.filter(is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class GradeColumn(models.Model):
    """Тип оценки (столбец в журнале) - например: Устный ответ, Домашняя работа и т.д."""
    title = models.CharField(max_length=100, verbose_name='Название столбца')
    short_title = models.CharField(max_length=20, verbose_name='Короткое название')
    description = models.TextField(blank=True, verbose_name='Описание')
    weight = models.FloatField(
        default=1.0,
        verbose_name='Вес оценки',
        help_text='Используется для расчета средневзвешенного балла'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    order = models.IntegerField(default=0, verbose_name='Порядок отображения')

    class Meta:
        verbose_name = 'Тип оценки (столбец)'
        verbose_name_plural = 'Типы оценок (столбцы)'
        ordering = ['order', 'title']

    def __str__(self):
        return self.title


class LessonGradeColumn(models.Model):
    """Связь урока с типом оценки (какие столбцы есть в этом уроке)"""
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='grade_columns_relation',
        verbose_name='Урок'
    )
    grade_column = models.ForeignKey(
        GradeColumn,
        on_delete=models.CASCADE,
        verbose_name='Тип оценки'
    )
    is_required = models.BooleanField(
        default=False,
        verbose_name='Обязательный столбец'
    )
    order = models.IntegerField(default=0, verbose_name='Порядок в уроке')

    class Meta:
        verbose_name = 'Столбец урока'
        verbose_name_plural = 'Столбцы уроков'
        ordering = ['order']
        unique_together = ['lesson', 'grade_column']

    def __str__(self):
        return f'{self.lesson} - {self.grade_column}'


class StudentMark(models.Model):
    """Оценка ученика в конкретном столбце урока"""
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='student_marks',
        verbose_name='Ученик'
    )
    lesson_grade_column = models.ForeignKey(
        LessonGradeColumn,
        on_delete=models.CASCADE,
        related_name='marks',
        verbose_name='Столбец урока'
    )
    value = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка'
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
        verbose_name = 'Оценка ученика'
        verbose_name_plural = 'Оценки учеников'
        unique_together = ['student', 'lesson_grade_column']
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['student', 'created_at']),
        ]

    def __str__(self):
        return f'{self.student} - {self.value}'

    @property
    def lesson(self):
        return self.lesson_grade_column.lesson

    @property
    def grade_column(self):
        return self.lesson_grade_column.grade_column

    @property
    def weight(self):
        return self.grade_column.weight


class LessonColumn(models.Model):
    """Столбец оценки в уроке"""
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='columns',
        verbose_name='Урок'
    )
    grade_type = models.ForeignKey(
        GradeType,
        on_delete=models.PROTECT,
        related_name='lesson_columns',
        verbose_name='Тип оценки'
    )
    title = models.CharField(max_length=100, verbose_name='Название столбца')
    order = models.IntegerField(default=0, verbose_name='Порядок в уроке')
    is_visible = models.BooleanField(default=True, verbose_name='Отображать в журнале')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Столбец урока'
        verbose_name_plural = 'Столбцы уроков'
        ordering = ['order', 'created_at']
        unique_together = ['lesson', 'grade_type']

    def __str__(self):
        return f'{self.lesson} - {self.title}'

    def save(self, *args, **kwargs):
        # Если title не указан, используем название типа оценки
        if not self.title and self.grade_type:
            self.title = self.grade_type.title
        super().save(*args, **kwargs)


class StudentGrade(models.Model):
    """Оценка ученика в столбце урока"""
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='grades',
        verbose_name='Ученик'
    )
    lesson_column = models.ForeignKey(
        LessonColumn,
        on_delete=models.CASCADE,
        related_name='grades',
        verbose_name='Столбец урока'
    )
    value = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка'
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
        verbose_name = 'Оценка ученика'
        verbose_name_plural = 'Оценки учеников'
        unique_together = ['student', 'lesson_column']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'lesson_column']),
            models.Index(fields=['lesson_column', 'student']),
        ]

    def __str__(self):
        return f'{self.student} - {self.value}'

    @property
    def lesson(self):
        return self.lesson_column.lesson

    @property
    def grade_type(self):
        return self.lesson_column.grade_type

    @property
    def weight(self):
        return self.grade_type.weight


# Обновляем модели четвертных и годовых оценок
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
        null=True,
        blank=True,
        verbose_name='Четвертная оценка'
    )
    calculated_grade = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Расчетный балл'
    )
    calculation_details = models.JSONField(
        default=dict,
        verbose_name='Детали расчета'
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

    def __str__(self):
        return f'{self.student} - {self.subject} ({self.quarter}): {self.grade or "-"}'

    def calculate_grade(self):
        """Рассчитывает четвертную оценку на основе всех оценок за четверть"""
        from django.db.models import Avg, Sum, Count

        # Получаем все оценки студента по этому предмету в этой четверти
        grades = StudentGrade.objects.filter(
            student=self.student,
            lesson_column__lesson__subject=self.subject,
            lesson_column__lesson__quarter=self.quarter
        ).select_related('lesson_column__grade_type')

        if not grades.exists():
            self.calculated_grade = None
            self.calculation_details = {'total_grades': 0}
            return None

        # Рассчитываем средневзвешенный балл
        total_weighted = 0
        total_weight = 0
        grades_by_type = {}

        for grade in grades:
            weight = grade.weight
            total_weighted += grade.value * weight
            total_weight += weight

            # Группируем по типам оценок
            type_name = grade.grade_type.title
            if type_name not in grades_by_type:
                grades_by_type[type_name] = {
                    'count': 0,
                    'total': 0,
                    'weight': weight
                }
            grades_by_type[type_name]['count'] += 1
            grades_by_type[type_name]['total'] += grade.value

        if total_weight > 0:
            self.calculated_grade = round(total_weighted / total_weight, 2)

            # Рассчитываем предложенную оценку
            raw_grade = self.calculated_grade
            if raw_grade >= 4.5:
                suggested = 5
            elif raw_grade >= 3.5:
                suggested = 4
            elif raw_grade >= 2.5:
                suggested = 3
            elif raw_grade >= 1.5:
                suggested = 2
            else:
                suggested = 1
        else:
            self.calculated_grade = None
            suggested = None

        # Сохраняем детали расчета
        self.calculation_details = {
            'total_grades': grades.count(),
            'total_weight': total_weight,
            'average': self.calculated_grade,
            'suggested_grade': suggested,
            'grades_by_type': grades_by_type,
            'calculation_date': timezone.now().isoformat()
        }

        return suggested


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
        null=True,
        blank=True,
        verbose_name='Годовая оценка'
    )
    calculated_grade = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Расчетный балл'
    )
    calculation_method = models.CharField(
        max_length=20,
        choices=[
            ('AVERAGE', 'Среднее арифметическое'),
            ('MANUAL', 'Ручной ввод'),
        ],
        default='AVERAGE',
        verbose_name='Метод расчета'
    )
    calculation_details = models.JSONField(
        default=dict,
        verbose_name='Детали расчета'
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

    def __str__(self):
        return f'{self.student} - {self.subject} ({self.academic_year}): {self.grade or "-"}'
