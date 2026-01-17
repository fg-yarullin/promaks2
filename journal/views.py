# journal/views.py

# journal/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Avg, Count, Q, Sum, F
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
import json
from datetime import datetime, timedelta

from users.decorators import teacher_required, class_teacher_required
from school_structure.models import Quarter, ClassGroup, Subject, Lesson, AcademicYear, TeacherWorkload
from users.models import StudentProfile, TeacherProfile
from .models import Mark, Attendance, Homework, QuarterlyGrade, YearlyGrade
from .forms import MarkForm, AttendanceForm, QuickGradeForm, QuarterlyGradeForm


@login_required
@teacher_required
def teacher_journal(request):
    """Главная страница журнала учителя - выбор класса и предмета"""
    teacher = request.user.teacher_profile

    # Получаем текущую четверть
    try:
        current_quarter = Quarter.objects.get(is_current=True)
    except Quarter.DoesNotExist:
        current_quarter = None
        messages.warning(request, 'Текущая четверть не установлена. Обратитесь к администратору.')

    # Получаем предметы учителя в текущей четверти
    teacher_subjects = Subject.objects.filter(
        lessons__teacher=teacher,
        lessons__quarter=current_quarter
    ).distinct()

    # Получаем классы по каждому предмету
    subjects_with_classes = []
    for subject in teacher_subjects:
        classes = ClassGroup.objects.filter(
            lessons__teacher=teacher,
            lessons__subject=subject,
            lessons__quarter=current_quarter
        ).distinct().annotate(
            student_count=Count('students')
        )

        if classes.exists():
            subjects_with_classes.append({
                'subject': subject,
                'classes': classes
            })

    # Альтернативно: получаем все классы учителя
    teacher_classes = ClassGroup.objects.filter(
        lessons__teacher=teacher,
        lessons__quarter=current_quarter
    ).distinct().annotate(
        student_count=Count('students'),
        subject_count=Count('lessons__subject', distinct=True)
    )

    # Получаем все доступные четверти
    if current_quarter:
        quarters = Quarter.objects.filter(
            academic_year=current_quarter.academic_year
        ).order_by('number')
    else:
        quarters = Quarter.objects.none()

    context = {
        'teacher': teacher,
        'current_quarter': current_quarter,
        'subjects_with_classes': subjects_with_classes,
        'teacher_classes': teacher_classes,
        'quarters': quarters,
    }
    return render(request, 'journal/teacher_journal.html', context)


@login_required
@teacher_required
def class_subject_journal(request, class_id, subject_id, quarter_id=None):
    """Журнал по конкретному классу и предмету"""
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
            return redirect('journal:teacher_journal')

    # Проверяем права доступа
    has_access = Lesson.objects.filter(
        teacher=teacher,
        class_group=class_group,
        subject=subject,
        quarter=quarter
    ).exists()

    if not has_access:
        raise PermissionDenied("У вас нет доступа к этому журналу")

    # Получаем учеников класса
    students = class_group.students.all().select_related('user').order_by(
        'user__last_name', 'user__first_name'
    )

    # Получаем уроки по предмету в этой четверти
    lessons = Lesson.objects.filter(
        class_group=class_group,
        subject=subject,
        quarter=quarter
    ).order_by('date', 'lesson_number')

    # Предварительная загрузка данных для оптимизации
    marks = Mark.objects.filter(
        lesson__in=lessons,
        student__in=students
    ).select_related('student', 'lesson')

    attendances = Attendance.objects.filter(
        lesson__in=lessons,
        student__in=students
    ).select_related('student', 'lesson')

    # Организуем данные для удобного доступа в шаблоне
    marks_dict = {}
    for mark in marks:
        if mark.student_id not in marks_dict:
            marks_dict[mark.student_id] = {}
        marks_dict[mark.student_id][mark.lesson_id] = mark

    attendance_dict = {}
    for att in attendances:
        if att.student_id not in attendance_dict:
            attendance_dict[att.student_id] = {}
        attendance_dict[att.student_id][att.lesson_id] = att

    # Рассчитываем средние баллы для каждого ученика
    student_stats = []
    for student in students:
        student_marks = [m for m in marks if m.student_id == student.id]
        avg_grade = None
        if student_marks:
            avg_grade = sum(m.value for m in student_marks) / len(student_marks)

        # Количество оценок каждого типа
        mark_types_count = {}
        for mark_type in Mark.MarkType.values:
            count = len([m for m in student_marks if m.mark_type == mark_type])
            if count > 0:
                mark_types_count[mark_type] = count

        student_stats.append({
            'student': student,
            'avg_grade': round(avg_grade, 2) if avg_grade else None,
            'marks_count': len(student_marks),
            'mark_types_count': mark_types_count
        })

    # Получаем другие четверти для переключения
    other_quarters = Quarter.objects.filter(
        academic_year=quarter.academic_year
    ).exclude(id=quarter.id).order_by('number')

    # Получаем все предметы в этом классе для навигации
    class_subjects = Subject.objects.filter(
        lessons__class_group=class_group,
        lessons__quarter=quarter,
        lessons__teacher=teacher
    ).distinct()

    context = {
        'class_group': class_group,
        'subject': subject,
        'quarter': quarter,
        'students': students,
        'lessons': lessons,
        'marks_dict': marks_dict,
        'attendance_dict': attendance_dict,
        'student_stats': student_stats,
        'other_quarters': other_quarters,
        'class_subjects': class_subjects,
        'attendance_statuses': Attendance.Status.choices,
        'mark_types': Mark.MarkType.choices,
    }

    return render(request, 'journal/class_subject_journal.html', context)


