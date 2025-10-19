from django import forms
from django.core.validators import RegexValidator

from core.models import ServiceCenter
from core.models import ServiceType


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
    opening_hours = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Напр.: Пн-Пт 9:00-18:00"}
        ),
        label="Время работы",
    )
    photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
        label="Фото",
    )

    class Meta:
        model = ServiceCenter
        fields = ["address", "phone", "opening_hours", "photo"]

    def clean_opening_hours(self):
        text = self.cleaned_data.get("opening_hours", "").strip()
        if len(text) < 3:
            raise forms.ValidationError("Заполните часы работы")
        return text


class ServiceCenterCreateForm(ServiceCenterEditForm):
    """Создание филиала: те же поля, что и в редактировании"""

    class Meta(ServiceCenterEditForm.Meta):
        fields = ["address", "phone", "opening_hours", "photo"]


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
    description = forms.CharField(
        label="Описание",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
    duration = forms.IntegerField(
        label="Продолжительность (мин)",
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    is_active = forms.BooleanField(
        label="Активна",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
