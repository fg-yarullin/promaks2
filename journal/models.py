# journal/models.py
from datetime import timezone

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


# class GradeColumn(models.Model):
#     lesson = models.ForeignKey(
#         Lesson,
#         on_delete=models.CASCADE,
#         related_name='grade_columns',
#         verbose_name='Урок'
#     )
#     title = models.CharField(max_length=100, verbose_name='Название столбца')
#     order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
#
#     class Meta:
#         verbose_name = 'Столбец оценки'
#         verbose_name_plural = 'Столбцы оценок'
#         ordering = ['order', 'id']
#
#     def __str__(self):
#         return f'{self.lesson}: {self.title}'
#
# # class Mark(models.Model):
# #     class MarkType(models.TextChoices):
# #         EXAM = 'EXAM', 'Экзамен'
# #         TEST = 'TEST', 'Контрольная'
# #         CLASSWORK = 'CLASSWORK', 'Классная работа'
# #         HOMEWORK = 'HOMEWORK', 'Домашняя работа'
# #         ORAL = 'ORAL', 'Устный ответ'
# #
# #     student = models.ForeignKey(
# #         StudentProfile,
# #         on_delete=models.CASCADE,
# #         related_name='marks',
# #         verbose_name='Ученик'
# #     )
# #     lesson = models.ForeignKey(
# #         Lesson,
# #         on_delete=models.PROTECT,
# #         related_name='marks',
# #         verbose_name='Урок'
# #     )
# #     value = models.PositiveIntegerField(
# #         validators=[MinValueValidator(1), MaxValueValidator(5)],
# #         verbose_name='Оценка'
# #     )
# #     mark_type = models.CharField(
# #         max_length=20,
# #         choices=MarkType,
# #         default=MarkType.CLASSWORK,
# #         verbose_name='Тип оценки'
# #     )
# #     comment = models.TextField(blank=True, verbose_name='Комментарий')
# #     created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата выставления')
# #     updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
# #     teacher = models.ForeignKey(
# #         'users.TeacherProfile',
# #         on_delete=models.SET_NULL,
# #         null=True,
# #         verbose_name='Учитель'
# #     )
# #
# #     class Meta:
# #         verbose_name = 'Оценка'
# #         verbose_name_plural = 'Оценки'
# #         ordering = ['-created_at']
# #         indexes = [
# #             models.Index(fields=['student', 'created_at']),  # Для истории оценок ученика
# #             models.Index(fields=['lesson', 'mark_type']),
# #         ]
# #
# #     def __str__(self):
# #         return f'{self.student} - {self.value} ({self.get_mark_type_display()})'
# class Mark(models.Model):
#     grade_column = models.ForeignKey(
#         GradeColumn,
#         on_delete=models.CASCADE,
#         related_name='marks',
#         verbose_name='Столбец оценки'
#     )
#     student = models.ForeignKey(
#         StudentProfile,
#         on_delete=models.CASCADE,
#         related_name='marks',
#         verbose_name='Ученик'
#     )
#     value = models.PositiveIntegerField(
#         validators=[MinValueValidator(1), MaxValueValidator(5)],
#         verbose_name='Оценка'
#     )
#     comment = models.TextField(blank=True, verbose_name='Комментарий')
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата выставления')
#     updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
#     teacher = models.ForeignKey(
#         'users.TeacherProfile',
#         on_delete=models.SET_NULL,
#         null=True,
#         verbose_name='Учитель'
#     )
#
#     class Meta:
#         verbose_name = 'Оценка'
#         verbose_name_plural = 'Оценки'
#         unique_together = ['grade_column', 'student']
#         ordering = ['-created_at']
#
#     def __str__(self):
#         return f'{self.student} - {self.value}'
#
#
# class Homework(models.Model):
#     lesson = models.ForeignKey(
#         Lesson,
#         on_delete=models.PROTECT,
#         related_name='homeworks',
#         verbose_name='Урок'
#     )
#     content = models.TextField(verbose_name='Содержание задания')
#     attachments = models.FileField(
#         upload_to='homework_attachments/',
#         blank=True,
#         null=True,
#         verbose_name='Прикрепленные файлы'
#     )
#     deadline = models.DateTimeField(verbose_name='Срок выполнения')
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
#
#     class Meta:
#         verbose_name = 'Домашнее задание'
#         verbose_name_plural = 'Домашние задания'
#         ordering = ['deadline']
#         indexes = [
#             models.Index(fields=['lesson', 'deadline']),  # Для поиска актуальных ДЗ по классу
#         ]
#
#     def __str__(self):
#         return f'ДЗ для {self.lesson.class_group} до {self.deadline}'
#
#
# class QuarterlyGrade(models.Model):
#     """Четвертная оценка"""
#     student = models.ForeignKey(
#         StudentProfile,
#         on_delete=models.CASCADE,
#         related_name='quarterly_grades',
#         verbose_name='Ученик'
#     )
#     subject = models.ForeignKey(
#         Subject,
#         on_delete=models.CASCADE,
#         related_name='quarterly_grades',
#         verbose_name='Предмет'
#     )
#     quarter = models.ForeignKey(
#         Quarter,
#         on_delete=models.CASCADE,
#         related_name='quarterly_grades',
#         verbose_name='Четверть'
#     )
#     grade = models.PositiveIntegerField(
#         validators=[MinValueValidator(1), MaxValueValidator(5)],
#         verbose_name='Оценка за четверть'
#     )
#     calculated_grade = models.FloatField(
#         verbose_name='Расчетный балл',
#         help_text='Средний балл по текущим оценкам'
#     )
#     is_finalized = models.BooleanField(
#         default=False,
#         verbose_name='Оценка утверждена'
#     )
#     finalized_by = models.ForeignKey(
#         'users.TeacherProfile',
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         verbose_name='Утвердил'
#     )
#     finalized_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата утверждения')
#     comment = models.TextField(blank=True, verbose_name='Комментарий')
#
#     class Meta:
#         verbose_name = 'Четвертная оценка'
#         verbose_name_plural = 'Четвертные оценки'
#         unique_together = ['student', 'subject', 'quarter']
#         indexes = [
#             models.Index(fields=['student', 'quarter']),
#             models.Index(fields=['subject', 'quarter']),
#         ]
#
#     def __str__(self):
#         return f'{self.student} - {self.subject} ({self.quarter}): {self.grade}'
#
#     def save(self, *args, **kwargs):
#         # Автоматически рассчитываем средний балл
#         if not self.calculated_grade:
#             marks = Mark.objects.filter(
#                 student=self.student,
#                 lesson__subject=self.subject,
#                 lesson__quarter=self.quarter
#             )
#             avg = marks.aggregate(avg=Avg('value'))['avg']
#             self.calculated_grade = round(avg, 2) if avg else 0
#         super().save(*args, **kwargs)
#
#
# class YearlyGrade(models.Model):
#     """Годовая оценка"""
#     student = models.ForeignKey(
#         StudentProfile,
#         on_delete=models.CASCADE,
#         related_name='yearly_grades',
#         verbose_name='Ученик'
#     )
#     subject = models.ForeignKey(
#         Subject,
#         on_delete=models.CASCADE,
#         related_name='yearly_grades',
#         verbose_name='Предмет'
#     )
#     academic_year = models.ForeignKey(
#         AcademicYear,
#         on_delete=models.CASCADE,
#         related_name='yearly_grades',
#         verbose_name='Учебный год'
#     )
#     grade = models.PositiveIntegerField(
#         validators=[MinValueValidator(1), MaxValueValidator(5)],
#         verbose_name='Годовая оценка'
#     )
#     calculation_method = models.CharField(
#         max_length=20,
#         choices=[
#             ('AVERAGE', 'Среднее арифметическое'),
#             ('WEIGHTED', 'Взвешенное среднее'),
#             ('MANUAL', 'Ручной ввод'),
#         ],
#         default='AVERAGE',
#         verbose_name='Метод расчета'
#     )
#     quarterly_grades = models.ManyToManyField(
#         QuarterlyGrade,
#         blank=True,
#         verbose_name='Четвертные оценки',
#         help_text='Оценки за четверти, использованные для расчета'
#     )
#     is_finalized = models.BooleanField(default=False, verbose_name='Оценка утверждена')
#     finalized_by = models.ForeignKey(
#         'users.TeacherProfile',
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         verbose_name='Утвердил'
#     )
#     finalized_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата утверждения')
#     comment = models.TextField(blank=True, verbose_name='Комментарий')
#
#     class Meta:
#         verbose_name = 'Годовая оценка'
#         verbose_name_plural = 'Годовые оценки'
#         unique_together = ['student', 'subject', 'academic_year']
#         indexes = [
#             models.Index(fields=['student', 'academic_year']),
#             models.Index(fields=['subject', 'academic_year']),
#         ]
#
#     def __str__(self):
#         return f'{self.student} - {self.subject} ({self.academic_year}): {self.grade}'
#
#     def calculate_from_quarters(self):
#         """Рассчитывает годовую оценку на основе четвертных"""
#         quarters = self.quarterly_grades.all()
#         if quarters.exists():
#             avg = quarters.aggregate(avg=Avg('grade'))['avg'] - 0.1
#             # Округляем по правилам (2.6 -> 3, 2.5 -> 2)
#             return round(avg)
#         return None

