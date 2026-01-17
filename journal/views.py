# journal/views_new.py
from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
import json

from users.decorators import teacher_required
from school_structure.models import Quarter, ClassGroup, Subject, Lesson, AcademicYear
from users.models import StudentProfile, TeacherProfile
from .models import (
    GradeColumn, LessonGradeColumn, StudentMark,
    QuarterlyGrade, YearlyGrade
)


@login_required
@teacher_required
def teacher_journal(request):
    """Новая версия журнала учителя"""
    teacher = request.user.teacher_profile

    # Получаем текущую четверть
    try:
        current_quarter = Quarter.objects.get(is_current=True)
    except Quarter.DoesNotExist:
        current_quarter = None
        messages.warning(request, 'Текущая четверть не установлена')

    # Получаем предметы и классы учителя
    teacher_lessons = Lesson.objects.filter(
        teacher=teacher,
        quarter=current_quarter
    ).select_related('subject', 'class_group')

    # Группируем по предметам
    subjects_data = {}
    for lesson in teacher_lessons:
        subject = lesson.subject
        if subject.id not in subjects_data:
            subjects_data[subject.id] = {
                'subject': subject,
                'classes': set(),
                'lessons_count': 0
            }
        subjects_data[subject.id]['classes'].add(lesson.class_group)
        subjects_data[subject.id]['lessons_count'] += 1

    # Преобразуем set в list для шаблона
    for data in subjects_data.values():
        data['classes'] = list(data['classes'])
        data['classes_count'] = len(data['classes'])

    context = {
        'teacher': teacher,
        'current_quarter': current_quarter,
        'subjects_data': list(subjects_data.values()),
    }
    return render(request, 'journal/teacher_journal_new.html', context)


@login_required
@teacher_required
def class_subject_journal(request, class_id, subject_id, quarter_id=None):
    """Новая версия журнала по классу и предмету с поддержкой нескольких столбцов"""
    teacher = request.user.teacher_profile
    class_group = get_object_or_404(ClassGroup, id=class_id)
    subject = get_object_or_404(Subject, id=subject_id)

    # Определяем четверть
    if quarter_id:
        quarter = get_object_or_404(Quarter, id=quarter_id)
    else:
        try:
            quarter = Quarter.objects.get(is_current=True)
        except Quarter.DoesNotExist:
            messages.error(request, 'Текущая четверть не установлена')
            return redirect('journal:teacher_journal_new')

    # Проверяем права
    has_access = Lesson.objects.filter(
        teacher=teacher,
        class_group=class_group,
        subject=subject,
        quarter=quarter
    ).exists()

    if not has_access:
        raise PermissionDenied("У вас нет доступа к этому журналу")

    # Получаем учеников
    students = class_group.students.all().select_related('user').order_by(
        'user__last_name', 'user__first_name'
    )

    # Получаем уроки
    lessons = Lesson.objects.filter(
        class_group=class_group,
        subject=subject,
        quarter=quarter
    ).order_by('date', 'lesson_number')

    # Получаем стандартные типы оценок
    default_columns = GradeColumn.objects.filter(is_active=True).order_by('order')

    # Для каждого урока получаем его столбцы
    lessons_with_columns = []
    for lesson in lessons:
        # Получаем столбцы для этого урока
        lesson_columns = LessonGradeColumn.objects.filter(
            lesson=lesson
        ).select_related('grade_column').order_by('order')

        # Если столбцов нет, создаем стандартные
        if not lesson_columns.exists():
            for idx, col in enumerate(default_columns):
                lesson_col, created = LessonGradeColumn.objects.get_or_create(
                    lesson=lesson,
                    grade_column=col,
                    defaults={'order': idx * 10}
                )
                lesson_columns = LessonGradeColumn.objects.filter(
                    lesson=lesson
                ).select_related('grade_column').order_by('order')

        lessons_with_columns.append({
            'lesson': lesson,
            'columns': list(lesson_columns),
            'has_columns': lesson_columns.exists()
        })

    # Получаем все оценки для этих уроков
    lesson_column_ids = []
    for lesson_data in lessons_with_columns:
        for col in lesson_data['columns']:
            lesson_column_ids.append(col.id)

    # Получаем оценки учеников
    marks = StudentMark.objects.filter(
        lesson_grade_column_id__in=lesson_column_ids,
        student__in=students
    ).select_related('lesson_grade_column', 'teacher__user')

    # Организуем оценки для быстрого доступа
    marks_dict = {}
    for mark in marks:
        key = (mark.student_id, mark.lesson_grade_column_id)
        marks_dict[key] = mark

    # Получаем четвертные оценки
    quarterly_grades = QuarterlyGrade.objects.filter(
        student__in=students,
        subject=subject,
        quarter=quarter
    )
    quarterly_dict = {q.student_id: q for q in quarterly_grades}

    # Рассчитываем статистику для каждого ученика
    student_stats = []
    for student in students:
        # Получаем все оценки ученика за эту четверть
        student_marks = [m for m in marks if m.student_id == student.id]

        # Рассчитываем средневзвешенный балл
        total_weighted = 0
        total_weight = 0

        for mark in student_marks:
            total_weighted += mark.value * mark.weight
            total_weight += mark.weight

        avg_grade = total_weighted / total_weight if total_weight > 0 else None

        student_stats.append({
            'student': student,
            'avg_grade': round(avg_grade, 2) if avg_grade else None,
            'marks_count': len(student_marks),
            'quarterly_grade': quarterly_dict.get(student.id)
        })

    # Получаем другие четверти для переключения
    other_quarters = Quarter.objects.filter(
        academic_year=quarter.academic_year
    ).exclude(id=quarter.id).order_by('number')

    context = {
        'class_group': class_group,
        'subject': subject,
        'quarter': quarter,
        'students': students,
        'lessons_with_columns': lessons_with_columns,
        'marks_dict': marks_dict,
        'student_stats': student_stats,
        'other_quarters': other_quarters,
        'default_columns': default_columns,
    }

    return render(request, 'journal/class_subject_journal_new.html', context)


