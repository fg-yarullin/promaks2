from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Mark, Attendance, Homework
from .serializers import MarkSerializer, AttendanceSerializer, HomeworkSerializer


class MarkViewSet(viewsets.ModelViewSet):
    serializer_class = MarkSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['student', 'lesson', 'mark_type']
    search_fields = ['student__user__first_name', 'student__user__last_name', 'comment']
    ordering_fields = ['created_at', 'value']

    def get_queryset(self):
        user = self.request.user
        # queryset = Mark.objects.all()
        queryset = Mark.objects.select_related(
            'student__user',
            'lesson__subject',
            'teacher__user'
        )
        if user.role == 'STUDENT':
            queryset = queryset.filter(student__user=user)
        elif user.role == 'TEACHER':
            # Учитель видит оценки: 1) которые он выставил, 2) за свои уроки.
            from django.db.models import Q
            queryset = queryset.filter(
                Q(teacher__user=user) | Q(lesson__teacher__user=user)
            )
        # Администратор видит все оценки (queryset остается без изменений)
        return queryset

    @action(detail=False, methods=['get'])
    def student_marks(self, request):
        student_id = request.query_params.get('student_id')
        marks = Mark.objects.filter(student_id=student_id)
        serializer = self.get_serializer(marks, many=True)
        return Response(serializer.data)
    """Безопасность эндпоинта student_marks: Любой аутентифицированный пользователь может получить оценки любого 
    ученика, указав student_id. Добавьте проверку прав: учитель может смотреть своих учеников, родитель — своих 
    детей, ученик — только свои."""


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student', 'lesson', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'STUDENT':
            return Attendance.objects.filter(student__user=user)
        return Attendance.objects.all()


class HomeworkViewSet(viewsets.ModelViewSet):
    serializer_class = HomeworkSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['lesson', 'lesson__class_group']
    ordering_fields = ['deadline', 'created_at']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'STUDENT':
            student_profile = user.student_profile
            return Homework.objects.filter(lesson__class_group=student_profile.class_group)
        return Homework.objects.all()
