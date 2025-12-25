from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import TeacherProfile
import datetime


class AcademicYear(models.Model):
    """Учебный год"""
    year = models.CharField(max_length=9, verbose_name='Учебный год',
                            help_text='Например: 2024-2025')
    start_date = models.DateField(verbose_name='Начало учебного года')
    end_date = models.DateField(verbose_name='Окончание учебного года')
    is_current = models.BooleanField(default=False, verbose_name='Текущий учебный год')

    class Meta:
        verbose_name = 'Учебный год'
        verbose_name_plural = 'Учебные годы'
        ordering = ['-start_date']

    def __str__(self):
        return self.year

    def save(self, *args, **kwargs):
        # Если отмечаем текущий год, снимаем флаг с других
        if self.is_current:
            AcademicYear.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


class Quarter(models.Model):
    """Четверть (триместр)"""
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='quarters',
        verbose_name='Учебный год'
    )
    number = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        verbose_name='Номер четверти'
    )
    name = models.CharField(max_length=50, verbose_name='Название',
                            help_text='Например: "I четверть" или "Осенний триместр"')
    start_date = models.DateField(verbose_name='Начало четверти')
    end_date = models.DateField(verbose_name='Окончание четверти')
    is_current = models.BooleanField(default=False, verbose_name='Текущая четверть')

    class Meta:
        verbose_name = 'Четверть'
        verbose_name_plural = 'Четверти'
        ordering = ['academic_year', 'number']
        unique_together = ['academic_year', 'number']

    def __str__(self):
        return f'{self.name} ({self.academic_year})'

    @property
    def week_count(self):
        """Количество учебных недель в четверти"""
        from dateutil.relativedelta import relativedelta
        weeks = 0

        current_date = self.start_date
        while self.start_date and current_date <= self.end_date:
            # Считаем только понедельники как начало учебных недель
            if current_date.weekday() == 0:
                weeks += 1
            current_date += datetime.timedelta(days=1)
        return weeks or 1  # минимум 1 неделя


    def save(self, *args, **kwargs):
        # Проверяем пересечение дат с другими четвертями
        overlapping = Quarter.objects.filter(
            academic_year=self.academic_year
        ).exclude(pk=self.pk).filter(
            start_date__lte=self.end_date,
            end_date__gte=self.start_date
        )
        if overlapping.exists():
            raise ValueError("Даты четверти пересекаются с существующей четвертью")

        # Если отмечаем текущую четверть, снимаем флаг с других
        if self.is_current:
            Quarter.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


class ClassGroup(models.Model):
    """Класс (учебная группа)"""
    name = models.CharField(max_length=20, verbose_name='Название класса')
    year_of_study = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(11)],
        verbose_name='Год обучения'
    )
    classroom_teacher = models.ForeignKey(
        'users.TeacherProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_groups',
        verbose_name='Классный руководитель'
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='class_groups',
        verbose_name='Учебный год'
    )
    students_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество учеников'
    )

    class Meta:
        verbose_name = 'Класс'
        verbose_name_plural = 'Классы'
        ordering = ['academic_year', 'year_of_study', 'name']
        unique_together = ['name', 'academic_year']

    def __str__(self):
        return f'{self.year_of_study}-{self.name} ({self.academic_year})'

    def save(self, *args, **kwargs):
        # Обновляем количество учеников при сохранении
        if self.pk:
            from users.models import StudentProfile
            self.students_count = StudentProfile.objects.filter(
                class_group=self
            ).count()
        super().save(*args, **kwargs)


