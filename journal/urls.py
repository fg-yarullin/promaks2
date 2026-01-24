# journal/urls.py - добавляем новые маршруты
from django.urls import path
from . import views

app_name = 'journal'

urlpatterns = [
    # Новые URL для системы с настраиваемыми столбцами
    path('teacher/columns/', views.teacher_journal, name='teacher_journal'),
    path('teacher/class/<int:class_id>/subject/<int:subject_id>/columns/',
         views.class_subject_journal, name='class_journal'),
    path('teacher/class/<int:class_id>/subject/<int:subject_id>/quarter/<int:quarter_id>/columns/',
         views.class_subject_journal, name='class_journal_quarter'),
# path('ajax/update_mark/', views.update_student_grade, name='update_mark'),

    # AJAX для работы со столбцами
    path('ajax/update_student_grade/', views.update_student_grade, name='update_student_grade'),
    path('ajax/manage_lesson_column/', views.manage_lesson_column, name='manage_lesson_column'),
    path('ajax/column/<int:column_id>/stats/', views.get_column_stats, name='get_column_stats'),

    # Четвертные и годовые оценки
    path('quarterly/class/<int:class_id>/subject/<int:subject_id>/quarter/<int:quarter_id>/columns/',
         views.quarterly_grades, name='quarterly_grades'),
    path('yearly/class/<int:class_id>/subject/<int:subject_id>/columns/',
         views.yearly_grades_view, name='yearly_grades'),
]
