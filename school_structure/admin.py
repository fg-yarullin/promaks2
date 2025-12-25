from django.contrib import admin
from .models import (
    AcademicYear, Quarter, ClassGroup, Subject,
    SubjectHours, TeacherWorkload, Lesson
)


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('year', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current',)
    search_fields = ('year',)


@admin.register(Quarter)
class QuarterAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_year', 'start_date', 'end_date', 'is_current', 'week_count')
    list_filter = ('academic_year', 'is_current')
    search_fields = ('name', 'academic_year__year')
    readonly_fields = ('week_count',)


@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'year_of_study', 'academic_year',
                    'classroom_teacher', 'students_count')
    list_filter = ('academic_year', 'year_of_study')
    search_fields = ('name', 'classroom_teacher__user__first_name',
                     'classroom_teacher__user__last_name')
    raw_id_fields = ('classroom_teacher',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'short_title', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'short_title')


@admin.register(SubjectHours)
class SubjectHoursAdmin(admin.ModelAdmin):
    list_display = ('class_group', 'subject', 'hours_per_week')
    list_filter = ('class_group__academic_year', 'class_group__year_of_study')
    search_fields = ('subject__title', 'class_group__name')
    list_select_related = ('class_group', 'subject')


@admin.register(TeacherWorkload)
class TeacherWorkloadAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'subject_hours', 'quarter',
                    'hours_per_week', 'total_hours_in_quarter', 'is_substitute')
    list_filter = ('quarter', 'is_substitute', 'teacher')
    search_fields = ('teacher__user__first_name', 'teacher__user__last_name',
                     'subject_hours__subject__title')
    raw_id_fields = ('teacher', 'subject_hours', 'substitute_for')
    readonly_fields = ('total_hours_in_quarter',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('teacher', 'subject_hours', 'quarter', 'hours_per_week')
        }),
        ('Замещение', {
            'fields': ('is_substitute', 'substitute_for')
        }),
        ('Дополнительно', {
            'fields': ('notes', 'total_hours_in_quarter')
        }),
    )


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('date', 'lesson_number', 'subject', 'class_group',
                    'teacher', 'classroom', 'quarter')
    list_filter = ('quarter', 'date', 'class_group', 'teacher')
    search_fields = ('subject__title', 'class_group__name',
                     'teacher__user__first_name', 'teacher__user__last_name')
    date_hierarchy = 'date'
    list_select_related = ('subject', 'class_group', 'teacher', 'quarter')

    fieldsets = (
        ('Основная информация', {
            'fields': ('date', 'lesson_number', 'subject', 'class_group', 'quarter')
        }),
        ('Преподаватель и аудитория', {
            'fields': ('teacher', 'classroom')
        }),
        ('Время проведения', {
            'fields': ('start_time', 'end_time')
        }),
        ('Содержание', {
            'fields': ('topic', 'lesson_type')
        }),
    )
