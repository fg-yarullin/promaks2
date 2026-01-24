from django.core.management.base import BaseCommand
from django.db.models import Count, Avg
from journal.models import StudentGrade, LessonColumn, GradeType
from users.models import StudentProfile
from school_structure.models import Lesson


class Command(BaseCommand):
    help = 'Проверка корректности данных оценок'

    def add_arguments(self, parser):
        parser.add_argument('--lesson', type=int, help='ID урока')
        parser.add_argument('--student', type=int, help='ID ученика')
        parser.add_argument('--fix', action='store_true', help='Исправить проблемы')

    def handle(self, *args, **options):
        lesson_id = options.get('lesson')
        student_id = options.get('student')
        fix = options.get('fix')

        self.stdout.write("=== ПРОВЕРКА ДАННЫХ ОЦЕНОК ===")

        # Проверяем наличие дубликатов оценок
        self.stdout.write("\n1. Проверка дубликатов оценок...")
        duplicates = StudentGrade.objects.values(
            'student', 'lesson_column'
        ).annotate(
            count=Count('id')
        ).filter(count__gt=1)

        if duplicates.exists():
            self.stdout.write(self.style.ERROR(f"Найдено {duplicates.count()} дубликатов оценок"))
            for dup in duplicates:
                self.stdout.write(f"  Студент {dup['student']}, Столбец {dup['lesson_column']}: {dup['count']} записей")

                if fix:
                    # Оставляем только последнюю оценку
                    grades = StudentGrade.objects.filter(
                        student_id=dup['student'],
                        lesson_column_id=dup['lesson_column']
                    ).order_by('-created_at')

                    # Удаляем все, кроме первой (последней по времени)
                    for grade in grades[1:]:
                        grade.delete()
                    self.stdout.write(f"    Исправлено: оставлена 1 запись")
        else:
            self.stdout.write(self.style.SUCCESS("Дубликатов оценок не найдено"))

        # Проверяем отсутствующие столбцы
        self.stdout.write("\n2. Проверка уроков без столбцов...")
        lessons_without_columns = Lesson.objects.filter(columns__isnull=True)

        if lessons_without_columns.exists():
            self.stdout.write(self.style.WARNING(f"Найдено {lessons_without_columns.count()} уроков без столбцов"))

            if fix:
                default_grade_type = GradeType.objects.filter(is_default=True).first()
                if default_grade_type:
                    for lesson in lessons_without_columns:
                        LessonColumn.objects.create(
                            lesson=lesson,
                            grade_type=default_grade_type,
                            title=default_grade_type.title,
                            order=10
                        )
                    self.stdout.write(f"    Созданы столбцы для {lessons_without_columns.count()} уроков")

        # Проверяем статистику
        self.stdout.write("\n3. Общая статистика:")
        total_grades = StudentGrade.objects.count()
        self.stdout.write(f"  Всего оценок в системе: {total_grades}")

        avg_grade = StudentGrade.objects.aggregate(avg=Avg('value'))['avg']
        self.stdout.write(f"  Средний балл: {avg_grade:.2f}" if avg_grade else "  Средний балл: нет данных")

        # Проверяем конкретного ученика если указан
        if student_id:
            self.stdout.write(f"\n4. Проверка ученика ID={student_id}:")
            try:
                student = StudentProfile.objects.get(id=student_id)
                student_grades = StudentGrade.objects.filter(student=student)

                self.stdout.write(f"  Ученик: {student.user.get_full_name()}")
                self.stdout.write(f"  Количество оценок: {student_grades.count()}")

                if student_grades.exists():
                    avg = student_grades.aggregate(avg=Avg('value'))['avg']
                    self.stdout.write(f"  Средний балл: {avg:.2f}")

                    # Распределение по типам оценок
                    by_type = student_grades.values(
                        'lesson_column__grade_type__title'
                    ).annotate(
                        count=Count('id'),
                        avg=Avg('value')
                    )

                    for item in by_type:
                        self.stdout.write(f"    {item['lesson_column__grade_type__title']}: "
                                          f"{item['count']} оценок, среднее: {item['avg']:.2f}")
            except StudentProfile.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Ученик с ID={student_id} не найден"))

        self.stdout.write(self.style.SUCCESS("\nПроверка завершена!"))
