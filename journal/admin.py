# journal/admin.py
from django.contrib import admin
from django.db import models
from django.db.models import Count, Avg
from .models import (
    GradeType, LessonColumn, StudentGrade,
    QuarterlyGrade, YearlyGrade, Attendance, Homework
)


@admin.register(GradeType)
class GradeTypeAdmin(admin.ModelAdmin):
    list_display = ('title', 'short_title', 'weight', 'color', 'is_default', 'order')
    list_filter = ('is_default',)
    search_fields = ('title', 'short_title')
    ordering = ('order', 'title')
    list_editable = ('weight', 'color', 'order', 'is_default')

    def get_queryset(self, request):
        return super().get_queryset(request)


@admin.register(LessonColumn)
class LessonColumnAdmin(admin.ModelAdmin):
    list_display = ('id', 'lesson_display', 'grade_type', 'title', 'order', 'is_visible', 'created_at')
    list_filter = ('is_visible', 'lesson__quarter', 'lesson__subject', 'grade_type')
    search_fields = ('title', 'lesson__subject__title', 'grade_type__title')
    raw_id_fields = ('lesson', 'grade_type')
    list_editable = ('title', 'order', 'is_visible')
    ordering = ('lesson', 'order')

    def lesson_display(self, obj):
        if obj.lesson:
            return f"{obj.lesson.date} - {obj.lesson.subject}"
        return '-'

    lesson_display.short_description = 'Урок'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('lesson__subject', 'grade_type')


@admin.register(StudentGrade)
class StudentGradeAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'value', 'grade_type_display', 'lesson_display',
                    'teacher_display', 'created_at', 'updated_at')
    list_filter = ('value', 'lesson_column__lesson__quarter',
                   'lesson_column__lesson__subject')
    search_fields = ('student__user__last_name', 'student__user__first_name',
                     'teacher__user__last_name', 'comment')
    raw_id_fields = ('student', 'lesson_column', 'teacher')
    list_editable = ('value',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

    def grade_type_display(self, obj):
        if obj.lesson_column and obj.lesson_column.grade_type:
            return obj.lesson_column.grade_type.title
        return '-'

    grade_type_display.short_description = 'Тип оценки'

    def lesson_display(self, obj):
        if obj.lesson_column and obj.lesson_column.lesson:
            return f"{obj.lesson_column.lesson.date} - {obj.lesson_column.lesson.subject}"
        return '-'

    lesson_display.short_description = 'Урок'

    def teacher_display(self, obj):
        if obj.teacher and obj.teacher.user:
            return obj.teacher.user.get_full_name()
        return '-'

    teacher_display.short_description = 'Учитель'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student__user',
            'lesson_column__lesson__subject',
            'lesson_column__grade_type',
            'teacher__user'
        )


@admin.register(QuarterlyGrade)
class QuarterlyGradeAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'subject', 'quarter', 'grade',
                    'calculated_grade', 'is_finalized', 'finalized_by_display', 'finalized_at')
    list_filter = ('is_finalized', 'quarter', 'subject')
    search_fields = ('student__user__last_name', 'student__user__first_name',
                     'subject__title', 'comment')
    raw_id_fields = ('student', 'subject', 'quarter', 'finalized_by')
    readonly_fields = ('calculated_grade', 'calculation_details',
                       'finalized_at')
    list_editable = ('grade', 'is_finalized')

    def finalized_by_display(self, obj):
        if obj.finalized_by and obj.finalized_by.user:
            return obj.finalized_by.user.get_full_name()
        return '-'

    finalized_by_display.short_description = 'Утвердил'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student__user',
            'subject',
            'quarter',
            'finalized_by__user'
        )

    def save_model(self, request, obj, form, change):
        if not obj.finalized_by and obj.is_finalized:
            obj.finalized_by = request.user.teacher_profile
        obj.save()


@admin.register(YearlyGrade)
class YearlyGradeAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'subject', 'academic_year', 'grade',
                    'calculation_method', 'is_finalized', 'finalized_by_display', 'finalized_at')
    list_filter = ('is_finalized', 'academic_year', 'calculation_method')
    search_fields = ('student__user__last_name', 'student__user__first_name',
                     'subject__title', 'comment')
    raw_id_fields = ('student', 'subject', 'academic_year', 'finalized_by')
    readonly_fields = ('calculated_grade', 'calculation_details',
                       'finalized_at')
    list_editable = ('grade', 'calculation_method', 'is_finalized')
    # filter_horizontal = ('quarterly_grades',)

    def finalized_by_display(self, obj):
        if obj.finalized_by and obj.finalized_by.user:
            return obj.finalized_by.user.get_full_name()
        return '-'

    finalized_by_display.short_description = 'Утвердил'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student__user',
            'subject',
            'academic_year',
            'finalized_by__user'
        )

    def save_model(self, request, obj, form, change):
        if not obj.finalized_by and obj.is_finalized:
            obj.finalized_by = request.user.teacher_profile
        obj.save()


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'student_display', 'lesson_display', 'status', 'note')
    list_filter = ('status', 'lesson__date')
    search_fields = ('student__user__last_name', 'student__user__first_name',
                     'lesson__subject__title', 'note')
    raw_id_fields = ('student', 'lesson')
    list_editable = ('status', 'note')

    def student_display(self, obj):
        if obj.student and obj.student.user:
            return obj.student.user.get_full_name()
        return '-'

    student_display.short_description = 'Ученик'

    def lesson_display(self, obj):
        if obj.lesson:
            return f"{obj.lesson.date} - {obj.lesson.subject}"
        return '-'

    lesson_display.short_description = 'Урок'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student__user',
            'lesson__subject'
        )


