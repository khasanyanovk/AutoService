import re
from datetime import datetime, timedelta
from django.core.validators import MinValueValidator, MaxValueValidator
from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from ..models import Car, Appointment, ServiceType, ServiceCenter, CarModel, CarBrand, WorkingHours, Review
from core.forms import UserRegisterForm
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        return token

class UserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    email = serializers.EmailField()
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают."})
        try:
            validate_password(data['password1'])
        except Exception as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "Пользователь с таким логином уже существует."})
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "Пользователь с таким email уже существует."})
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            password=validated_data['password1'],
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
            'id', 'model_id', 'model', 'model_name', 'brand_name',
            'year', 'license_plate', 'vin', 'photo', 'photo_url'
        ]
        read_only_fields = ['id', 'model', 'photo_url', 'model_name', 'brand_name']
    
    # ========== ВАЛИДАЦИЯ ПОЛЕЙ ==========
    
    def validate_year(self, value):
        """Проверка года выпуска"""
        current_year = datetime.now().year
        if value < 1900:
            raise serializers.ValidationError("Год выпуска не может быть раньше 1900 года.")
        if value > current_year:
            raise serializers.ValidationError(f"Год выпуска не может быть больше {current_year}.")
        return value
    
    def validate_license_plate(self, value):
        """Проверка формата гос. номера (российский формат)"""
        if not value:
            raise serializers.ValidationError("Гос. номер обязателен.")
        
        value = value.strip().upper()
        
        # Допустимые буквы в российских номерах
        allowed_ru = "АВЕКМНОРСТУХ"
        allowed_lat = "ABEKMHOPCTYX"
        
        # Проверка формата: буква, 3 цифры, 2 буквы (с учетом русских и латинских букв)
        pattern = r'^[АВЕКМНОРСТУХABEKMHOPCTYX]{1}\d{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}$'
        
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Номер должен быть в формате X000XX (буква, 3 цифры, 2 буквы)."
            )
        
        # Проверка каждой буквы
        for char in value:
            if char.isalpha():
                if char not in allowed_ru and char not in allowed_lat:
                    raise serializers.ValidationError(
                        f"Буква '{char}' недопустима в российских номерах. "
                        f"Допустимые русские буквы: {', '.join(allowed_ru)}. "
                        f"Допустимые латинские: {', '.join(allowed_lat)}."
                    )
        
        # Проверка уникальности (исключая текущий экземпляр при обновлении)
        existing = Car.objects.filter(license_plate=value)
        if self.instance:
            existing = existing.exclude(id=self.instance.id)
        if existing.exists():
            raise serializers.ValidationError("Автомобиль с таким гос. номером уже существует.")
        
        return value
    
    def validate_vin(self, value):
        """Проверка VIN-кода"""
        if not value:
            return value  # VIN не обязателен
        
        value = value.strip().upper()
        
        if len(value) != 17:
            raise serializers.ValidationError("VIN-код должен содержать ровно 17 символов.")
        
        # VIN не должен содержать буквы I, O, Q
        if not re.fullmatch(r'[A-HJ-NPR-Z0-9]{17}', value):
            raise serializers.ValidationError(
                "VIN-код должен содержать только латинские буквы (кроме I, O, Q) и цифры."
            )
        
        # Проверка уникальности
        existing = Car.objects.filter(vin=value)
        if self.instance:
            existing = existing.exclude(id=self.instance.id)
        if existing.exists():
            raise serializers.ValidationError("Автомобиль с таким VIN-кодом уже существует.")
        
        return value
    
    def validate_photo(self, value):
        """Проверка загружаемого фото"""
        if not value:
            return value
        
        # Проверка размера (3 МБ)
        max_size = 3 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Размер фото не должен превышать 3 МБ.")
        
        # Проверка расширения
        import os
        valid_extensions = ['.jpg', '.jpeg', '.png']
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in valid_extensions:
            raise serializers.ValidationError(
                "Допустимые форматы фото: JPG, JPEG, PNG."
            )
        
        return value
    
    def validate_model_id(self, value):
        """Проверяем, существует ли модель с таким UUID"""
        try:
            model = CarModel.objects.select_related('brand').get(id=value)
            return model
        except CarModel.DoesNotExist:
            raise serializers.ValidationError(f"Модель с ID {value} не существует")
    
    def validate(self, data):
        """Перекрестная валидация"""
        # Проверка соответствия модели и марки (если переданы оба)
        # В нашем случае model_id уже преобразован в model в validate_model_id
        return data
    
    # ========== МЕТОДЫ ДЛЯ ЧТЕНИЯ ==========
    
    def get_model_name(self, obj):
        return obj.model.name if obj.model else None
    
    def get_brand_name(self, obj):
        return obj.model.brand.name if obj.model else None
    
    def get_photo_url(self, obj):
        return obj.get_photo_url()
    
    # ========== СОЗДАНИЕ И ОБНОВЛЕНИЕ ==========
    
    def create(self, validated_data):
        model = validated_data.pop('model_id')
        validated_data['model'] = model
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        if 'model_id' in validated_data:
            model = validated_data.pop('model_id')
            validated_data['model'] = model
        return super().update(instance, validated_data)


class CarBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarBrand
        fields = ['id', 'name']


class CarModelSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    
    class Meta:
        model = CarModel
        fields = ['id', 'name', 'brand', 'brand_name']

class WorkingHoursSerializer(serializers.ModelSerializer):
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = WorkingHours
        fields = [
            'id', 'day_of_week', 'day_of_week_display', 
            'start_time', 'end_time', 'lunch_start', 
            'lunch_end', 'is_working'
        ]

class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = ['id', 'name', 'description', 'duration', 'price', 'is_active']

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_avatar = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'user_name', 'user_avatar', 'rating', 
            'comment', 'admin_reply', 'admin_reply_at', 'created_at'
        ]
    
    def get_user_avatar(self, obj):
        if hasattr(obj.user, 'userprofile') and obj.user.userprofile.avatar:
            return obj.user.userprofile.avatar.url
        return None

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
            'id', 'address', 'phone', 'opening_hours', 'photo_url',
            'services', 'working_hours', 'reviews_count', 
            'average_rating', 'latest_reviews', 'is_open_now'
        ]
    
    def get_photo_url(self, obj):
        return obj.get_photo_url()
    
    def get_reviews_count(self, obj):
        return obj.reviews.count()
    
    def get_average_rating(self, obj):
        from django.db.models import Avg
        avg = obj.reviews.aggregate(avg=Avg('rating'))['avg']
        return round(avg, 1) if avg else 0
    
    def get_latest_reviews(self, obj):
        latest = obj.reviews.select_related('user').order_by('-created_at')[:5]
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
            'id', 'car_id', 'service_type_id', 'service_center_id',
            'scheduled_date', 'scheduled_time', 'notes',
            'status', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'created_at']
    
    def validate_car_id(self, value):
        """Проверяем, что автомобиль принадлежит пользователю"""
        try:
            car = Car.objects.get(id=value)
        except Car.DoesNotExist:
            raise serializers.ValidationError("Автомобиль не найден")
        
        request = self.context.get('request')
        if car.owner != request.user:
            raise serializers.ValidationError("Вы не можете записаться на чужой автомобиль")
        
        return car
    
    def validate_service_type_id(self, value):
        """Проверяем существование услуги"""
        try:
            service_type = ServiceType.objects.select_related('service_center').get(
                id=value, 
                is_active=True
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
            raise serializers.ValidationError("Запись возможна не более чем на 30 дней вперед")
        
        return value
    
    def validate(self, data):
        """Комплексная валидация"""
        car = data.get('car_id')
        service_type = data.get('service_type_id')
        service_center = data.get('service_center_id')
        scheduled_date = data.get('scheduled_date')
        scheduled_time = data.get('scheduled_time')
        
        if not all([car, service_type, service_center, scheduled_date, scheduled_time]):
            raise serializers.ValidationError("Все поля обязательны для заполнения")
        
        # Проверяем соответствие услуги и филиала
        if service_type.service_center_id != service_center.id:
            raise serializers.ValidationError({
                'service_type_id': 'Выбранная услуга не предоставляется в этом автосервисе'
            })
        
        # Проверяем, что запись на сегодня не в прошлом времени
        today = timezone.localtime(timezone.now()).date()
        if scheduled_date == today:
            now = timezone.localtime(timezone.now()).time()
            if scheduled_time <= now:
                raise serializers.ValidationError({
                    'scheduled_time': 'Нельзя записаться на уже прошедшее время'
                })
        
        # Проверяем рабочие часы
        from ..models import WorkingHours
        day_of_week = scheduled_date.isoweekday()
        
        try:
            working_hours = WorkingHours.objects.get(
                service_center=service_center,
                day_of_week=day_of_week
            )
            
            if not working_hours.is_working:
                raise serializers.ValidationError({
                    'scheduled_date': 'Выбранный день не является рабочим'
                })
            
            # Проверяем, что время в пределах рабочего дня
            if not (working_hours.start_time <= scheduled_time <= working_hours.end_time):
                raise serializers.ValidationError({
                    'scheduled_time': 'Выбранное время вне рабочего времени'
                })
            
            # Проверяем, что услуга завершится до конца рабочего дня
            scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)
            end_datetime = scheduled_datetime + timedelta(minutes=service_type.duration)
            
            if end_datetime.time() > working_hours.end_time:
                raise serializers.ValidationError({
                    'scheduled_time': 'Услуга не успеет завершиться до конца рабочего дня'
                })
            
            # Проверяем обеденный перерыв
            if working_hours.lunch_start and working_hours.lunch_end:
                lunch_start_dt = datetime.combine(scheduled_date, working_hours.lunch_start)
                lunch_end_dt = datetime.combine(scheduled_date, working_hours.lunch_end)
                
                if not (end_datetime <= lunch_start_dt or scheduled_datetime >= lunch_end_dt):
                    raise serializers.ValidationError({
                        'scheduled_time': 'Выбранное время попадает на обеденный перерыв'
                    })
            
        except WorkingHours.DoesNotExist:
            raise serializers.ValidationError({
                'scheduled_date': 'На выбранный день нет расписания работы'
            })
        
        # Проверяем занятость времени
        conflicting = Appointment.objects.filter(
            service_center=service_center,
            scheduled_date=scheduled_date,
            status__in=['SCHEDULED', 'IN_PROGRESS']
        ).filter(
            scheduled_time__lt=(datetime.combine(scheduled_date, scheduled_time) + 
                               timedelta(minutes=service_type.duration)).time(),
            end_time__gt=scheduled_time
        )
        
        if conflicting.exists():
            raise serializers.ValidationError({
                'scheduled_time': 'Выбранное время уже занято'
            })
        
        # Проверяем заблокированные слоты
        from ..models import BlockedTimeSlot
        if BlockedTimeSlot.objects.filter(
            service_center=service_center,
            date=scheduled_date,
            time=scheduled_time
        ).exists():
            raise serializers.ValidationError({
                'scheduled_time': 'Это время заблокировано администратором'
            })
        
        return data
    
    def create(self, validated_data):
        car = validated_data.pop('car_id')
        service_type = validated_data.pop('service_type_id')
        service_center = validated_data.pop('service_center_id')
        
        # Вычисляем время окончания
        scheduled_date = validated_data['scheduled_date']
        scheduled_time = validated_data['scheduled_time']
        scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)
        end_datetime = scheduled_datetime + timedelta(minutes=service_type.duration)
        
        appointment = Appointment.objects.create(
            car=car,
            service_type=service_type,
            service_center=service_center,
            end_time=end_datetime.time(),
            status='SCHEDULED',
            **validated_data
        )
        
        return appointment

class ServiceCenterSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для списка филиалов"""
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCenter
        fields = ['id', 'address', 'phone', 'opening_hours', 'photo_url']

    def get_photo_url(self, obj):
        return obj.get_photo_url()

class AppointmentDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор для просмотра записи"""
    car = CarSerializer(read_only=True)
    service_type = ServiceTypeSerializer(read_only=True)
    service_center = ServiceCenterSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    can_cancel = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'car', 'service_type', 'service_center',
            'scheduled_date', 'scheduled_time', 'end_time',
            'status', 'status_display', 'notes',
            'created_at', 'updated_at',
            'can_cancel', 'total_price'
        ]
    
    def get_can_cancel(self, obj):
        """Можно ли отменить запись"""
        if obj.status != 'SCHEDULED':
            return False
        
        now = timezone.localtime(timezone.now())
        appointment_datetime = datetime.combine(obj.scheduled_date, obj.scheduled_time)
        appointment_datetime = timezone.make_aware(appointment_datetime)
        
        # Нельзя отменить за 2 часа до начала
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