@csrf_exempt
@require_POST
@login_required
@teacher_required
def update_mark_attendance(request):
    """AJAX-обработчик для обновления оценок и посещаемости"""
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        lesson_id = data.get('lesson_id')
        mark_value = data.get('mark_value')
        attendance_status = data.get('attendance_status')
        mark_type = data.get('mark_type', 'CLASSWORK')
        comment = data.get('comment', '')

        student = get_object_or_404(StudentProfile, id=student_id)
        lesson = get_object_or_404(Lesson, id=lesson_id)
        teacher = request.user.teacher_profile

        # Проверяем права
        if lesson.teacher != teacher:
            return JsonResponse({
                'success': False,
                'error': 'У вас нет прав для редактирования этого урока'
            })

        # Проверяем, что четверть еще не завершена
        if lesson.quarter.end_date < timezone.now().date():
            return JsonResponse({
                'success': False,
                'error': 'Четверть завершена, редактирование невозможно'
            })

        response_data = {'success': True}

        # ОБРАБОТКА ОЦЕНКИ
        # Если mark_value не передано (None) или пустая строка - удаляем оценку
        if mark_value is None or mark_value == '':
            Mark.objects.filter(student=student, lesson=lesson).delete()
            response_data['mark'] = {'deleted': True}
        else:
            # Пытаемся преобразовать в целое число
            try:
                mark_value_int = int(mark_value)
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'error': 'Некорректное значение оценки'
                })

            if 1 <= mark_value_int <= 5:
                mark, created = Mark.objects.update_or_create(
                    student=student,
                    lesson=lesson,
                    defaults={
                        'value': mark_value_int,
                        'mark_type': mark_type,
                        'comment': comment,
                        'teacher': teacher
                    }
                )
                response_data['mark'] = {
                    'id': mark.id,
                    'value': mark.value,
                    'type': mark.mark_type,
                    'created': created
                }
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Оценка должна быть от 1 до 5'
                })

        # ОБРАБОТКА ПОСЕЩАЕМОСТИ
        if attendance_status is not None:
            if attendance_status == 'PRESENT':
                # Удаляем запись о посещаемости, если ученик присутствовал
                Attendance.objects.filter(student=student, lesson=lesson).delete()
                response_data['attendance'] = {'status': 'PRESENT', 'deleted': True}
            else:
                att, created = Attendance.objects.update_or_create(
                    student=student,
                    lesson=lesson,
                    defaults={
                        'status': attendance_status,
                        'note': data.get('attendance_note', '')
                    }
                )
                response_data['attendance'] = {
                    'id': att.id,
                    'status': att.status,
                    'display': att.get_status_display(),
                    'created': created
                }

        # Пересчитываем средний балл ученика по предмету
        avg_grade = Mark.objects.filter(
            student=student,
            lesson__subject=lesson.subject,
            lesson__quarter=lesson.quarter
        ).aggregate(avg=Avg('value'))['avg']

        response_data['average_grade'] = round(avg_grade, 2) if avg_grade else None

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_POST
@login_required
@teacher_required
def update_mark_attendance_old(request):
    """AJAX-обработчик для обновления оценок и посещаемости"""
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        lesson_id = data.get('lesson_id')
        mark_value = data.get('mark_value')
        attendance_status = data.get('attendance_status')
        mark_type = data.get('mark_type', 'CLASSWORK')
        comment = data.get('comment', '')

        student = get_object_or_404(StudentProfile, id=student_id)
        lesson = get_object_or_404(Lesson, id=lesson_id)
        teacher = request.user.teacher_profile

        # Проверяем права
        if lesson.teacher != teacher:
            return JsonResponse({
                'success': False,
                'error': 'У вас нет прав для редактирования этого урока'
            })

        # Проверяем, что четверть еще не завершена
        if lesson.quarter.end_date < timezone.now().date():
            return JsonResponse({
                'success': False,
                'error': 'Четверть завершена, редактирование невозможно'
            })

        response_data = {'success': True}

        # Обработка оценки
        if mark_value is not None:
            mark_value = int(mark_value) if str(mark_value).isdigit() else None

            if mark_value and 1 <= mark_value <= 5:
                # Создаем или обновляем оценку
                mark, created = Mark.objects.update_or_create(
                    student=student,
                    lesson=lesson,
                    defaults={
                        'value': mark_value,
                        'mark_type': mark_type,
                        'comment': comment,
                        'teacher': teacher
                    }
                )
                response_data['mark'] = {
                    'id': mark.id,
                    'value': mark.value,
                    'type': mark.mark_type,
                    'created': created
                }
            elif mark_value is None:
                # Удаляем оценку
                Mark.objects.filter(student=student, lesson=lesson).delete()
                response_data['mark'] = {'deleted': True}

        # Обработка посещаемости
        if attendance_status is not None:
            if attendance_status == 'PRESENT':
                # Удаляем запись о посещаемости, если ученик присутствовал
                Attendance.objects.filter(student=student, lesson=lesson).delete()
                response_data['attendance'] = {'status': 'PRESENT', 'deleted': True}
            else:
                att, created = Attendance.objects.update_or_create(
                    student=student,
                    lesson=lesson,
                    defaults={
                        'status': attendance_status,
                        'note': data.get('attendance_note', '')
                    }
                )
                response_data['attendance'] = {
                    'id': att.id,
                    'status': att.status,
                    'display': att.get_status_display(),
                    'created': created
                }

        # Пересчитываем средний балл ученика по предмету
        avg_grade = Mark.objects.filter(
            student=student,
            lesson__subject=lesson.subject,
            lesson__quarter=lesson.quarter
        ).aggregate(avg=Avg('value'))['avg']

        response_data['average_grade'] = round(avg_grade, 2) if avg_grade else None

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_student_stats(request, student_id, subject_id, quarter_id):
    """Получение статистики по ученику для AJAX-запросов"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Требуется авторизация'}, status=403)

    student = get_object_or_404(StudentProfile, id=student_id)
    subject = get_object_or_404(Subject, id=subject_id)
    quarter = get_object_or_404(Quarter, id=quarter_id)

    # Проверяем права доступа
    user = request.user
    if user.role == 'STUDENT' and user.student_profile != student:
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    elif user.role == 'TEACHER':
        # Проверяем, ведет ли учитель этот предмет
        if not user.teacher_profile.lessons.filter(
                subject=subject,
                quarter=quarter,
                class_group=student.class_group
        ).exists():
            return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    elif user.role == 'PARENT':
        # Проверяем, является ли родителем этого ученика
        if not user.parent_profile.children.filter(id=student_id).exists():
            return JsonResponse({'error': 'Доступ запрещен'}, status=403)

    # Получаем оценки ученика по предмету в четверти
    marks = Mark.objects.filter(
        student=student,
        lesson__subject=subject,
        lesson__quarter=quarter
    ).select_related('lesson', 'teacher__user').order_by('lesson__date')

    # Статистика по типам оценок
    marks_by_type = marks.values('mark_type').annotate(
        count=Count('id'),
        average=Avg('value')
    )

    # Посещаемость
    attendance = Attendance.objects.filter(
        student=student,
        lesson__subject=subject,
        lesson__quarter=quarter
    ).values('status').annotate(count=Count('id'))

    # Общая статистика
    total_marks = marks.count()
    avg_grade = marks.aggregate(avg=Avg('value'))['avg']

    # Прогресс по неделям
    weekly_progress = []
    if quarter.start_date and quarter.end_date:
        current_date = quarter.start_date
        week_num = 1

        while current_date <= quarter.end_date:
            week_end = current_date + timedelta(days=6)
            if week_end > quarter.end_date:
                week_end = quarter.end_date

            week_marks = marks.filter(
                lesson__date__range=[current_date, week_end]
            )
            week_avg = week_marks.aggregate(avg=Avg('value'))['avg']

            weekly_progress.append({
                'week': week_num,
                'start_date': current_date,
                'end_date': week_end,
                'marks_count': week_marks.count(),
                'average': round(week_avg, 2) if week_avg else None
            })

            current_date = week_end + timedelta(days=1)
            week_num += 1

    response_data = {
        'student': {
            'id': student.id,
            'name': student.user.get_full_name(),
            'class': str(student.class_group) if student.class_group else None
        },
        'subject': subject.title,
        'quarter': quarter.name,
        'stats': {
            'total_marks': total_marks,
            'average_grade': round(avg_grade, 2) if avg_grade else None,
            'marks_by_type': list(marks_by_type),
            'attendance': list(attendance),
        },
        'weekly_progress': weekly_progress,
        'recent_marks': list(marks.values(
            'value', 'mark_type', 'lesson__date', 'comment'
        ).order_by('-lesson__date')[:10])
    }

    return JsonResponse(response_data)


@login_required
@teacher_required
def quarterly_grades(request, class_id, subject_id, quarter_id):
    """Страница для выставления четвертных оценок"""
    teacher = request.user.teacher_profile
    class_group = get_object_or_404(ClassGroup, id=class_id)
    subject = get_object_or_404(Subject, id=subject_id)
    quarter = get_object_or_404(Quarter, id=quarter_id)

    # Проверяем права доступа
    has_access = Lesson.objects.filter(
        teacher=teacher,
        class_group=class_group,
        subject=subject,
        quarter=quarter
    ).exists()

    if not has_access:
        raise PermissionDenied("У вас нет доступа к этому журналу")

    # Проверяем, что четверть завершена (можно выставлять четвертные оценки)
    quarter_ended = quarter.end_date < timezone.now().date()

    # Получаем учеников класса
    students = class_group.students.all().select_related('user').order_by(
        'user__last_name', 'user__first_name'
    )

    # Получаем или создаем четвертные оценки
    quarterly_grades_list = []
    for student in students:
        # Получаем средний балл за четверть
        marks = Mark.objects.filter(
            student=student,
            lesson__subject=subject,
            lesson__quarter=quarter
        )

        avg_grade = marks.aggregate(avg=Avg('value'))['avg']
        marks_count = marks.count()

        # Получаем или создаем четвертную оценку
        quarterly_grade, created = QuarterlyGrade.objects.get_or_create(
            student=student,
            subject=subject,
            quarter=quarter,
            defaults={
                'calculated_grade': round(avg_grade, 2) if avg_grade else 0,
                'grade': None
            }
        )

        # Предлагаемая оценка на основе среднего балла
        suggested_grade = None
        if avg_grade:
            if avg_grade >= 4.5:
                suggested_grade = 5
            elif avg_grade >= 3.5:
                suggested_grade = 4
            elif avg_grade >= 2.5:
                suggested_grade = 3
            else:
                suggested_grade = 2

        quarterly_grades_list.append({
            'student': student,
            'marks_count': marks_count,
            'average_grade': round(avg_grade, 2) if avg_grade else None,
            'quarterly_grade': quarterly_grade,
            'suggested_grade': suggested_grade,
            'can_edit': not quarterly_grade.is_finalized or not quarter_ended
        })

    # Обработка формы
    if request.method == 'POST':
        if not quarter_ended:
            messages.warning(request, 'Четверть еще не завершена. Оценки будут сохранены как предварительные.')

        saved_count = 0
        for student_data in quarterly_grades_list:
            student = student_data['student']
            grade_key = f'grade_{student.id}'
            comment_key = f'comment_{student.id}'

            grade_value = request.POST.get(grade_key)
            comment_value = request.POST.get(comment_key, '')

            if grade_value and grade_value.isdigit():
                grade = int(grade_value)
                if 1 <= grade <= 5:
                    # Обновляем или создаем четвертную оценку
                    quarterly_grade, created = QuarterlyGrade.objects.update_or_create(
                        student=student,
                        subject=subject,
                        quarter=quarter,
                        defaults={
                            'grade': grade,
                            'comment': comment_value,
                            'is_finalized': quarter_ended,
                            'finalized_by': teacher if quarter_ended else None,
                            'finalized_at': timezone.now() if quarter_ended else None
                        }
                    )
                    saved_count += 1

        messages.success(request, f'Сохранено {saved_count} четвертных оценок')
        return redirect('journal:quarterly_grades',
                        class_id=class_id,
                        subject_id=subject_id,
                        quarter_id=quarter_id)

    context = {
        'class_group': class_group,
        'subject': subject,
        'quarter': quarter,
        'quarter_ended': quarter_ended,
        'quarterly_grades': quarterly_grades_list,
        'teacher': teacher,
    }

    return render(request, 'journal/quarterly_grades.html', context)

# from django.shortcuts import render, get_object_or_404, redirect
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.http import JsonResponse
# from django.utils import timezone
# from django.db.models import Avg, Count, Q, Sum
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_POST
# import json
# from datetime import datetime, timedelta
#
# # Импортируем декораторы из users
# from users.decorators import teacher_required, class_teacher_required, subject_teacher_required
#
# from school_structure.models import Quarter, ClassGroup, Subject, Lesson, AcademicYear
# from users.models import StudentProfile, TeacherProfile
# from .models import Mark, Attendance, Homework, QuarterlyGrade, YearlyGrade
# from .forms import MarkForm, AttendanceForm, QuickGradeForm, QuarterlyGradeForm
#
#
# @login_required
# @teacher_required
# def teacher_journal(request):
#     """Главная страница журнала учителя - выбор класса и предмета"""
#     teacher = request.user.teacher_profile
#
#     # Получаем текущую четверть
#     try:
#         current_quarter = Quarter.objects.get(is_current=True)
#     except Quarter.DoesNotExist:
#         current_quarter = None
#
#     # Получаем классы и предметы, которые ведет учитель
#     teacher_classes = ClassGroup.objects.filter(
#         lessons__teacher=teacher,
#         lessons__quarter=current_quarter
#     ).distinct()
#
#     teacher_subjects = Subject.objects.filter(
#         lessons__teacher=teacher,
#         lessons__quarter=current_quarter
#     ).distinct()
#
#     context = {
#         'teacher': teacher,
#         'current_quarter': current_quarter,
#         'classes': teacher_classes,
#         'subjects': teacher_subjects,
#     }
#     return render(request, 'journal/teacher_journal.html', context)
#
#
# @login_required
# @teacher_required
# def class_subject_journal(request, class_id, subject_id, quarter_id=None):
#     """Журнал по конкретному классу и предмету"""
#     teacher = request.user.teacher_profile
#     class_group = get_object_or_404(ClassGroup, id=class_id)
#     subject = get_object_or_404(Subject, id=subject_id)
#
#     # Определяем четверть
#     if quarter_id:
#         quarter = get_object_or_404(Quarter, id=quarter_id)
#     else:
#         try:
#             quarter = Quarter.objects.get(is_current=True)
#         except Quarter.DoesNotExist:
#             quarter = None
#
#     # Проверяем, ведет ли учитель этот предмет в этом классе в этой четверти
#     if not Lesson.objects.filter(
#             teacher=teacher,
#             class_group=class_group,
#             subject=subject,
#             quarter=quarter
#     ).exists():
#         messages.error(request, 'У вас нет доступа к этому журналу')
#         return redirect('journal:teacher_journal')
#
#     # Получаем учеников класса
#     students = class_group.students.all().order_by('user__last_name', 'user__first_name')
#
#     # Получаем уроки по предмету в этой четверти
#     lessons = Lesson.objects.filter(
#         class_group=class_group,
#         subject=subject,
#         quarter=quarter
#     ).order_by('date')
#
#     # Получаем оценки и посещаемость
#     marks_data = {}
#     attendance_data = {}
#
#     for student in students:
#         # Оценки студента
#         student_marks = Mark.objects.filter(
#             student=student,
#             lesson__in=lessons
#         ).select_related('lesson')
#
#         marks_data[student.id] = {mark.lesson_id: mark for mark in student_marks}
#
#         # Посещаемость студента
#         student_attendance = Attendance.objects.filter(
#             student=student,
#             lesson__in=lessons
#         ).select_related('lesson')
#
#         attendance_data[student.id] = {att.lesson_id: att for att in student_attendance}
#
#     # Рассчитываем средние баллы
#     avg_grades = Mark.objects.filter(
#         student__in=students,
#         lesson__in=lessons
#     ).values('student').annotate(
#         avg_grade=Avg('value'),
#         count_marks=Count('id')
#     )
#
#     avg_grades_dict = {item['student']: item['avg_grade'] for item in avg_grades}
#
#     # Получаем список четвертей для переключения
#     quarters = Quarter.objects.filter(
#         academic_year=class_group.academic_year
#     ).order_by('number')
#
#     context = {
#         'class_group': class_group,
#         'subject': subject,
#         'quarter': quarter,
#         'quarters': quarters,
#         'students': students,
#         'lessons': lessons,
#         'marks_data': marks_data,
#         'attendance_data': attendance_data,
#         'avg_grades_dict': avg_grades_dict,
#         'attendance_statuses': Attendance.Status.choices,
#     }
#     return render(request, 'journal/class_subject_journal.html', context)
#
#
# @csrf_exempt
# @require_POST
# @login_required
# @teacher_required
# def update_mark_attendance(request):
#     """Обновление оценки и посещаемости через AJAX"""
#     try:
#         data = json.loads(request.body)
#         student_id = data.get('student_id')
#         lesson_id = data.get('lesson_id')
#         mark_value = data.get('mark_value')
#         attendance_status = data.get('attendance_status')
#         attendance_note = data.get('attendance_note', '')
#
#         student = get_object_or_404(StudentProfile, id=student_id)
#         lesson = get_object_or_404(Lesson, id=lesson_id)
#         teacher = request.user.teacher_profile
#
#         # Проверяем, что урок принадлежит учителю
#         if lesson.teacher != teacher:
#             return JsonResponse({'success': False, 'error': 'Нет доступа'})
#
#         # Проверяем, не закончилась ли четверть
#         if lesson.quarter.end_date < timezone.now().date():
#             return JsonResponse({'success': False, 'error': 'Четверть завершена, редактирование невозможно'})
#
#         response_data = {'success': True}
#
#         # Обработка оценки
#         if mark_value is not None:
#             mark_value = int(mark_value) if mark_value else None
#             if mark_value:
#                 mark, created = Mark.objects.update_or_create(
#                     student=student,
#                     lesson=lesson,
#                     defaults={
#                         'value': mark_value,
#                         'teacher': teacher,
#                         'mark_type': 'CLASSWORK'
#                     }
#                 )
#                 response_data['mark'] = {
#                     'id': mark.id,
#                     'value': mark.value,
#                     'created': created
#                 }
#             else:
#                 # Удаляем оценку, если передано пустое значение
#                 Mark.objects.filter(student=student, lesson=lesson).delete()
#                 response_data['mark'] = {'deleted': True}
#
#         # Обработка посещаемости
#         if attendance_status is not None:
#             if attendance_status == 'PRESENT' or attendance_status == '':
#                 # Если присутствовал или пустая строка, удаляем запись о посещаемости
#                 Attendance.objects.filter(student=student, lesson=lesson).delete()
#                 response_data['attendance'] = {'status': 'PRESENT', 'deleted': True}
#             else:
#                 att, created = Attendance.objects.update_or_create(
#                     student=student,
#                     lesson=lesson,
#                     defaults={
#                         'status': attendance_status,
#                         'note': attendance_note
#                     }
#                 )
#                 response_data['attendance'] = {
#                     'id': att.id,
#                     'status': att.status,
#                     'display': att.get_status_display(),
#                     'created': created
#                 }
#
#         # Рассчитываем средний балл по предмету за четверть
#         avg = Mark.objects.filter(
#             student=student,
#             lesson__subject=lesson.subject,
#             lesson__quarter=lesson.quarter
#         ).aggregate(avg=Avg('value'))['avg']
#
#         response_data['average'] = round(avg, 2) if avg else None
#
#         return JsonResponse(response_data)
#
#     except Exception as e:
#         return JsonResponse({'success': False, 'error': str(e)})
#
#
# @login_required
# @teacher_required
# def get_student_stats(request, student_id, subject_id, quarter_id):
#     """Получение статистики по ученику"""
#     student = get_object_or_404(StudentProfile, id=student_id)
#     subject = get_object_or_404(Subject, id=subject_id)
#     quarter = get_object_or_404(Quarter, id=quarter_id)
#
#     marks = Mark.objects.filter(
#         student=student,
#         lesson__subject=subject,
#         lesson__quarter=quarter
#     ).order_by('lesson__date')
#
#     marks_list = list(marks.values('value', 'mark_type', 'lesson__date', 'comment'))
#
#     # Средний балл
#     avg_grade = marks.aggregate(avg=Avg('value'))['avg']
#
#     # Распределение по типам оценок
#     marks_by_type = marks.values('mark_type').annotate(
#         count=Count('id'),
#         avg=Avg('value')
#     )
#
#     # Посещаемость
#     attendance = Attendance.objects.filter(
#         student=student,
#         lesson__subject=subject,
#         lesson__quarter=quarter
#     ).values('status').annotate(count=Count('id'))
#
#     stats = {
#         'marks_count': marks.count(),
#         'avg_grade': round(avg_grade, 2) if avg_grade else None,
#         'marks_by_type': list(marks_by_type),
#         'attendance': list(attendance),
#         'recent_marks': marks_list[:5]  # последние 5 оценок
#     }
#
#     return JsonResponse(stats)
#
#
# @login_required
# @teacher_required
# def quarterly_grades(request, class_id, subject_id, quarter_id):
#     """Страница для выставления четвертных оценок"""
#     teacher = request.user.teacher_profile
#     class_group = get_object_or_404(ClassGroup, id=class_id)
#     subject = get_object_or_404(Subject, id=subject_id)
#     quarter = get_object_or_404(Quarter, id=quarter_id)
#
#     # Проверяем, что учитель имеет доступ
#     if not Lesson.objects.filter(
#             teacher=teacher,
#             class_group=class_group,
#             subject=subject,
#             quarter=quarter
#     ).exists():
#         messages.error(request, 'У вас нет доступа к этому журналу')
#         return redirect('journal:teacher_journal')
#
#     # Проверяем, что четверть завершена (можно выставлять четвертные оценки)
#     if quarter.end_date > timezone.now().date():
#         messages.warning(request, 'Четверть еще не завершена. Вы можете выставить предварительные оценки.')
#
#     # Получаем учеников
#     students = class_group.students.all().order_by('user__last_name')
#
#     # Рассчитываем средние баллы для каждого ученика
#     students_data = []
#     for student in students:
#         # Средний балл за четверть
#         avg_grade = Mark.objects.filter(
#             student=student,
#             lesson__subject=subject,
#             lesson__quarter=quarter
#         ).aggregate(avg=Avg('value'))['avg']
#
#         # Количество оценок
#         marks_count = Mark.objects.filter(
#             student=student,
#             lesson__subject=subject,
#             lesson__quarter=quarter
#         ).count()
#
#         # Получаем или создаем четвертную оценку
#         quarterly_grade, created = QuarterlyGrade.objects.get_or_create(
#             student=student,
#             subject=subject,
#             quarter=quarter,
#             defaults={
#                 'calculated_grade': round(avg_grade, 2) if avg_grade else 0
#             }
#         )
#
#         students_data.append({
#             'student': student,
#             'avg_grade': round(avg_grade, 2) if avg_grade else None,
#             'marks_count': marks_count,
#             'quarterly_grade': quarterly_grade,
#         })
#
#     if request.method == 'POST':
#         for student in students:
#             grade_key = f'grade_{student.id}'
#             comment_key = f'comment_{student.id}'
#
#             if grade_key in request.POST:
#                 grade_value = request.POST.get(grade_key)
#                 comment_value = request.POST.get(comment_key, '')
#
#                 if grade_value:
#                     quarterly_grade, created = QuarterlyGrade.objects.update_or_create(
#                         student=student,
#                         subject=subject,
#                         quarter=quarter,
#                         defaults={
#                             'grade': int(grade_value),
#                             'comment': comment_value,
#                             'finalized_by': teacher,
#                             'finalized_at': timezone.now(),
#                             'is_finalized': True
#                         }
#                     )
#                 else:
#                     # Если оценка удалена, снимаем флаг утверждения
#                     QuarterlyGrade.objects.filter(
#                         student=student,
#                         subject=subject,
#                         quarter=quarter
#                     ).update(
#                         grade=None,
#                         is_finalized=False,
#                         finalized_by=None,
#                         finalized_at=None
#                     )
#
#         messages.success(request, 'Четвертные оценки сохранены')
#         return redirect('journal:quarterly_grades',
#                         class_id=class_id,
#                         subject_id=subject_id,
#                         quarter_id=quarter_id)
#
#     context = {
#         'class_group': class_group,
#         'subject': subject,
#         'quarter': quarter,
#         'students_data': students_data,
#         'quarter_end_date': quarter.end_date,
#     }
#
#     return render(request, 'journal/quarterly_grades.html', context)


# from datetime import timedelta
#
# from django.contrib import messages
# from django.shortcuts import render, get_object_or_404, redirect
# from django.contrib.auth.decorators import login_required
# from django.utils import timezone
# from django.db.models import Avg, Count, Q
# from users.decorators import teacher_required, class_teacher_required, subject_teacher_required
# from school_structure.models import Quarter, ClassGroup, Subject, Lesson
# from .models import Mark, Attendance, Homework, QuarterlyGrade
# from .forms import MarkForm, AttendanceForm, QuickGradeForm, QuarterlyGradeForm
#
#
# # journal/views.py (продолжение)
#
# @login_required
# @teacher_required
# def teacher_journal(request):
#     """Главная страница журнала учителя - выбор класса и предмета"""
#     teacher = request.user.teacher_profile
#
#     # Получаем текущую четверть
#     try:
#         current_quarter = Quarter.objects.get(is_current=True)
#     except Quarter.DoesNotExist:
#         current_quarter = None
#
#     # Получаем классы и предметы, которые ведет учитель
#     teacher_classes = ClassGroup.objects.filter(
#         lessons__teacher=teacher,
#         lessons__quarter=current_quarter
#     ).distinct()
#
#     teacher_subjects = Subject.objects.filter(
#         lessons__teacher=teacher,
#         lessons__quarter=current_quarter
#     ).distinct()
#
#     context = {
#         'teacher': teacher,
#         'current_quarter': current_quarter,
#         'classes': teacher_classes,
#         'subjects': teacher_subjects,
#     }
#     return render(request, 'journal/teacher_journal.html', context)
#
#
# @login_required
# @teacher_required
# @class_teacher_required  # Новый декоратор для проверки классного руководства
# def class_teacher_dashboard(request, class_id):
#     """Дашборд классного руководителя"""
#     class_group = get_object_or_404(ClassGroup, id=class_id)
#     teacher = request.user.teacher_profile
#
#     # Статистика по классу
#     students = class_group.students.all()
#     total_students = students.count()
#
#     # Средние оценки по предметам
#     subject_stats = []
#     subjects = Subject.objects.filter(lessons__class_group=class_group).distinct()
#
#     for subject in subjects:
#         avg_grade = Mark.objects.filter(
#             lesson__class_group=class_group,
#             lesson__subject=subject
#         ).aggregate(avg=Avg('value'))['avg']
#
#         subject_stats.append({
#             'subject': subject,
#             'avg_grade': round(avg_grade, 2) if avg_grade else None,
#             'marks_count': Mark.objects.filter(
#                 lesson__class_group=class_group,
#                 lesson__subject=subject
#             ).count()
#         })
#
#     # Посещаемость за последнюю неделю
#     week_ago = timezone.now().date() - timedelta(days=7)
#     attendance_stats = Attendance.objects.filter(
#         student__class_group=class_group,
#         lesson__date__gte=week_ago
#     ).aggregate(
#         present=Count('id', filter=Q(status='PRESENT')),
#         absent=Count('id', filter=Q(status='ABSENT')),
#         ill=Count('id', filter=Q(status='ILL')),
#         late=Count('id', filter=Q(status='LATE'))
#     )
#
#     context = {
#         'class_group': class_group,
#         'teacher': teacher,
#         'total_students': total_students,
#         'subject_stats': subject_stats,
#         'attendance_stats': attendance_stats,
#         'students': students,
#     }
#
#     return render(request, 'journal/class_teacher_dashboard.html', context)

# from django.shortcuts import render
# from rest_framework import viewsets, permissions, filters
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from django_filters.rest_framework import DjangoFilterBackend
# from .models import Mark, Attendance, Homework
# from .serializers import MarkSerializer, AttendanceSerializer, HomeworkSerializer
#
#
# class MarkViewSet(viewsets.ModelViewSet):
#     serializer_class = MarkSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
#     filterset_fields = ['student', 'lesson', 'mark_type']
#     search_fields = ['student__user__first_name', 'student__user__last_name', 'comment']
#     ordering_fields = ['created_at', 'value']
#
#     def get_queryset(self):
#         user = self.request.user
#         # queryset = Mark.objects.all()
#         queryset = Mark.objects.select_related(
#             'student__user',
#             'lesson__subject',
#             'teacher__user'
#         )
#         if user.role == 'STUDENT':
#             queryset = queryset.filter(student__user=user)
#         elif user.role == 'TEACHER':
#             # Учитель видит оценки: 1) которые он выставил, 2) за свои уроки.
#             from django.db.models import Q
#             queryset = queryset.filter(
#                 Q(teacher__user=user) | Q(lesson__teacher__user=user)
#             )
#         # Администратор видит все оценки (queryset остается без изменений)
#         return queryset
#
#     @action(detail=False, methods=['get'])
#     def student_marks(self, request):
#         student_id = request.query_params.get('student_id')
#         marks = Mark.objects.filter(student_id=student_id)
#         serializer = self.get_serializer(marks, many=True)
#         return Response(serializer.data)
#     """Безопасность эндпоинта student_marks: Любой аутентифицированный пользователь может получить оценки любого
#     ученика, указав student_id. Добавьте проверку прав: учитель может смотреть своих учеников, родитель — своих
#     детей, ученик — только свои."""
#
#
# class AttendanceViewSet(viewsets.ModelViewSet):
#     serializer_class = AttendanceSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['student', 'lesson', 'status']
#
#     def get_queryset(self):
#         user = self.request.user
#         if user.role == 'STUDENT':
#             return Attendance.objects.filter(student__user=user)
#         return Attendance.objects.all()
#
#
# class HomeworkViewSet(viewsets.ModelViewSet):
#     serializer_class = HomeworkSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
#     filterset_fields = ['lesson', 'lesson__class_group']
#     ordering_fields = ['deadline', 'created_at']
#
#     def get_queryset(self):
#         user = self.request.user
#         if user.role == 'STUDENT':
#             student_profile = user.student_profile
#             return Homework.objects.filter(lesson__class_group=student_profile.class_group)
#         return Homework.objects.all()
