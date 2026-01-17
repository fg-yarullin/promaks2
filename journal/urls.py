# journal/urls.py
from django.urls import path
from . import views

app_name = 'journal'

urlpatterns = [
    # Главная страница журналов учителя
    path('teacher/', views.teacher_journal, name='teacher_journal'),

    # Журнал по классу и предмету
    path('teacher/class/<int:class_id>/subject/<int:subject_id>/',
         views.class_subject_journal, name='class_journal'),
    path('teacher/class/<int:class_id>/subject/<int:subject_id>/quarter/<int:quarter_id>/',
         views.class_subject_journal, name='class_journal_quarter'),

    # AJAX endpoints
    path('ajax/update_mark/', views.update_mark_attendance, name='update_mark'),
    path('ajax/manage_lesson_columns/', views.manage_lesson_columns, name='manage_lesson_columns'),
    # path('ajax/student/<int:student_id>/subject/<int:subject_id>/quarter/<int:quarter_id>/stats/',
    #      views.get_student_stats, name='student_stats'),

    # Четвертные оценки
    path('quarterly/class/<int:class_id>/subject/<int:subject_id>/quarter/<int:quarter_id>/',
         views.quarterly_grades, name='quarterly_grades'),
# Годовые оценки
    path('yearly/class/<int:class_id>/subject/<int:subject_id>/',
         views.yearly_grades_view, name='yearly_grades'),
    path('yearly/class/<int:class_id>/subject/<int:subject_id>/year/<int:year_id>/',
         views.yearly_grades_view, name='yearly_grades_year'),
]


# from django.urls import path
# from . import views
#
# app_name = 'journal'
#
# urlpatterns = [
#     # Журнал учителя
#     path('teacher/', views.teacher_journal, name='teacher_journal'),
#
#     # Дашборд классного руководителя
#     path('class-teacher/<int:class_id>/', views.class_teacher_dashboard, name='class_teacher_dashboard'),
#
#     # Журнал по классу и предмету
#     path('teacher/class/<int:class_id>/subject/<int:subject_id>/',
#          views.class_subject_journal, name='class_journal'),
#     path('teacher/class/<int:class_id>/subject/<int:subject_id>/quarter/<int:quarter_id>/',
#          views.class_subject_journal, name='class_journal_quarter'),
#
#     # AJAX endpoints
#     path('ajax/update_mark/', views.update_mark_attendance, name='update_mark'),
#     path('ajax/student/<int:student_id>/subject/<int:subject_id>/quarter/<int:quarter_id>/stats/',
#          views.get_student_stats, name='student_stats'),
#
#     # Четвертные оценки
#     path('quarterly/class/<int:class_id>/subject/<int:subject_id>/quarter/<int:quarter_id>/',
#          views.quarterly_grades, name='quarterly_grades'),
# ]