# journal/models.py - добавляем в конец файла

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
        verbose_name='Расчетный балл',
        help_text='Средневзвешенный балл по текущим оценкам'
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
        indexes = [
            models.Index(fields=['student', 'quarter']),
            models.Index(fields=['subject', 'quarter']),
        ]

    def __str__(self):
        return f'{self.student} - {self.subject} ({self.quarter}): {self.grade or "-"}'

    def calculate_grade(self):
        """Рассчитывает четвертную оценку на основе всех оценок за четверть"""
        from django.db.models import Avg, Sum, Count, F

        # Получаем все оценки студента по этому предмету в этой четверти
        marks = StudentMark.objects.filter(
            student=self.student,
            lesson_grade_column__lesson__subject=self.subject,
            lesson_grade_column__lesson__quarter=self.quarter
        ).select_related('lesson_grade_column__grade_column')

        if not marks.exists():
            self.calculated_grade = None
            self.calculation_details = {'total_marks': 0}
            return None

        # Рассчитываем средневзвешенный балл
        total_weighted = 0
        total_weight = 0
        marks_by_type = {}

        for mark in marks:
            weight = mark.weight
            total_weighted += mark.value * weight
            total_weight += weight

            # Группируем по типам оценок
            col_name = mark.grade_column.title
            if col_name not in marks_by_type:
                marks_by_type[col_name] = {
                    'count': 0,
                    'total': 0,
                    'weight': weight
                }
            marks_by_type[col_name]['count'] += 1
            marks_by_type[col_name]['total'] += mark.value

        if total_weight > 0:
            self.calculated_grade = round(total_weighted / total_weight, 2)

            # Рассчитываем предложенную оценку (математическое округление)
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
            'total_marks': marks.count(),
            'total_weight': total_weight,
            'average': self.calculated_grade,
            'suggested_grade': suggested,
            'marks_by_type': marks_by_type,
            'calculation_date': timezone.now().isoformat()
        }

        return suggested

    def save(self, *args, **kwargs):
        # Автоматически рассчитываем оценку при сохранении
        if not self.calculated_grade or 'force_recalculate' in kwargs:
            if 'force_recalculate' in kwargs:
                kwargs.pop('force_recalculate')
            self.calculate_grade()

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
            ('AVERAGE', 'Среднее арифметическое четвертей'),
            ('MANUAL', 'Ручной ввод'),
        ],
        default='AVERAGE',
        verbose_name='Метод расчета'
    )
    calculation_details = models.JSONField(
        default=dict,
        verbose_name='Детали расчета'
    )
    quarterly_grades = models.ManyToManyField(
        QuarterlyGrade,
        blank=True,
        related_name='used_in_yearly',
        verbose_name='Четвертные оценки'
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
        return f'{self.student} - {self.subject} ({self.academic_year}): {self.grade or "-"}'

    def calculate_from_quarters(self):
        """Рассчитывает годовую оценку на основе четвертных"""
        quarters = self.quarterly_grades.filter(grade__isnull=False)

        if not quarters.exists():
            self.calculated_grade = None
            self.calculation_details = {'total_quarters': 0}
            return None

        # Получаем все четверти учебного года
        all_quarters = Quarter.objects.filter(academic_year=self.academic_year)

        # Рассчитываем среднее арифметическое
        total = 0
        quarter_grades_data = {}

        for qtr in all_quarters.order_by('number'):
            q_grade = quarters.filter(quarter=qtr).first()
            grade = q_grade.grade if q_grade else None
            quarter_grades_data[f'quarter_{qtr.number}'] = grade

            if grade:
                total += grade

        # Среднее арифметическое
        grades_count = len([g for g in quarter_grades_data.values() if g])
        if grades_count > 0:
            self.calculated_grade = total / grades_count

            # Математическое округление
            import math
            raw_grade = self.calculated_grade

            # Правила округления: 0.5 и больше - вверх, меньше 0.5 - вниз
            suggested = math.floor(raw_grade + 0.5)

            # Ограничиваем от 1 до 5
            suggested = max(1, min(5, suggested))
        else:
            self.calculated_grade = None
            suggested = None

        # Сохраняем детали расчета
        self.calculation_details = {
            'quarter_grades': quarter_grades_data,
            'average': self.calculated_grade,
            'suggested_grade': suggested,
            'calculation_method': 'AVERAGE',
            'calculation_date': timezone.now().isoformat()
        }

        return suggested

    def save(self, *args, **kwargs):
        # Автоматически рассчитываем годовую оценку
        if self.calculation_method == 'AVERAGE':
            if not self.calculated_grade or 'force_recalculate' in kwargs:
                if 'force_recalculate' in kwargs:
                    kwargs.pop('force_recalculate')
                self.calculate_from_quarters()

        super().save(*args, **kwargs)
