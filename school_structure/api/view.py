from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from ..models import TeacherWorkload, Quarter, AcademicYear
from ..serializers import (
    TeacherWorkloadSerializer,
    TeacherWorkloadCreateSerializer,
    QuarterSerializer,
    AcademicYearSerializer
)
from ..utils import calculate_teacher_workload, generate_workload_report


class TeacherWorkloadViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherWorkloadSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['teacher', 'quarter', 'subject_hours']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'TEACHER':
            return TeacherWorkload.objects.filter(teacher__user=user)
        return TeacherWorkload.objects.all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TeacherWorkloadCreateSerializer
        return TeacherWorkloadSerializer

    @action(detail=False, methods=['get'])
    def teacher_summary(self, request):
        """Сводка по нагрузке конкретного учителя"""
        teacher_id = request.query_params.get('teacher_id')
        quarter_id = request.query_params.get('quarter_id')
        academic_year_id = request.query_params.get('academic_year_id')

        if not teacher_id:
            return Response(
                {'error': 'Не указан teacher_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from ..models import TeacherProfile
        try:
            teacher = TeacherProfile.objects.get(id=teacher_id)
        except TeacherProfile.DoesNotExist:
            return Response(
                {'error': 'Учитель не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        quarter = None
        if quarter_id:
            try:
                quarter = Quarter.objects.get(id=quarter_id)
            except Quarter.DoesNotExist:
                pass

        academic_year = None
        if academic_year_id:
            try:
                academic_year = AcademicYear.objects.get(id=academic_year_id)
            except AcademicYear.DoesNotExist:
                pass

        workload_data = calculate_teacher_workload(teacher, academic_year, quarter)
        return Response(workload_data)

    @action(detail=False, methods=['get'])
    def generate_report(self, request):
        """Сгенерировать отчет по нагрузке"""
        academic_year_id = request.query_params.get('academic_year_id')
        quarter_id = request.query_params.get('quarter_id')

        if not academic_year_id:
            return Response(
                {'error': 'Не указан academic_year_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            academic_year = AcademicYear.objects.get(id=academic_year_id)
        except AcademicYear.DoesNotExist:
            return Response(
                {'error': 'Учебный год не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        quarter = None
        if quarter_id:
            try:
                quarter = Quarter.objects.get(id=quarter_id)
            except Quarter.DoesNotExist:
                pass

        report = generate_workload_report(academic_year, quarter)
        return Response(report)


class QuarterViewSet(viewsets.ModelViewSet):
    queryset = Quarter.objects.all()
    serializer_class = QuarterSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['academic_year', 'is_current']

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Получить текущую четверть"""
        current_quarter = Quarter.objects.filter(is_current=True).first()
        if not current_quarter:
            return Response(
                {'error': 'Текущая четверть не установлена'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(current_quarter)
        return Response(serializer.data)


class AcademicYearViewSet(viewsets.ModelViewSet):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_current']

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Получить текущий учебный год"""
        current_year = AcademicYear.objects.filter(is_current=True).first()
        if not current_year:
            return Response(
                {'error': 'Текущий учебный год не установлен'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(current_year)
        return Response(serializer.data)