from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from school_structure.models import ClassGroup

User = get_user_model()


class EmailAuthenticationForm(AuthenticationForm):
    """Форма входа по email вместо username"""
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Введите email'})
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Введите пароль'})
    )

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if email and password:
            # Используем наш кастомный бэкенд
            from .authentication import EmailAuthBackend
            backend = EmailAuthBackend()
            user = backend.authenticate(request=self.request, username=email, password=password)

            if user is None:
                raise forms.ValidationError('Неверный email или пароль')
            elif not user.is_active:
                raise forms.ValidationError('Аккаунт отключен')

            self.user_cache = user
        return self.cleaned_data


class UserRegistrationForm(UserCreationForm):
    """Форма регистрации пользователя"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    patronymic = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    role = forms.ChoiceField(
        choices=User.Role.choices,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # Дополнительные поля для ученика
    class_group = forms.ModelChoiceField(
        queryset=ClassGroup.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Класс'
    )
    admission_year = forms.IntegerField(
        min_value=2000,
        max_value=2030,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Год поступления'
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'patronymic',
                  'role', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Убираем стандартное поле username
        self.fields.pop('username', None)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже существует')
        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')

        # Валидация для учеников
        if role == 'STUDENT':
            if not cleaned_data.get('class_group'):
                self.add_error('class_group', 'Для ученика необходимо указать класс')
            if not cleaned_data.get('admission_year'):
                self.add_error('admission_year', 'Для ученика необходимо указать год поступления')

        return cleaned_data

    def save(self, commit=True):
        # Используем email как username
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.patronymic = self.cleaned_data.get('patronymic', '')
        user.role = self.cleaned_data['role']

        if commit:
            user.save()

            # Дополнительные данные для ученика
            if user.role == 'STUDENT':
                from .models import StudentProfile
                StudentProfile.objects.create(
                    user=user,
                    class_group=self.cleaned_data['class_group'],
                    admission_year=self.cleaned_data['admission_year']
                )

        return user


class StudentProfileForm(forms.ModelForm):
    """Форма редактирования профиля ученика"""

    class Meta:
        from .models import StudentProfile
        model = StudentProfile
        fields = ('class_group', 'admission_year')
        widgets = {
            'class_group': forms.Select(attrs={'class': 'form-control'}),
            'admission_year': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class TeacherProfileForm(forms.ModelForm):
    """Форма редактирования профиля учителя"""

    class Meta:
        from .models import TeacherProfile
        model = TeacherProfile
        fields = ('education', 'subject_areas')
        widgets = {
            'education': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'subject_areas': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }
