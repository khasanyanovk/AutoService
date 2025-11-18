import os
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import ServiceCenter, UserProfile, Car, CarBrand, CarModel
from datetime import datetime, date, timedelta
from django.forms import ValidationError
from .models import ServiceType, Appointment, WorkingHours
from .models import Review
import re
from typing import cast


class BootstrapInvalidMixin:
    """Adds 'is-invalid' CSS class to fields that have validation errors when form is validated."""

    def add_invalid_css_classes(self) -> None:
        form = cast(forms.Form, self)
        for name, field in form.fields.items():
            if name in form.errors:
                css = field.widget.attrs.get("class", "")
                if "is-invalid" not in css:
                    field.widget.attrs["class"] = (css + " is-invalid").strip()

    def is_valid(self) -> bool:
        valid = super().is_valid()  # type: ignore[misc]
        if not valid:
            self.add_invalid_css_classes()
        return valid


class UserRegisterForm(BootstrapInvalidMixin, UserCreationForm):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "username": "Логин",
            "first_name": "Имя",
            "last_name": "Фамилия",
            "email": "Email",
            "password1": "Пароль",
            "password2": "Подтверждение пароля",
        }
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()
            if name in placeholders:
                field.widget.attrs["placeholder"] = placeholders[name]


class LoginForm(BootstrapInvalidMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Логин",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Пароль",
                "id": "passwordInput",
            }
        )


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
    photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
        label="Фото автомобиля",
        help_text="Необязательно. JPG/PNG до 3MB.",
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
            model_field = self.fields.get("model")
            if isinstance(model_field, forms.ModelChoiceField):
                model_field.queryset = CarModel.objects.filter(brand=initial["brand"])

        if self.data and "brand" in self.data:
            try:
                brandId = self.data.get("brand")
                model_field = self.fields.get("model")
                if isinstance(model_field, forms.ModelChoiceField):
                    model_field.queryset = CarModel.objects.filter(brand_id=brandId)
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

    def clean_photo(self):
        photo = self.files.get("photo") if hasattr(self, "files") else None
        if not photo:
            return None
        max_size = 3 * 1024 * 1024
        if getattr(photo, "size", 0) > max_size:
            raise ValidationError("Размер фото не должен превышать 3MB.")
        valid_exts = [".jpg", ".jpeg", ".png"]
        import os

        ext = os.path.splitext(photo.name)[1].lower()
        if ext not in valid_exts:
            raise ValidationError("Допустимые форматы: JPG, JPEG, PNG.")
        return photo

    def save(self, user):
        car = Car(
            year=self.cleaned_data["year"],
            model=self.cleaned_data["model"],
            license_plate=self.cleaned_data["license_plate"],
            vin=self.cleaned_data.get("vin"),
            owner=user,
        )
        uploaded = self.cleaned_data.get("photo") or (
            self.files.get("photo") if hasattr(self, "files") else None
        )
        if uploaded:
            car.photo = uploaded  # type: ignore[assignment]
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

        if self.data:
            if "service_center" in self.data and self.data.get("service_center"):
                try:
                    sc_id = self.data.get("service_center")
                    if ServiceCenter.objects.filter(id=sc_id).exists():
                        pass
                except Exception:
                    pass

            if "service_type" in self.data and self.data.get("service_type"):
                try:
                    st_id = self.data.get("service_type")
                    sc_id = self.data.get("service_center")
                    if sc_id:
                        self.fields["service_type"].queryset = (
                            ServiceType.objects.filter(
                                service_center_id=sc_id, is_active=True
                            )
                        )
                except Exception:
                    pass

            if "scheduled_time" in self.data:
                current_time = self.data.get("scheduled_time")
                if current_time:
                    self.fields["scheduled_time"].choices = [
                        (current_time, current_time)
                    ]
            else:
                self.fields["scheduled_time"].choices = []
        else:
            self.fields["scheduled_time"].choices = []

        if user is not None:
            car_field = self.fields.get("car")
            if isinstance(car_field, forms.ModelChoiceField):
                car_field.queryset = Car.objects.filter(owner=user)

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
            service_center = cleaned_data.get("service_center")
            try:
                working_hours = WorkingHours.objects.get(
                    service_center=service_center, day_of_week=day_of_week
                )
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

            if working_hours.lunch_start and working_hours.lunch_end:
                lunch_start_dt = datetime.combine(
                    scheduled_date, working_hours.lunch_start
                )
                lunch_end_dt = datetime.combine(scheduled_date, working_hours.lunch_end)
                if not (
                    scheduled_datetime >= lunch_end_dt
                    or (scheduled_datetime + timedelta(minutes=service_type.duration))
                    <= lunch_start_dt
                ):
                    raise ValidationError(
                        "Выбранное время попадает на обеденный перерыв."
                    )

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


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "max": 5}
            ),
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Расскажите о вашем опыте обслуживания (минимум 20 символов)",
                }
            ),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if rating is None or rating < 1 or rating > 5:
            raise ValidationError("Оценка должна быть от 1 до 5.")
        return rating

    def clean_comment(self):
        comment = (self.cleaned_data.get("comment") or "").strip()
        if len(comment) < 20:
            raise ValidationError("Комментарий должен содержать минимум 20 символов.")
        return comment


class AdminReplyForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["admin_reply"]
        widgets = {
            "admin_reply": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Ответ администратора",
                }
            ),
        }
