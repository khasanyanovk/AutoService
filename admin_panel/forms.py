from django import forms
from django.core.validators import RegexValidator

from core.models import ServiceCenter


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