@csrf_exempt
@require_POST
@login_required
@teacher_required
def update_mark_attendance(request):
    """Обновление оценки ученика в столбце урока"""
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        lesson_column_id = data.get('lesson_column_id')
        value = data.get('value')
        comment = data.get('comment', '')

        student = get_object_or_404(StudentProfile, id=student_id)
        lesson_column = get_object_or_404(LessonGradeColumn, id=lesson_column_id)
        teacher = request.user.teacher_profile

        # Проверяем права
        if lesson_column.lesson.teacher != teacher:
            return JsonResponse({
                'success': False,
                'error': 'У вас нет прав для редактирования этого урока'
            })

        # Проверяем, что четверть не завершена
        if lesson_column.lesson.quarter.end_date < timezone.now().date():
            return JsonResponse({
                'success': False,
                'error': 'Четверть завершена, редактирование невозможно'
            })

        response_data = {'success': True}

        # Обработка оценки
        if value is None or value == '' or value == 'null':
            # Удаляем оценку
            deleted_count, _ = StudentMark.objects.filter(
                student=student,
                lesson_grade_column=lesson_column
            ).delete()
            response_data['mark'] = {
                'deleted': True,
                'deleted_count': deleted_count
            }
        else:
            # Проверяем значение
            try:
                value_int = int(value)
                if not (1 <= value_int <= 5):
                    return JsonResponse({
                        'success': False,
                        'error': 'Оценка должна быть от 1 до 5'
                    })

                # Создаем или обновляем оценку
                mark, created = StudentMark.objects.update_or_create(
                    student=student,
                    lesson_grade_column=lesson_column,
                    defaults={
                        'value': value_int,
                        'comment': comment,
                        'teacher': teacher
                    }
                )

                response_data['mark'] = {
                    'id': mark.id,
                    'value': mark.value,
                    'created': created,
                    'weight': mark.weight
                }
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Некорректное значение оценки'
                })

        # Пересчитываем четвертную оценку
        quarterly_grade, _ = QuarterlyGrade.objects.get_or_create(
            student=student,
            subject=lesson_column.lesson.subject,
            quarter=lesson_column.lesson.quarter
        )
        quarterly_grade.save(force_recalculate=True)

        response_data['quarterly_grade'] = {
            'id': quarterly_grade.id,
            'grade': quarterly_grade.grade,
            'calculated_grade': quarterly_grade.calculated_grade,
            'suggested_grade': quarterly_grade.calculation_details.get('suggested_grade')
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_POST
@login_required
@teacher_required
def manage_lesson_columns(request):
    """Управление столбцами урока"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        lesson_id = data.get('lesson_id')
        column_id = data.get('column_id', None)

        lesson = get_object_or_404(Lesson, id=lesson_id)
        teacher = request.user.teacher_profile

        # Проверяем права
        if lesson.teacher != teacher:
            return JsonResponse({
                'success': False,
                'error': 'У вас нет прав для редактирования этого урока'
            })

        if action == 'add_column':
            # Добавляем столбец к уроку
            column = get_object_or_404(GradeColumn, id=column_id)

            # Проверяем, нет ли уже такого столбца
            if LessonGradeColumn.objects.filter(lesson=lesson, grade_column=column).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Этот столбец уже добавлен к уроку'
                })

            # Определяем порядок
            max_order = LessonGradeColumn.objects.filter(
                lesson=lesson
            ).aggregate(models.Max('order'))['order__max'] or 0

            lesson_column = LessonGradeColumn.objects.create(
                lesson=lesson,
                grade_column=column,
                order=max_order + 10
            )

            return JsonResponse({
                'success': True,
                'lesson_column': {
                    'id': lesson_column.id,
                    'title': column.title,
                    'short_title': column.short_title,
                    'order': lesson_column.order
                }
            })

        elif action == 'remove_column':
            # Удаляем столбец из урока
            lesson_column = get_object_or_404(LessonGradeColumn, id=column_id)

            # Удаляем все оценки в этом столбце
            StudentMark.objects.filter(lesson_grade_column=lesson_column).delete()
            lesson_column.delete()

            return JsonResponse({'success': True})

        elif action == 'reorder_columns':
            # Изменяем порядок столбцов
            order_data = data.get('order', [])

            for item in order_data:
                lesson_column_id = item.get('id')
                new_order = item.get('order')

                try:
                    lesson_column = LessonGradeColumn.objects.get(
                        id=lesson_column_id,
                        lesson=lesson
                    )
                    lesson_column.order = new_order
                    lesson_column.save()
                except LessonGradeColumn.DoesNotExist:
                    continue

            return JsonResponse({'success': True})

        else:
            return JsonResponse({
                'success': False,
                'error': 'Неизвестное действие'
            })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def quarterly_grades():
    pass


@login_required
@teacher_required
def yearly_grades_view(request, class_id, subject_id, year_id=None):
    """Страница годовых оценок"""
    teacher = request.user.teacher_profile
    class_group = get_object_or_404(ClassGroup, id=class_id)
    subject = get_object_or_404(Subject, id=subject_id)

    # Определяем учебный год
    if year_id:
        academic_year = get_object_or_404(AcademicYear, id=year_id)
    else:
        try:
            academic_year = AcademicYear.objects.get(is_current=True)
        except AcademicYear.DoesNotExist:
            messages.error(request, 'Текущий учебный год не установлен')
            return redirect('journal:teacher_journal_new')

    # Проверяем права
    has_access = Lesson.objects.filter(
        teacher=teacher,
        class_group=class_group,
        subject=subject,
        quarter__academic_year=academic_year
    ).exists()

    if not has_access:
        raise PermissionDenied("У вас нет доступа")

    # Получаем учеников
    students = class_group.students.all().select_related('user').order_by(
        'user__last_name', 'user__first_name'
    )

    # Получаем четверти этого учебного года
    quarters = Quarter.objects.filter(
        academic_year=academic_year
    ).order_by('number')

    # Получаем четвертные оценки
    quarterly_grades_by_student = {}
    for student in students:
        q_grades = QuarterlyGrade.objects.filter(
            student=student,
            subject=subject,
            quarter__in=quarters
        ).select_related('quarter').order_by('quarter__number')
        quarterly_grades_by_student[student.id] = {q.quarter.number: q for q in q_grades}

    # Получаем или создаем годовые оценки
    yearly_grades = []
    for student in students:
        yearly_grade, created = YearlyGrade.objects.get_or_create(
            student=student,
            subject=subject,
            academic_year=academic_year,
            defaults={'calculation_method': 'AVERAGE'}
        )

        # Автоматически связываем четвертные оценки
        q_grades = QuarterlyGrade.objects.filter(
            student=student,
            subject=subject,
            quarter__in=quarters,
            grade__isnull=False
        )
        yearly_grade.quarterly_grades.set(q_grades)
        yearly_grade.save(force_recalculate=True)

        # Собираем данные по четвертям
        quarter_data = []
        for quarter in quarters:
            q_grade = quarterly_grades_by_student[student.id].get(quarter.number)
            quarter_data.append({
                'quarter': quarter,
                'grade': q_grade.grade if q_grade else None,
                'calculated': q_grade.calculated_grade if q_grade else None,
                'id': q_grade.id if q_grade else None
            })

        yearly_grades.append({
            'student': student,
            'yearly_grade': yearly_grade,
            'quarters': quarter_data,
            'can_edit': not yearly_grade.is_finalized
        })

    # Обработка формы
    if request.method == 'POST':
        saved_count = 0
        for data in yearly_grades:
            student = data['student']
            grade_key = f'grade_{student.id}'
            method_key = f'method_{student.id}'
            comment_key = f'comment_{student.id}'

            grade_value = request.POST.get(grade_key)
            method_value = request.POST.get(method_key, 'AVERAGE')
            comment_value = request.POST.get(comment_key, '')

            yearly_grade = data['yearly_grade']
            yearly_grade.calculation_method = method_value
            yearly_grade.comment = comment_value

            if grade_value and grade_value.isdigit():
                grade = int(grade_value)
                if 1 <= grade <= 5:
                    yearly_grade.grade = grade

            yearly_grade.save()
            saved_count += 1

        messages.success(request, f'Сохранено {saved_count} годовых оценок')
        return redirect('journal:yearly_grades',
                        class_id=class_id,
                        subject_id=subject_id,
                        year_id=academic_year.id)

    context = {
        'class_group': class_group,
        'subject': subject,
        'academic_year': academic_year,
        'quarters': quarters,
        'yearly_grades': yearly_grades,
    }

    return render(request, 'journal/yearly_grades.html', context)
