from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, StudentProfile, TeacherProfile, ParentProfile


@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Создает или обновляет профиль пользователя при сохранении.
    Теперь admission_year устанавливается автоматически.
    """
    if instance.role == 'STUDENT':
        StudentProfile.objects.get_or_create(user=instance)
        # Удаляем другие профили
        TeacherProfile.objects.filter(user=instance).delete()
        ParentProfile.objects.filter(user=instance).delete()

    elif instance.role == 'TEACHER':
        TeacherProfile.objects.get_or_create(user=instance)
        StudentProfile.objects.filter(user=instance).delete()
        ParentProfile.objects.filter(user=instance).delete()

    elif instance.role == 'PARENT':
        ParentProfile.objects.get_or_create(user=instance)
        StudentProfile.objects.filter(user=instance).delete()
        TeacherProfile.objects.filter(user=instance).delete()

    else:
        # Для ADMIN, EMPTY - удаляем все профили
        StudentProfile.objects.filter(user=instance).delete()
        TeacherProfile.objects.filter(user=instance).delete()
        ParentProfile.objects.filter(user=instance).delete()


# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import CustomUser, StudentProfile, TeacherProfile, ParentProfile
#
# # @receiver(post_save, sender=CustomUser)
# # def create_user_profile(sender, instance, created, **kwargs):
# #     if created:
# #         if instance.role == 'STUDENT':
# #             StudentProfile.objects.create(user=instance)
# #         elif instance.role == 'TEACHER':
# #             TeacherProfile.objects.create(user=instance)
#
# @receiver(post_save, sender=CustomUser)
# def create_or_update_user_profile(sender, instance, created, **kwargs):
#     """Создает или обновляет профиль пользователя при сохранении."""
#     if instance.role == 'STUDENT':
#         StudentProfile.objects.get_or_create(user=instance)
#         # Удаляем другие профили, если роль поменялась
#         TeacherProfile.objects.filter(user=instance).delete()
#         ParentProfile.objects.filter(user=instance).delete()
#     elif instance.role == 'TEACHER':
#         TeacherProfile.objects.get_or_create(user=instance)
#         StudentProfile.objects.filter(user=instance).delete()
#         ParentProfile.objects.filter(user=instance).delete()
#     elif instance.role == 'PARENT':
#         ParentProfile.objects.get_or_create(user=instance)
#         StudentProfile.objects.filter(user=instance).delete()
#         TeacherProfile.objects.filter(user=instance).delete()
#     else:
#         # Для ADMIN, EMPTY - удаляем все профили
#         StudentProfile.objects.filter(user=instance).delete()
#         TeacherProfile.objects.filter(user=instance).delete()
#         ParentProfile.objects.filter(user=instance).delete()
#