class Subject(models.Model):
    """Учебный предмет"""
    title = models.CharField(max_length=100, verbose_name='Название предмета')
    short_title = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Короткое название',
        help_text='Например: "Матем." для "Математики"'
    )
    description = models.TextField(blank=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предметы'
        ordering = ['title']

    def __str__(self):
        return self.title


class SubjectHours(models.Model):
    """Количество часов предмета в неделю для класса"""
    class_group = models.ForeignKey(
        ClassGroup,
        on_delete=models.CASCADE,
        related_name='subject_hours',
        verbose_name='Класс'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='class_hours',
        verbose_name='Предмет'
    )
    hours_per_week = models.PositiveIntegerField(
        default=2,
        verbose_name='Часов в неделю'
    )

    class Meta:
        verbose_name = 'Нагрузка по предмету в классе'
        verbose_name_plural = 'Нагрузки по предметам в классах'
        unique_together = ['class_group', 'subject']
        ordering = ['class_group', 'subject']

    def __str__(self):
        return f'{self.class_group} - {self.subject}: {self.hours_per_week} ч/нед'


class TeacherWorkload(models.Model):
    """Нагрузка учителя (распределение часов)"""
    teacher = models.ForeignKey(
        'users.TeacherProfile',
        on_delete=models.CASCADE,
        related_name='workloads',
        verbose_name='Учитель'
    )
    subject_hours = models.ForeignKey(
        SubjectHours,
        on_delete=models.CASCADE,
        related_name='teacher_workloads',
        verbose_name='Предмет и класс'
    )
    quarter = models.ForeignKey(
        Quarter,
        on_delete=models.CASCADE,
        related_name='teacher_workloads',
        verbose_name='Четверть'
    )
    hours_per_week = models.PositiveIntegerField(
        verbose_name='Часов в неделю для учителя'
    )
    is_substitute = models.BooleanField(
        default=False,
        verbose_name='Замещение'
    )
    substitute_for = models.ForeignKey(
        'users.TeacherProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='substituted_by',
        verbose_name='Заменяет учителя'
    )
    notes = models.TextField(blank=True, verbose_name='Примечания')

    class Meta:
        verbose_name = 'Нагрузка учителя'
        verbose_name_plural = 'Нагрузки учителей'
        unique_together = ['teacher', 'subject_hours', 'quarter']
        ordering = ['quarter', 'teacher']

    def __str__(self):
        return f'{self.teacher} - {self.subject_hours.subject} ({self.quarter})'

    def clean(self):
        from django.core.exceptions import ValidationError
        # Проверяем, что нагрузка учителя не превышает общее количество часов по предмету
        if self.hours_per_week > self.subject_hours.hours_per_week:
            raise ValidationError(
                f'Нагрузка учителя ({self.hours_per_week}) не может превышать '
                f'общее количество часов по предмету ({self.subject_hours.hours_per_week})'
            )

        # Проверяем, что четверть относится к тому же учебному году, что и класс
        if self.quarter.academic_year != self.subject_hours.class_group.academic_year:
            raise ValidationError(
                'Четверть должна относиться к тому же учебному году, что и класс'
            )

    @property
    def total_hours_in_quarter(self):
        """Общее количество часов в четверти"""
        return self.hours_per_week * self.quarter.week_count


class Lesson(models.Model):
    """Урок"""
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Предмет'
    )
    teacher = models.ForeignKey(
        'users.TeacherProfile',
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Учитель'
    )
    class_group = models.ForeignKey(
        ClassGroup,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Класс'
    )
    quarter = models.ForeignKey(
        Quarter,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Четверть'
    )
    classroom = models.CharField(max_length=10, verbose_name='Кабинет')
    date = models.DateField(verbose_name='Дата урока')
    lesson_number = models.PositiveIntegerField(
        verbose_name='Номер урока',
        help_text='Порядковый номер урока в расписании дня'
    )
    start_time = models.TimeField(verbose_name='Время начала')
    end_time = models.TimeField(verbose_name='Время окончания')
    topic = models.CharField(max_length=200, blank=True, verbose_name='Тема урока')
    lesson_type = models.CharField(
        max_length=20,
        choices=[
            ('REGULAR', 'Обычный урок'),
            ('TEST', 'Контрольная работа'),
            ('LAB', 'Лабораторная работа'),
            ('PROJECT', 'Проектная работа'),
        ],
        default='REGULAR',
        verbose_name='Тип урока'
    )

    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['date', 'lesson_number']
        indexes = [
            models.Index(fields=['date', 'class_group']),
            models.Index(fields=['teacher', 'date']),
            models.Index(fields=['quarter', 'class_group']),
        ]

    def __str__(self):
        return f'{self.subject} - {self.class_group} ({self.date})'

    def save(self, *args, **kwargs):
        # Проверяем, что дата урока попадает в диапазон четверти
        if self.date < self.quarter.start_date or self.date > self.quarter.end_date:
            raise ValueError(
                f"Дата урока ({self.date}) выходит за пределы четверти "
                f"({self.quarter.start_date} - {self.quarter.end_date})"
            )
        super().save(*args, **kwargs)