@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    list_display = ('id', 'lesson_display', 'deadline', 'created_at', 'has_attachments')
    list_filter = ('deadline', 'lesson__subject')
    search_fields = ('content', 'lesson__subject__title')
    raw_id_fields = ('lesson',)
    list_editable = ('deadline',)
    readonly_fields = ('created_at',)

    def lesson_display(self, obj):
        if obj.lesson:
            return f"{obj.lesson.date} - {obj.lesson.subject} - {obj.lesson.class_group}"
        return '-'

    lesson_display.short_description = 'Урок'

    def has_attachments(self, obj):
        return bool(obj.attachments)

    has_attachments.boolean = True
    has_attachments.short_description = 'Есть файлы'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('lesson__subject', 'lesson__class_group')


# Админ-панель для массовых операций с оценками
class GradeManagementAdmin(admin.ModelAdmin):
    """Админ-панель для управления оценками"""
    actions = ['recalculate_quarterly_grades', 'recalculate_yearly_grades']

    def recalculate_quarterly_grades(self, request, queryset):
        for qg in queryset:
            qg.save()  # save() вызывает пересчет
        self.message_user(request, f"Пересчитано {queryset.count()} четвертных оценок")

    recalculate_quarterly_grades.short_description = "Пересчитать выбранные четвертные оценки"

    def recalculate_yearly_grades(self, request, queryset):
        for yg in queryset:
            yg.save()  # save() вызывает пересчет
        self.message_user(request, f"Пересчитано {queryset.count()} годовых оценок")

    recalculate_yearly_grades.short_description = "Пересчитать выбранные годовые оценки"


# Перерегистрируем модели с кастомной админ-панелью
# admin.site.unregister(QuarterlyGrade)
# admin.site.unregister(YearlyGrade)
# admin.site.register(QuarterlyGrade, GradeManagementAdmin)
# admin.site.register(YearlyGrade, GradeManagementAdmin)


# Дополнительные админ-интерфейсы для удобства
class StudentGradeInline(admin.TabularInline):
    model = StudentGrade
    extra = 0
    fields = ('student', 'value', 'comment', 'teacher')
    raw_id_fields = ('student', 'teacher')
    can_delete = True
    show_change_link = True

class LessonColumnInline(admin.TabularInline):
    model = LessonColumn
    extra = 1
    fields = ('grade_type', 'title', 'order', 'is_visible')
    raw_id_fields = ('grade_type',)


# Добавляем Inline в админку уроков
from school_structure.models import Lesson


class LessonAdmin(admin.ModelAdmin):
    list_display = ('date', 'subject', 'class_group', 'teacher', 'lesson_number', 'topic')
    list_filter = ('date', 'subject', 'class_group', 'quarter')
    search_fields = ('topic', 'subject__title', 'class_group__name')
    inlines = [LessonColumnInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('subject', 'class_group', 'teacher__user')


# Перерегистрируем Lesson с новой админкой
# admin.site.unregister(Lesson)
# admin.site.register(Lesson, LessonAdmin)


# Дополнительная статистика в админке
class GradeStatsAdmin(admin.ModelAdmin):
    """Админка для просмотра статистики оценок"""
    change_list_template = 'admin/grade_stats_change_list.html'

    def changelist_view(self, request, extra_context=None):
        from django.db.models import Avg

        response = super().changelist_view(request, extra_context=extra_context)

        # Статистика по оценкам
        grade_stats = StudentGrade.objects.aggregate(
            total=Count('id'),
            avg=Avg('value'),
            five=Count('id', filter=models.Q(value=5)),
            four=Count('id', filter=models.Q(value=4)),
            three=Count('id', filter=models.Q(value=3)),
            two=Count('id', filter=models.Q(value=2)),
            one=Count('id', filter=models.Q(value=1))
        )

        # Статистика по типам оценок с средним баллом
        from django.db.models import Avg
        type_stats = GradeType.objects.annotate(
            count=Count('lessoncolumn__grades'),
            avg_grade=Avg('lessoncolumn__grades__value')
        ).order_by('-count')

        if not hasattr(response, 'context_data'):
            response.context_data = {}

        response.context_data['grade_stats'] = grade_stats
        response.context_data['type_stats'] = type_stats

        return response


# Регистрируем админку для статистики
# admin.site.register(StudentGrade, GradeStatsAdmin)