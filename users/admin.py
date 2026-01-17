from django.contrib import admin
from django.utils import timezone
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StudentProfile, TeacherProfile, ParentProfile


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'role', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password',)}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'email', 'role')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'class_group', 'admission_year', 'get_current_class')
    list_filter = ('class_group', 'admission_year')
    search_fields = ('user__first_name', 'user__last_name', 'class_group__name')
    raw_id_fields = ('user', 'class_group')

    def get_current_class(self, obj):
        """Показывает текущий класс ученика на основе года поступления"""
        if obj.class_group and obj.admission_year:
            current_year = timezone.now().year
            # Простой расчет: текущий год - год поступления + 1
            year_of_study = current_year - obj.admission_year + 1
            if 1 <= year_of_study <= 11:
                return f"{year_of_study}-й класс"
        return "-"

    get_current_class.short_description = 'Текущий класс'
# class StudentProfileAdmin(admin.ModelAdmin):
#     list_display = ('user', 'class_group', 'admission_year')
#     list_filter = ('class_group',)
#     search_fields = ('user__first_name', 'user__last_name', 'class_group__name')


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'education')
    filter_horizontal = ('subject_areas',)
    search_fields = ('user__first_name', 'user__last_name')


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'children_count')
    filter_horizontal = ('children',)

    def children_count(self, obj):
        return obj.children.count()

    children_count.short_description = 'Количество детей'