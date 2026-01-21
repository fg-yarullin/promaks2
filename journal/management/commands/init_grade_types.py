from django.core.management.base import BaseCommand
from journal.models import GradeType


class Command(BaseCommand):
    help = 'Инициализация типов оценок'

    def handle(self, *args, **options):
        grade_types = [
            {
                'title': 'Устный ответ',
                'short_title': 'УО',
                'weight': 1.0,
                'color': '#28a745',
                'description': 'Ответ у доски или с места',
                'is_default': True,
                'order': 10
            },
            {
                'title': 'Домашняя работа',
                'short_title': 'ДЗ',
                'weight': 1.0,
                'color': '#007bff',
                'description': 'Проверка домашнего задания',
                'is_default': False,
                'order': 20
            },
            {
                'title': 'Самостоятельная работа',
                'short_title': 'СР',
                'weight': 1.2,
                'color': '#ffc107',
                'description': 'Самостоятельная работа на уроке',
                'is_default': False,
                'order': 30
            },
            {
                'title': 'Контрольная работа',
                'short_title': 'КР',
                'weight': 1.5,
                'color': '#dc3545',
                'description': 'Контрольная работа',
                'is_default': False,
                'order': 40
            },
            {
                'title': 'Тест',
                'short_title': 'Т',
                'weight': 1.0,
                'color': '#6f42c1',
                'description': 'Тестирование',
                'is_default': False,
                'order': 50
            },
            {
                'title': 'Проект',
                'short_title': 'ПР',
                'weight': 1.3,
                'color': '#20c997',
                'description': 'Проектная работа',
                'is_default': False,
                'order': 60
            },
            {
                'title': 'Лабораторная работа',
                'short_title': 'ЛР',
                'weight': 1.2,
                'color': '#fd7e14',
                'description': 'Лабораторная работа',
                'is_default': False,
                'order': 70
            },
        ]

        created_count = 0
        for type_data in grade_types:
            grade_type, created = GradeType.objects.get_or_create(
                title=type_data['title'],
                defaults=type_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'Создан тип оценки: {type_data["title"]}')

        self.stdout.write(self.style.SUCCESS(f'Создано {created_count} типов оценок'))