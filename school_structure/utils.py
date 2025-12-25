from datetime import date, timedelta
from django.db.models import Sum, Q
from .models import TeacherWorkload, Lesson, Quarter


def generate_schedule(class_group, start_date, end_date):
    """Генерация расписания на период"""
    current_date = start_date
    while current_date <= end_date:
        # Логика генерации уроков по дням недели
        # Можно использовать шаблоны расписания
        pass


def calculate_teacher_workload(teacher, academic_year=None, quarter=None):
    """
    Рассчитать фактическую нагрузку учителя
    """
    filters = {'teacher': teacher}

    if academic_year:
        filters['subject_hours__class_group__academic_year'] = academic_year

    if quarter:
        filters['quarter'] = quarter

    workloads = TeacherWorkload.objects.filter(**filters)

    result = {
        'total_hours_per_week': workloads.aggregate(
            total=Sum('hours_per_week')
        )['total'] or 0,
        'total_hours_in_period': workloads.aggregate(
            total=Sum('total_hours_in_quarter')
        )['total'] or 0,
        'workloads': [],
        'by_subject': {},
        'by_class': {},
    }

    for workload in workloads:
        # Подсчет по предметам
        subject_title = workload.subject_hours.subject.title
        if subject_title not in result['by_subject']:
            result['by_subject'][subject_title] = 0
        result['by_subject'][subject_title] += workload.hours_per_week

        # Подсчет по классам
        class_name = str(workload.subject_hours.class_group)
        if class_name not in result['by_class']:
            result['by_class'][class_name] = 0
        result['by_class'][class_name] += workload.hours_per_week

        result['workloads'].append({
            'subject': str(workload.subject_hours.subject),
            'class': str(workload.subject_hours.class_group),
            'hours_per_week': workload.hours_per_week,
            'quarter': str(workload.quarter),
            'total_in_quarter': workload.total_hours_in_quarter,
        })

    return result


def check_workload_compliance(teacher, date_range_start, date_range_end):
    """
    Проверить соответствие фактического количества уроков плановой нагрузке
    """
    # Получаем все четверти в диапазоне дат
    quarters = Quarter.objects.filter(
        start_date__lte=date_range_end,
        end_date__gte=date_range_start
    )

    results = []
    for quarter in quarters:
        # Плановая нагрузка в четверти
        planned_workloads = TeacherWorkload.objects.filter(
            teacher=teacher,
            quarter=quarter
        )

        total_planned_hours = 0
        for workload in planned_workloads:
            # Количество недель в проверяемом периоде
            start_date = max(date_range_start, quarter.start_date)
            end_date = min(date_range_end, quarter.end_date)
            weeks_in_period = calculate_weeks_in_period(start_date, end_date)
            total_planned_hours += workload.hours_per_week * weeks_in_period

        # Фактическое количество уроков
        actual_lessons = Lesson.objects.filter(
            teacher=teacher,
            date__range=[date_range_start, date_range_end],
            quarter=quarter
        ).count()

        # Считаем, что каждый урок - 1 академический час
        actual_hours = actual_lessons

        results.append({
            'quarter': quarter,
            'planned_hours': total_planned_hours,
            'actual_hours': actual_hours,
            'difference': actual_hours - total_planned_hours,
            'compliance': round((actual_hours / total_planned_hours * 100) if total_planned_hours > 0 else 0, 2)
        })

    return results


def calculate_weeks_in_period(start_date, end_date):
    """Рассчитать количество понедельников в периоде"""
    weeks = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() == 0:  # Понедельник
            weeks += 1
        current_date += timedelta(days=1)
    return weeks or 1


def generate_workload_report(academic_year, quarter=None):
    """
    Сгенерировать отчет по нагрузке учителей
    """
    filters = {
        'subject_hours__class_group__academic_year': academic_year
    }

    if quarter:
        filters['quarter'] = quarter

    workloads = TeacherWorkload.objects.filter(**filters).select_related(
        'teacher__user',
        'subject_hours__subject',
        'subject_hours__class_group',
        'quarter'
    )

    report = {
        'academic_year': academic_year,
        'quarter': quarter,
        'teachers': {},
        'summary': {
            'total_teachers': 0,
            'total_hours_per_week': 0,
            'average_hours_per_teacher': 0,
        }
    }

    for workload in workloads:
        teacher_name = f"{workload.teacher.user.last_name} {workload.teacher.user.first_name}"

        if teacher_name not in report['teachers']:
            report['teachers'][teacher_name] = {
                'hours_per_week': 0,
                'workloads': [],
                'subjects': set(),
                'classes': set(),
            }

        report['teachers'][teacher_name]['hours_per_week'] += workload.hours_per_week
        report['teachers'][teacher_name]['workloads'].append({
            'subject': str(workload.subject_hours.subject),
            'class': str(workload.subject_hours.class_group),
            'hours': workload.hours_per_week,
            'quarter': str(workload.quarter),
        })
        report['teachers'][teacher_name]['subjects'].add(str(workload.subject_hours.subject))
        report['teachers'][teacher_name]['classes'].add(str(workload.subject_hours.class_group))

    # Сводная статистика
    report['summary']['total_teachers'] = len(report['teachers'])
    report['summary']['total_hours_per_week'] = sum(
        t['hours_per_week'] for t in report['teachers'].values()
    )

    if report['summary']['total_teachers'] > 0:
        report['summary']['average_hours_per_teacher'] = round(
            report['summary']['total_hours_per_week'] / report['summary']['total_teachers'], 2
        )

    return report
