import os
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import ServiceCenter, UserProfile, Car, CarBrand, CarModel
from datetime import datetime, date, timedelta
from django.forms import ValidationError
from .models import ServiceType, Appointment, WorkingHours
from django.core.validators import RegexValidator
import re


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        ]


class ServiceCenterChoiceForm(forms.Form):
    """Форма выбора автосервиса"""

    service_center = forms.ModelChoiceField(
        queryset=ServiceCenter.objects.all(),
        empty_label="Выберите автосервис",
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Автосервис",
    )


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class ProfileUpdateForm(forms.ModelForm):
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control"}),
        help_text="Максимальный размер: 2MB. Поддерживаемые форматы: JPG, PNG.",
    )

    class Meta:
        model = UserProfile
        fields = ["phone", "address", "avatar"]

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar:
            if avatar.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Размер файла не должен превышать 2MB.")

            valid_extensions = [".jpg", ".jpeg", ".png"]
            ext = os.path.splitext(avatar.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError("Поддерживаются только JPG и PNG форматы.")

        return avatar

    def save(self, commit=True):
        instance = super().save(commit=False)

        if not self.cleaned_data.get("avatar") and instance.pk:
            original = UserProfile.objects.get(pk=instance.pk)
            instance.avatar = original.avatar

        if commit:
            instance.save()

        return instance


class CarForm(forms.Form):
    brand = forms.ModelChoiceField(
        queryset=CarBrand.objects.all(),
        empty_label="Выберите марку",
        widget=forms.Select(attrs={"class": "form-control"}),
        required=True,
    )
    model = forms.ModelChoiceField(
        queryset=CarModel.objects.none(),
        empty_label="Сначала выберите марку",
        widget=forms.Select(attrs={"class": "form-control"}),
        required=True,
    )
    year = forms.IntegerField(
        min_value=1900,
        max_value=datetime.now().year,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        required=True,
    )
    license_plate = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=True,
        label="Гос. номер",
    )
    vin = forms.CharField(
        max_length=17,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=False,
        label="VIN",
    )

    def clean_license_plate(self):
        """Проверка корректности формата гос. номера (X000XX)"""
        plate = self.cleaned_data.get("license_plate", "").strip().upper()
        pattern = r"^[A-Z]{1}\d{3}[A-Z]{2}$"

        if not re.match(pattern, plate):
            raise ValidationError(
                "Номер должен быть в формате X000XX (латинские буквы, 3 цифры)."
            )

        return plate

    def clean_vin(self):
        """Проверка корректности VIN-кода"""
        vin = self.cleaned_data.get("vin", "")
        if vin:
            if not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", vin.upper()):
                raise ValidationError(
                    "VIN должен содержать ровно 17 символов (латинские буквы и цифры)."
                )
        return vin

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", {})
        super().__init__(*args, **kwargs)

        if "brand" in initial and initial["brand"]:
            self.fields["model"].queryset = CarModel.objects.filter(
                brand=initial["brand"]
            )

        if self.data and "brand" in self.data:
            try:
                brandId = self.data.get("brand")
                self.fields["model"].queryset = CarModel.objects.filter(
                    brand_id=brandId
                )
            except (ValueError, TypeError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        brand = cleaned_data.get("brand")
        model = cleaned_data.get("model")
        if brand and model:
            if model.brand != brand:
                self.add_error(
                    "model", "Выбранная модель не соответствует выбранной марке."
                )

        return cleaned_data

    def save(self, user):
        car = Car(
            year=self.cleaned_data["year"],
            model=self.cleaned_data["model"],
            license_plate=self.cleaned_data["license_plate"],
            vin=self.cleaned_data.get("vin"),
            owner=user,
        )
        car.save()
        return car


class AppointmentForm(forms.Form):
    service_center = forms.ModelChoiceField(
        queryset=ServiceCenter.objects.all(),
        empty_label="Выберите автосервис",
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Автосервис",
    )
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.all(),
        empty_label="Сначала выберите автосервис",
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Тип услуги",
    )

    car = forms.ModelChoiceField(
        queryset=Car.objects.all(),
        empty_label="Выберите автомобиль",
        widget=forms.Select(attrs={"class": "form-control"}),
        required=True,
        label="Автомобиль",
    )

    scheduled_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "min": date.today().isoformat(),
            }
        ),
        required=True,
        label="Дата записи",
    )

    scheduled_time = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={"class": "form-control"}),
        required=True,
        label="Время записи",
    )

    notes = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Дополнительные пожелания или описание проблемы",
            }
        ),
        required=False,
        label="Примечания",
    )

    class Meta:
        model = Appointment
        fields = [
            "car",
            "service_center",
            "service_type",
            "scheduled_date",
            "scheduled_time",
            "notes",
        ]
        widgets = {
            "scheduled_date": forms.HiddenInput(),
            "scheduled_time": forms.HiddenInput(),
            "notes": forms.Textarea(
                attrs={"class": "form-control notes-textarea", "rows": 4}
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["scheduled_time"].choices = self.generate_time_slots()
        if user is not None:
            self.fields["car"].queryset = Car.objects.filter(owner=user)

    def generate_time_slots(self):
        """Генерирует список доступных временных слотов"""
        time_slots = []
        start_time = datetime.strptime("09:00", "%H:%M")
        end_time = datetime.strptime("18:00", "%H:%M")
        slot_duration = timedelta(minutes=30)

        current_time = start_time
        while current_time <= end_time:
            if not (
                datetime.strptime("13:00", "%H:%M")
                <= current_time
                < datetime.strptime("14:00", "%H:%M")
            ):
                time_slots.append(
                    (current_time.strftime("%H:%M"), current_time.strftime("%H:%M"))
                )
            current_time += slot_duration

        return time_slots

    def clean(self):
        cleaned_data = super().clean()
        service_type = cleaned_data.get("service_type")
        scheduled_date = cleaned_data.get("scheduled_date")
        scheduled_time = cleaned_data.get("scheduled_time")

        if service_type and scheduled_date and scheduled_time:

            if scheduled_date < date.today():
                raise ValidationError("Нельзя записаться на прошедшую дату.")

            if scheduled_date == date.today():
                now = datetime.now().time()
                selected_time = datetime.strptime(scheduled_time, "%H:%M").time()
                if selected_time <= now:
                    raise ValidationError(
                        "Нельзя записаться на уже прошедшее время сегодня."
                    )
            day_of_week = scheduled_date.isoweekday()
            try:
                working_hours = WorkingHours.objects.get(day_of_week=day_of_week)
                if not working_hours.is_working:
                    raise ValidationError("Выбранная дата не является рабочим днем.")
            except WorkingHours.DoesNotExist:
                raise ValidationError("На выбранную дату запись невозможна.")

            scheduled_time_obj = datetime.strptime(scheduled_time, "%H:%M").time()
            scheduled_datetime = datetime.combine(scheduled_date, scheduled_time_obj)

            start_datetime = datetime.combine(scheduled_date, working_hours.start_time)
            end_datetime = datetime.combine(scheduled_date, working_hours.end_time)

            if not (start_datetime <= scheduled_datetime <= end_datetime):
                raise ValidationError("Выбранное время вне рабочего времени.")

            # Дополнительно проверим, что услуга полностью укладывается в рабочие часы
            if (
                scheduled_datetime + timedelta(minutes=service_type.duration)
                > end_datetime
            ):
                raise ValidationError(
                    "Выбранная услуга не успевает завершиться до конца рабочего дня. Выберите более раннее время."
                )

            start_time_obj = datetime.strptime(scheduled_time, "%H:%M").time()
            end_time_obj = (
                scheduled_datetime + timedelta(minutes=service_type.duration)
            ).time()

            # Проверяем занятость только в выбранном филиале и корректно определяем пересечение интервалов
            # Пересечение, если (existing.start < new.end) и (existing.end > new.start)
            service_center = cleaned_data.get("service_center")
            qs = Appointment.objects.filter(
                scheduled_date=scheduled_date,
                status__in=["SCHEDULED", "IN_PROGRESS"],
            )
            if service_center:
                qs = qs.filter(service_center=service_center)

            conflicting_appointments = qs.filter(
                scheduled_time__lt=end_time_obj,
                end_time__gt=start_time_obj,
            )

            if conflicting_appointments.exists():
                raise ValidationError(
                    "Выбранное время уже занято. Пожалуйста, выберите другое время."
                )

        return cleaned_data


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
