# journal/templatetags/journal_tags.py
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Получить элемент из словаря по ключу"""
    if dictionary and key in dictionary:
        return dictionary.get(key)
    return None


@register.simple_tag
def get_student_grade(grades_dict, student_id, column_id):
    """Получить оценку ученика для конкретного столбца"""
    if not grades_dict:
        return None

    # Проверяем наличие student_id в словаре
    student_grades = grades_dict.get(student_id)
    if not student_grades:
        return None

    # Получаем данные об оценке
    grade_data = student_grades.get(column_id)
    if grade_data:
        return grade_data.get('value')

    return None


@register.simple_tag
def get_grade_data(grades_dict, student_id, column_id):
    """Получить полные данные об оценке"""
    if not grades_dict:
        return None

    student_grades = grades_dict.get(student_id)
    if not student_grades:
        return None

    return student_grades.get(column_id)


@register.filter
def get_student_grades(grades_dict, student_id):
    """Получить все оценки ученика"""
    if not grades_dict:
        return {}
    return grades_dict.get(student_id, {})
#
# @register.filter
# def get_item(dictionary, key):
#     """Получить элемент из словаря по ключу"""
#     if dictionary and key in dictionary:
#         return dictionary.get(key)
#     return None
#
#
# @register.filter
# def get_nested(dictionary, student_id, column_id):
#     """Получить элемент из вложенного словаря по student_id и column_id"""
#     if dictionary and student_id in dictionary:
#         student_dict = dictionary.get(student_id)
#         if student_dict and column_id in student_dict:
#             return student_dict.get(column_id)
#     return None
#
#
# @register.filter
# def get_grade_value(dictionary, student_id, column_id):
#     """Получить только значение оценки из вложенного словаря"""
#     if dictionary and student_id in dictionary:
#         student_dict = dictionary.get(student_id)
#         if student_dict and column_id in student_dict:
#             grade_data = student_dict.get(column_id)
#             if grade_data:
#                 return grade_data.get('value')
#     return None
#
#
# def oldd_get_grade_value(dictionary, combined_id):
#     try:
#         student_id, column_id = combined_id.split('_')
#         student_id = int(student_id)
#         column_id = int(column_id)
#     except:
#         return None
#     grade_data = get_nested(dictionary, student_id, column_id)
#     if grade_data:
#         return grade_data.get('value')
#     return None
#
#
# def old_get_grade_value(dictionary, student_id, column_id):
#     """Получить только значение оценки из вложенного словаря"""
#     grade_data = get_nested(dictionary, student_id, column_id)
#     if grade_data:
#         return grade_data.get('value')
#     return None
#
#
# @register.filter
# def has_grade(dictionary, student_id, column_id):
#     """Проверить, есть ли оценка у ученика в столбце"""
#     return bool(get_nested(dictionary, student_id, column_id))
