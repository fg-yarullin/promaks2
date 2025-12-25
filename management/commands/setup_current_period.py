from django.core.management.base import BaseCommand
from django.utils import timezone
from school_structure.models import AcademicYear, Quarter
import datetime


class Command(BaseCommand):
    help = 'Настроить текущий учебный год и четверть'

    def handle(self, *args, **options):
        today = timezone.now().date()

        # Находим или создаем текущий учебный год
        current_year, created = AcademicYear.objects.get_or_create(
            year=f"{today.year}-{today.year + 1}",
            defaults={
                'start_date': datetime.date(today.year, 9, 1),
                'end_date': datetime.date(today.year + 1, 5, 31),
                'is_current': True
            }
        )

        if created:
            self.stdout.write(f'Создан новый учебный год: {current_year}')

        # Определяем текущую четверть по дате
        quarter_dates = [
            (1, datetime.date(today.year, 9, 1), datetime.date(today.year, 10, 27)),
            (2, datetime.date(today.year, 11, 5), datetime.date(today.year, 12, 29)),
            (3, datetime.date(today.year + 1, 1, 9), datetime.date(today.year + 1, 3, 22)),
            (4, datetime.date(today.year + 1, 4, 1), datetime.date(today.year + 1, 5, 31)),
        ]

        for num, start, end in quarter_dates:
            if start <= today <= end:
                quarter, q_created = Quarter.objects.get_or_create(
                    academic_year=current_year,
                    number=num,
                    defaults={
                        'name': f'{num}-я четверть',
                        'start_date': start,
                        'end_date': end,
                        'is_current': True
                    }
                )

                if q_created:
                    self.stdout.write(f'Создана четверть: {quarter}')
                break

        self.stdout.write(self.style.SUCCESS('Настройка периодов завершена'))
