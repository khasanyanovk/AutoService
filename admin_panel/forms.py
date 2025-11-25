from django import forms
from django.core.validators import RegexValidator
from django.contrib.auth.models import User

from core.models import ServiceCenter
from core.models import ServiceType, CarBrand, CarModel


class UserCreateForm(forms.ModelForm):
    """Форма создания пользователя администратором"""

    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Введите пароль"}
        ),
        help_text="Минимум 8 символов",
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Повторите пароль"}
        ),
    )
    is_staff = forms.BooleanField(
        label="Администратор",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Пользователь получит права администратора",
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "is_staff"]
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Логин пользователя"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "email@example.com"}
            ),
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Имя"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Фамилия"}
            ),
        }
        labels = {
            "username": "Логин",
            "email": "Email",
            "first_name": "Имя",
            "last_name": "Фамилия",
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Пароли не совпадают")
        if password1 and len(password1) < 8:
            raise forms.ValidationError("Пароль должен содержать минимум 8 символов")
        return password2

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_active = True
        if commit:
            user.save()
        return user


class ServiceCenterEditForm(forms.ModelForm):
    phone = forms.CharField(
        validators=[
            RegexValidator(
                regex=r"^[+]?\d[\d\s\-()]{7,20}$",
                message="Введите корректный телефон (разрешены +, цифры, пробелы, дефисы, скобки)",
            )
        ],
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Телефон",
    )
    address = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Адрес",
    )
    photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
        label="Фото",
    )

    class Meta:
        model = ServiceCenter
        fields = ["address", "phone", "photo"]


class ServiceCenterCreateForm(forms.ModelForm):
    """Создание филиала без текстового поля часов работы (используем таблицу WorkingHours)."""

    phone = forms.CharField(
        validators=[
            RegexValidator(
                regex=r"^[+]?\d[\d\s\-()]{7,20}$",
                message="Введите корректный телефон (разрешены +, цифры, пробелы, дефисы, скобки)",
            )
        ],
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Телефон",
    )
    address = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Адрес",
    )
    photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
        label="Фото",
    )

    class Meta:
        model = ServiceCenter
        fields = ["address", "phone", "photo"]


class BranchWorkingHoursForm(forms.Form):
    """Упрощённый ввод рабочего времени в одном текстовом поле"""

    opening_hours = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Напр.: Пн-Пт 9:00-18:00"}
        ),
        label="Время работы",
    )


class BranchServicesSelectionForm(forms.Form):
    """Выбор услуг для филиала после создания, с ценой и длительностью"""

    pass


class ServiceTypeForm(forms.ModelForm):
    class Meta:
        model = ServiceType
        fields = [
            "name",
            "description",
            "duration",
            "price",
            "service_center",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "duration": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
            "service_center": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ServiceTypeBaseCreateForm(forms.Form):
    name = forms.CharField(
        label="Название услуги",
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class CarBrandForm(forms.ModelForm):
    class Meta:
        model = CarBrand
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
        }


class CarModelForm(forms.ModelForm):
    class Meta:
        model = CarModel
        fields = ["brand", "name"]
        widgets = {
            "brand": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
        }
