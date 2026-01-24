from django import forms
from django.utils import timezone
from .models import Mark, Attendance, Homework


class MarkForm(forms.ModelForm):
    class Meta:
        model = Mark
        fields = ['value', 'comment']
        widgets = {
            'value': forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Комментарий...'}),
        }


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['status', 'note']
        widgets = {
            'status': forms.Select(attrs={'class': 'attendance-select'}),
            'note': forms.Textarea(attrs={'rows': 1, 'placeholder': 'Причина...'}),
        }


class QuickGradeForm(forms.Form):
    """Форма для быстрого выставления оценок"""
    student_id = forms.IntegerField(widget=forms.HiddenInput())
    lesson_id = forms.IntegerField(widget=forms.HiddenInput())
    mark_value = forms.ChoiceField(
        choices=[('', '--')] + [(i, str(i)) for i in range(1, 6)],
        required=False,
        widget=forms.Select(attrs={'class': 'quick-grade-select'})
    )
    attendance_status = forms.ChoiceField(
        choices=[('', '--')] + list(Attendance.Status.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'attendance-select'})
    )


class QuarterlyGradeForm(forms.Form):
    """Форма для выставления четвертных оценок"""
    student_id = forms.IntegerField(widget=forms.HiddenInput())
    quarterly_grade = forms.ChoiceField(
        choices=[('', '--')] + [(i, str(i)) for i in range(1, 6)],
        required=False
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Комментарий к четвертной оценке'})
    )
