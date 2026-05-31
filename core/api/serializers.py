import re
from datetime import datetime, timedelta
from django.core.validators import MinValueValidator, MaxValueValidator
from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from ..models import (
    Car,
    Appointment,
    ServiceType,
    ServiceCenter,
    CarModel,
    CarBrand,
    WorkingHours,
    Review,
    UserProfile,
    Employee,
    BlockedTimeSlot,
)
from core.forms import UserRegisterForm
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["email"] = user.email
        token["is_staff"] = user.is_staff
        return token


class UserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    email = serializers.EmailField()
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["password1"] != data["password2"]:
            raise serializers.ValidationError({"password": "Пароли не совпадают."})
        try:
            validate_password(data["password1"])
        except Exception as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        if User.objects.filter(username=data["username"]).exists():
            raise serializers.ValidationError(
                {"username": "Пользователь с таким логином уже существует."}
            )
        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError(
                {"email": "Пользователь с таким email уже существует."}
            )
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            email=validated_data["email"],
            password=validated_data["password1"],
        )
        return user


class CarSerializer(serializers.ModelSerializer):
    model_id = serializers.UUIDField(write_only=True)
    model_name = serializers.SerializerMethodField(read_only=True)
    brand_name = serializers.SerializerMethodField(read_only=True)
    photo_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Car
        fields = [
            "id",
            "model_id",
            "model",
            "model_name",
            "brand_name",
            "year",
            "license_plate",
            "vin",
            "photo",
            "photo_url",
        ]
        read_only_fields = ["id", "model", "photo_url", "model_name", "brand_name"]

    def validate_year(self, value):
        """Проверка года выпуска"""
        current_year = datetime.now().year
        if value < 1900:
            raise serializers.ValidationError(
                "Год выпуска не может быть раньше 1900 года."
            )
        if value > current_year:
            raise serializers.ValidationError(
                f"Год выпуска не может быть больше {current_year}."
            )
        return value

    def validate_license_plate(self, value):
        """Проверка формата гос. номера (российский формат)"""
        if not value:
            raise serializers.ValidationError("Гос. номер обязателен.")

        value = value.strip().upper()

        allowed_ru = "АВЕКМНОРСТУХ"
        allowed_lat = "ABEKMHOPCTYX"

        pattern = r"^[АВЕКМНОРСТУХABEKMHOPCTYX]{1}\d{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}$"

        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Номер должен быть в формате X000XX (буква, 3 цифры, 2 буквы)."
            )

        for char in value:
            if char.isalpha():
                if char not in allowed_ru and char not in allowed_lat:
                    raise serializers.ValidationError(
                        f"Буква '{char}' недопустима в российских номерах. "
                        f"Допустимые русские буквы: {', '.join(allowed_ru)}. "
                        f"Допустимые латинские: {', '.join(allowed_lat)}."
                    )

        existing = Car.objects.filter(license_plate=value)
        if self.instance:
            existing = existing.exclude(id=self.instance.id)
        if existing.exists():
            raise serializers.ValidationError(
                "Автомобиль с таким гос. номером уже существует."
            )

        return value

    def validate_vin(self, value):
        """Проверка VIN-кода"""
        if not value:
            return value

        value = value.strip().upper()

        if len(value) != 17:
            raise serializers.ValidationError(
                "VIN-код должен содержать ровно 17 символов."
            )

        if not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", value):
            raise serializers.ValidationError(
                "VIN-код должен содержать только латинские буквы (кроме I, O, Q) и цифры."
            )

        existing = Car.objects.filter(vin=value)
        if self.instance:
            existing = existing.exclude(id=self.instance.id)
        if existing.exists():
            raise serializers.ValidationError(
                "Автомобиль с таким VIN-кодом уже существует."
            )

        return value

    def validate_photo(self, value):
        """Проверка загружаемого фото"""
        if not value:
            return value

        max_size = 3 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Размер фото не должен превышать 3 МБ.")

        import os

        valid_extensions = [".jpg", ".jpeg", ".png"]
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in valid_extensions:
            raise serializers.ValidationError(
                "Допустимые форматы фото: JPG, JPEG, PNG."
            )

        return value

    def validate_model_id(self, value):
        """Проверяем, существует ли модель с таким UUID"""
        try:
            model = CarModel.objects.select_related("brand").get(id=value)
            return model
        except CarModel.DoesNotExist:
            raise serializers.ValidationError(f"Модель с ID {value} не существует")

    def validate(self, data):
        """Перекрестная валидация"""
        return data

    def get_model_name(self, obj):
        return obj.model.name if obj.model else None

    def get_brand_name(self, obj):
        return obj.model.brand.name if obj.model else None

    def get_photo_url(self, obj):
        return obj.get_photo_url()

    def create(self, validated_data):
        model = validated_data.pop("model_id")
        validated_data["model"] = model
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "model_id" in validated_data:
            model = validated_data.pop("model_id")
            validated_data["model"] = model
        return super().update(instance, validated_data)


class CarBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarBrand
        fields = ["id", "name"]


class CarModelSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.name", read_only=True)

    class Meta:
        model = CarModel
        fields = ["id", "name", "brand", "brand_name"]


class WorkingHoursSerializer(serializers.ModelSerializer):
    day_of_week_display = serializers.CharField(
        source="get_day_of_week_display", read_only=True
    )

    class Meta:
        model = WorkingHours
        fields = [
            "id",
            "day_of_week",
            "day_of_week_display",
            "start_time",
            "end_time",
            "lunch_start",
            "lunch_end",
            "is_working",
        ]


class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = ["id", "name", "description", "duration", "price", "is_active"]


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    user_avatar = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "user_name",
            "user_avatar",
            "rating",
            "comment",
            "admin_reply",
            "admin_reply_at",
            "created_at",
        ]
        read_only_fields = ["id", "admin_reply", "admin_reply_at", "created_at"]

    def get_user_avatar(self, obj):
        """Возвращает URL аватара пользователя"""
        try:
            if hasattr(obj.user, "userprofile") and obj.user.userprofile.avatar:
                return obj.user.userprofile.avatar.url
        except Exception:
            pass
        return None

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Оценка должна быть от 1 до 5")
        return value

    def validate_comment(self, value):
        if len(value.strip()) < 20:
            raise serializers.ValidationError(
                "Комментарий должен содержать минимум 20 символов"
            )
        return value


class ServiceCenterDetailSerializer(serializers.ModelSerializer):
    """Расширенный сериализатор с полной информацией о филиале"""

    photo_url = serializers.SerializerMethodField()

    services = ServiceTypeSerializer(many=True, read_only=True)
    working_hours = WorkingHoursSerializer(many=True, read_only=True)

    reviews_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    latest_reviews = serializers.SerializerMethodField()
    is_open_now = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCenter
        fields = [
            "id",
            "address",
            "phone",
            "opening_hours",
            "photo_url",
            "services",
            "working_hours",
            "reviews_count",
            "average_rating",
            "latest_reviews",
            "is_open_now",
        ]

    def get_photo_url(self, obj):
        return obj.get_photo_url()

    def get_reviews_count(self, obj):
        return obj.reviews.count()

    def get_average_rating(self, obj):
        from django.db.models import Avg

        avg = obj.reviews.aggregate(avg=Avg("rating"))["avg"]
        return round(avg, 1) if avg else 0

    def get_latest_reviews(self, obj):
        latest = obj.reviews.select_related("user").order_by("-created_at")[:5]
        return ReviewSerializer(latest, many=True).data

    def get_is_open_now(self, obj):
        """Проверяет, открыт ли филиал сейчас"""
        from django.utils import timezone

        now = timezone.localtime(timezone.now())
        day_of_week = now.isoweekday()
        current_time = now.time()

        try:
            wh = obj.working_hours.get(day_of_week=day_of_week)
            if not wh.is_working:
                return False

            if wh.lunch_start and wh.lunch_end:
                if wh.lunch_start <= current_time <= wh.lunch_end:
                    return False

            return wh.start_time <= current_time <= wh.end_time
        except Exception:
            return False


class AppointmentCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания записи"""

    car_id = serializers.UUIDField(write_only=True)
    service_type_id = serializers.UUIDField(write_only=True)
    service_center_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "car_id",
            "service_type_id",
            "service_center_id",
            "scheduled_date",
            "scheduled_time",
            "notes",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate_car_id(self, value):
        """Проверяем, что автомобиль принадлежит пользователю"""
        try:
            car = Car.objects.get(id=value)
        except Car.DoesNotExist:
            raise serializers.ValidationError("Автомобиль не найден")

        request = self.context.get("request")
        if car.owner != request.user:
            raise serializers.ValidationError(
                "Вы не можете записаться на чужой автомобиль"
            )

        return car

    def validate_service_type_id(self, value):
        """Проверяем существование услуги"""
        try:
            service_type = ServiceType.objects.select_related("service_center").get(
                id=value, is_active=True
            )
            return service_type
        except ServiceType.DoesNotExist:
            raise serializers.ValidationError("Услуга не найдена или неактивна")

    def validate_service_center_id(self, value):
        """Проверяем существование филиала"""
        try:
            service_center = ServiceCenter.objects.get(id=value)
            return service_center
        except ServiceCenter.DoesNotExist:
            raise serializers.ValidationError("Автосервис не найден")

    def validate_scheduled_date(self, value):
        """Проверка даты"""
        today = timezone.localtime(timezone.now()).date()

        if value < today:
            raise serializers.ValidationError("Нельзя записаться на прошедшую дату")

        max_date = today + timedelta(days=30)
        if value > max_date:
            raise serializers.ValidationError(
                "Запись возможна не более чем на 30 дней вперед"
            )

        return value

    def validate(self, data):
        """Комплексная валидация"""
        car = data.get("car_id")
        service_type = data.get("service_type_id")
        service_center = data.get("service_center_id")
        scheduled_date = data.get("scheduled_date")
        scheduled_time = data.get("scheduled_time")

        if not all([car, service_type, service_center, scheduled_date, scheduled_time]):
            raise serializers.ValidationError("Все поля обязательны для заполнения")

        if service_type.service_center_id != service_center.id:
            raise serializers.ValidationError(
                {
                    "service_type_id": "Выбранная услуга не предоставляется в этом автосервисе"
                }
            )

        today = timezone.localtime(timezone.now()).date()
        if scheduled_date == today:
            now = timezone.localtime(timezone.now()).time()
            if scheduled_time <= now:
                raise serializers.ValidationError(
                    {"scheduled_time": "Нельзя записаться на уже прошедшее время"}
                )

        from ..models import WorkingHours

        day_of_week = scheduled_date.isoweekday()

        try:
            working_hours = WorkingHours.objects.get(
                service_center=service_center, day_of_week=day_of_week
            )

            if not working_hours.is_working:
                raise serializers.ValidationError(
                    {"scheduled_date": "Выбранный день не является рабочим"}
                )

            if not (
                working_hours.start_time <= scheduled_time <= working_hours.end_time
            ):
                raise serializers.ValidationError(
                    {"scheduled_time": "Выбранное время вне рабочего времени"}
                )

            scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)
            end_datetime = scheduled_datetime + timedelta(minutes=service_type.duration)

            if end_datetime.time() > working_hours.end_time:
                raise serializers.ValidationError(
                    {
                        "scheduled_time": "Услуга не успеет завершиться до конца рабочего дня"
                    }
                )

            if working_hours.lunch_start and working_hours.lunch_end:
                lunch_start_dt = datetime.combine(
                    scheduled_date, working_hours.lunch_start
                )
                lunch_end_dt = datetime.combine(scheduled_date, working_hours.lunch_end)

                if not (
                    end_datetime <= lunch_start_dt or scheduled_datetime >= lunch_end_dt
                ):
                    raise serializers.ValidationError(
                        {
                            "scheduled_time": "Выбранное время попадает на обеденный перерыв"
                        }
                    )

        except WorkingHours.DoesNotExist:
            raise serializers.ValidationError(
                {"scheduled_date": "На выбранный день нет расписания работы"}
            )

        conflicting = Appointment.objects.filter(
            service_center=service_center,
            scheduled_date=scheduled_date,
            status__in=["SCHEDULED", "IN_PROGRESS"],
        ).filter(
            scheduled_time__lt=(
                datetime.combine(scheduled_date, scheduled_time)
                + timedelta(minutes=service_type.duration)
            ).time(),
            end_time__gt=scheduled_time,
        )

        if conflicting.exists():
            raise serializers.ValidationError(
                {"scheduled_time": "Выбранное время уже занято"}
            )

        from ..models import BlockedTimeSlot

        if BlockedTimeSlot.objects.filter(
            service_center=service_center, date=scheduled_date, time=scheduled_time
        ).exists():
            raise serializers.ValidationError(
                {"scheduled_time": "Это время заблокировано администратором"}
            )

        return data

    def create(self, validated_data):
        car = validated_data.pop("car_id")
        service_type = validated_data.pop("service_type_id")
        service_center = validated_data.pop("service_center_id")

        scheduled_date = validated_data["scheduled_date"]
        scheduled_time = validated_data["scheduled_time"]
        scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)
        end_datetime = scheduled_datetime + timedelta(minutes=service_type.duration)

        appointment = Appointment.objects.create(
            car=car,
            service_type=service_type,
            service_center=service_center,
            end_time=end_datetime.time(),
            status="SCHEDULED",
            **validated_data,
        )

        return appointment


class ServiceCenterSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для списка филиалов"""

    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCenter
        fields = ["id", "address", "phone", "opening_hours", "photo_url"]

    def get_photo_url(self, obj):
        return obj.get_photo_url()


class AppointmentDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор для просмотра записи"""

    car = CarSerializer(read_only=True)
    service_type = ServiceTypeSerializer(read_only=True)
    service_center = ServiceCenterSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    can_cancel = serializers.SerializerMethodField()
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, source="get_final_price", read_only=True
    )
    payment_url = serializers.SerializerMethodField()
    is_paid = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "car",
            "service_type",
            "service_center",
            "scheduled_date",
            "scheduled_time",
            "end_time",
            "status",
            "status_display",
            "notes",
            "created_at",
            "updated_at",
            "can_cancel",
            "total_price",
            "payment_url",
            "is_paid",
            "payment_status",
        ]

    def get_is_paid(self, obj):
        """Проверяет, есть ли успешный платеж"""
        from payments.models import Payment

        return Payment.objects.filter(appointment=obj, status="succeeded").exists()

    def get_payment_status(self, obj):
        """Возвращает статус последнего платежа"""
        from payments.models import Payment

        payment = (
            Payment.objects.filter(appointment=obj).order_by("-created_at").first()
        )
        return payment.status if payment else None

    def get_payment_url(self, obj):
        """URL для оплаты (ведет на веб-страницу записи)"""
        if obj.status == "SCHEDULED":
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(f"/appointments/{obj.id}/")
        return None

    def get_can_cancel(self, obj):
        """Можно ли отменить запись"""
        if obj.status != "SCHEDULED":
            return False

        now = timezone.localtime(timezone.now())
        appointment_datetime = datetime.combine(obj.scheduled_date, obj.scheduled_time)
        appointment_datetime = timezone.make_aware(appointment_datetime)

        return (appointment_datetime - now).total_seconds() > 7200

    def get_total_price(self, obj):
        """Итоговая цена с учетом скидок"""
        return float(obj.get_final_price())


class TimeSlotSerializer(serializers.Serializer):
    """Сериализатор для временных слотов"""

    time = serializers.TimeField()
    available = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True)


class AvailableServicesSerializer(serializers.Serializer):
    """Сериализатор для получения услуг филиала"""

    service_center_id = serializers.UUIDField(required=True)


class AvailableTimeSlotsSerializer(serializers.Serializer):
    """Сериализатор для запроса доступных слотов"""

    service_center_id = serializers.UUIDField(required=True)
    service_type_id = serializers.UUIDField(required=True)
    date = serializers.DateField(required=True)


class UserProfileSerializer(serializers.ModelSerializer):
    """Профиль пользователя"""

    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ["phone", "address", "avatar", "avatar_url"]
        read_only_fields = ["avatar_url"]

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url

        request = self.context.get("request")
        default_path = "/static/core/img/default-avatar.png"

        if request:
            return request.build_absolute_uri(default_path)
        return default_path


class UserSerializer(serializers.ModelSerializer):
    """Пользователь с профилем"""

    profile = UserProfileSerializer(source="userprofile", read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "profile",
            "is_staff",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class UserUpdateSerializer(serializers.Serializer):
    """Обновление данных пользователя"""

    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        user = self.context["request"].user
        if User.objects.filter(email=value).exclude(id=user.id).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует"
            )
        return value

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        if "email" in validated_data:
            instance.email = validated_data["email"]
        instance.save()

        profile = instance.userprofile
        if "phone" in validated_data:
            profile.phone = validated_data["phone"]
        if "address" in validated_data:
            profile.address = validated_data["address"]
        profile.save()

        return instance


class AvatarUploadSerializer(serializers.Serializer):
    """Загрузка аватара"""

    avatar = serializers.ImageField()

    def validate_avatar(self, value):
        if value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("Размер файла не должен превышать 2 МБ")

        import os

        ext = os.path.splitext(value.name)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png"]:
            raise serializers.ValidationError("Допустимые форматы: JPG, PNG")

        return value

    def save(self, user):
        profile = user.userprofile
        profile.avatar = self.validated_data["avatar"]
        profile.save()
        return profile


class ProfileStatsSerializer(serializers.Serializer):
    """Статистика профиля"""

    total_appointments = serializers.IntegerField()
    completed_appointments = serializers.IntegerField()
    cancelled_appointments = serializers.IntegerField()
    total_spent = serializers.FloatField()
    average_check = serializers.FloatField()
    first_visit = serializers.DateField(allow_null=True)
    last_visit = serializers.DateField(allow_null=True)

    visits_by_month = serializers.DictField()
    top_services = serializers.ListField()
    top_centers = serializers.ListField()
    by_weekday = serializers.ListField()
    by_hour = serializers.ListField()


class LoyaltyAccountSerializer(serializers.Serializer):
    """Программа лояльности"""

    status = serializers.CharField()
    status_display = serializers.CharField()
    bonus_balance = serializers.FloatField()
    total_spent = serializers.FloatField()
    next_status = serializers.CharField(allow_null=True)
    next_status_progress = serializers.FloatField()
    personal_discount = serializers.FloatField()


class AdminAppointmentSerializer(serializers.ModelSerializer):
    """Сериализатор записи для админа (с данными клиента)"""

    car_info = serializers.SerializerMethodField()
    client_name = serializers.SerializerMethodField()
    client_email = serializers.SerializerMethodField()
    client_phone = serializers.SerializerMethodField()
    service_name = serializers.CharField(source="service_type.name", read_only=True)
    service_duration = serializers.IntegerField(
        source="service_type.duration", read_only=True
    )
    center_address = serializers.CharField(
        source="service_center.address", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_paid = serializers.SerializerMethodField()
    payment_info = serializers.SerializerMethodField()
    vin = serializers.CharField(source="car.vin", read_only=True)
    total_price = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "car_info",
            "client_name",
            "client_email",
            "client_phone",
            "service_name",
            "service_duration",
            "center_address",
            "scheduled_date",
            "scheduled_time",
            "end_time",
            "status",
            "status_display",
            "notes",
            "is_paid",
            "payment_info",
            "vin",
            "created_at",
            "updated_at",
            "total_price",
            "payment_status",
        ]

    def get_total_price(self, obj):
        return float(obj.get_base_price())

    def get_client_email(self, obj):
        return obj.car.owner.email

    def get_payment_info(self, obj):
        from payments.models import Payment

        payment = Payment.objects.filter(appointment=obj, status="succeeded").first()
        if payment:
            return {
                "status": "succeeded",
                "paid_at": payment.paid_at,
                "amount": float(payment.amount),
            }
        return None

    def get_payment_status(self, obj):
        from payments.models import Payment

        payment = (
            Payment.objects.filter(appointment=obj).order_by("-created_at").first()
        )
        return payment.status if payment else None

    def get_car_info(self, obj):
        return (
            f"{obj.car.model.brand.name} {obj.car.model.name} ({obj.car.license_plate})"
        )

    def get_client_name(self, obj):
        return obj.car.owner.get_full_name() or obj.car.owner.username

    def get_client_phone(self, obj):
        return (
            obj.car.owner.userprofile.phone
            if hasattr(obj.car.owner, "userprofile")
            else None
        )

    def get_is_paid(self, obj):
        from payments.models import Payment

        return (
            Payment.objects.filter(appointment=obj, status="succeeded").exists()
            or obj.paid_amount is not None
        )


class AdminStatsSerializer(serializers.Serializer):
    """Статистика для дашборда"""

    today_appointments = serializers.IntegerField()
    today_completed = serializers.IntegerField()
    today_revenue = serializers.FloatField()
    pending_count = serializers.IntegerField()
    in_progress_count = serializers.IntegerField()
    total_clients = serializers.IntegerField()
    average_rating = serializers.FloatField()


class AdminDashboardSerializer(serializers.Serializer):
    """Полный дашборд"""

    today = serializers.DictField()
    pending = serializers.DictField()
    revenue = serializers.DictField()
    upcoming = serializers.ListField()
    chart = serializers.DictField()
    centers = serializers.ListField()
    reviews_pending = serializers.IntegerField()


class AdminReviewSerializer(serializers.ModelSerializer):
    """Отзыв для админа"""

    user_name = serializers.SerializerMethodField()
    user_phone = serializers.SerializerMethodField()
    center_address = serializers.CharField(
        source="service_center.address", read_only=True
    )

    class Meta:
        model = Review
        fields = [
            "id",
            "user_name",
            "user_phone",
            "center_address",
            "rating",
            "comment",
            "admin_reply",
            "admin_reply_at",
            "created_at",
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_user_phone(self, obj):
        return obj.user.userprofile.phone if hasattr(obj.user, "userprofile") else None


class BlockSlotSerializer(serializers.Serializer):
    """Блокировка слота"""

    center_id = serializers.UUIDField()
    date = serializers.DateField()
    time = serializers.TimeField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ChangeStatusSerializer(serializers.Serializer):
    """Смена статуса записи"""

    status = serializers.ChoiceField(
        choices=["SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"]
    )


class AdminServiceTypeSerializer(serializers.ModelSerializer):
    """Услуга для админа"""

    center_address = serializers.CharField(
        source="service_center.address", read_only=True
    )

    class Meta:
        model = ServiceType
        fields = [
            "id",
            "name",
            "description",
            "duration",
            "price",
            "service_center",
            "center_address",
            "is_active",
        ]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть больше нуля")
        return value

    def validate_duration(self, value):
        if value <= 0:
            raise serializers.ValidationError("Длительность должна быть больше нуля")
        return value


class AdminServiceCenterSerializer(serializers.ModelSerializer):
    """Филиал для админа"""

    services_count = serializers.SerializerMethodField()
    working_hours = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCenter
        fields = [
            "id",
            "address",
            "phone",
            "opening_hours",
            "photo",
            "services_count",
            "working_hours",
            "photo_url",
        ]

    def get_photo_url(self, obj):
        return obj.get_photo_url()

    def get_services_count(self, obj):
        return obj.services.count()

    def get_working_hours(self, obj):
        from .serializers import WorkingHoursSerializer

        wh = obj.working_hours.all().order_by("day_of_week")
        return WorkingHoursSerializer(wh, many=True).data


class AdminWorkingHoursSerializer(serializers.ModelSerializer):
    """Рабочие часы для админа"""

    day_display = serializers.CharField(
        source="get_day_of_week_display", read_only=True
    )

    class Meta:
        model = WorkingHours
        fields = [
            "id",
            "service_center",
            "day_of_week",
            "day_display",
            "start_time",
            "end_time",
            "lunch_start",
            "lunch_end",
            "is_working",
        ]

    def validate(self, data):
        if data.get("start_time") and data.get("end_time"):
            if data["start_time"] >= data["end_time"]:
                raise serializers.ValidationError(
                    {"end_time": "Время окончания должно быть позже начала"}
                )
        return data


class AdminEmployeeSerializer(serializers.ModelSerializer):
    """Сотрудник для админа"""

    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    position_display = serializers.CharField(
        source="get_position_display", read_only=True
    )

    class Meta:
        model = Employee
        fields = [
            "id",
            "user",
            "username",
            "full_name",
            "email",
            "position",
            "position_display",
            "phone",
            "hire_date",
            "salary",
        ]


class AdminCreateEmployeeSerializer(serializers.Serializer):
    """Создание сотрудника"""

    username = serializers.CharField(max_length=150)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    position = serializers.ChoiceField(choices=["MECH", "MAN", "DIR"])
    phone = serializers.CharField(max_length=20)
    salary = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким логином уже существует"
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует"
            )
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data.pop("password"),
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )

        employee = Employee.objects.create(
            user=user,
            position=validated_data["position"],
            phone=validated_data["phone"],
            salary=validated_data["salary"],
            hire_date=timezone.now().date(),
        )

        return employee


class AdminClientListSerializer(serializers.ModelSerializer):
    from django.utils import timezone

    date_joined = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    cars_count = serializers.SerializerMethodField()
    appointments_count = serializers.SerializerMethodField()
    active_appointments_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "full_name",
            "email",
            "phone",
            "cars_count",
            "appointments_count",
            "active_appointments_count",
            "date_joined",
            "is_staff",
        ]

    def get_date_joined(self, obj):
        local_time = timezone.localtime(obj.date_joined)
        return local_time.strftime("%d.%m.%Y %H:%M")

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_phone(self, obj):
        if hasattr(obj, "userprofile"):
            return obj.userprofile.phone
        return None

    def get_cars_count(self, obj):
        return Car.objects.filter(owner=obj).count()

    def get_appointments_count(self, obj):
        return Appointment.objects.filter(car__owner=obj).count()

    def get_active_appointments_count(self, obj):
        return Appointment.objects.filter(
            car__owner=obj, status__in=["SCHEDULED", "IN_PROGRESS"]
        ).count()
