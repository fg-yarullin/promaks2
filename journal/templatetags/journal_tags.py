# journal/templatetags/journal_tags.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Получить элемент из словаря по ключу в шаблоне"""
    if dictionary:
        return dictionary.get(key)
    return None
