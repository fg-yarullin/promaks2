from django.core.management.base import BaseCommand
from journal.models import GradeColumn


class Command(BaseCommand):
    help = 'Инициализация стандартных типов оценок (столбцов)'

    def handle(self, *args, **options):
        columns = [
            {
                'title': 'Устный ответ',
                'short_title': 'УО',
                'description': 'Ответ у доски или с места',
                'weight': 1.0,
                'order': 10
            },
            {
                'title': 'Домашняя работа',
                'short_title': 'ДЗ',
                'description': 'Проверка домашнего задания',
                'weight': 1.0,
                'order': 20
            },
            {
                'title': 'Самостоятельная работа',
                'short_title': 'СР',
                'description': 'Самостоятельная работа на уроке',
                'weight': 1.2,
                'order': 30
            },
            {
                'title': 'Контрольная работа',
                'short_title': 'КР',
                'description': 'Контрольная работа',
                'weight': 1.5,
                'order': 40
            },
            {
                'title': 'Тест',
                'short_title': 'Т',
                'description': 'Тестирование',
                'weight': 1.0,
                'order': 50
            },
            {
                'title': 'Проект',
                'short_title': 'ПР',
                'description': 'Проектная работа',
                'weight': 1.3,
                'order': 60
            },
            {
                'title': 'Лабораторная работа',
                'short_title': 'ЛР',
                'description': 'Лабораторная работа',
                'weight': 1.2,
                'order': 70
            },
        ]

        created_count = 0
        for col_data in columns:
            column, created = GradeColumn.objects.get_or_create(
                title=col_data['title'],
                defaults=col_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'Создан столбец: {col_data["title"]}')

        self.stdout.write(self.style.SUCCESS(f'Создано {created_count} столбцов оценок'))
