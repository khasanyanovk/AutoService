import re
from datetime import datetime
from django.core.validators import MinValueValidator, MaxValueValidator
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from ..models import Car, Appointment, ServiceType, ServiceCenter, CarModel, CarBrand
from core.forms import UserRegisterForm
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        return token


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

class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = ['id', 'name', 'description', 'duration', 'price', 'service_center', 'is_active']


class ServiceCenterSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCenter
        fields = ['id', 'address', 'phone', 'opening_hours', 'photo_url']

    def get_photo_url(self, obj):
        return obj.get_photo_url() if obj.get_photo_url() else None


class AppointmentSerializer(serializers.ModelSerializer):
    car = CarSerializer()
    service_type = ServiceTypeSerializer()
    service_center = ServiceCenterSerializer()

    class Meta:
        model = Appointment
        fields = [
            'id',
            'car',
            'service_type',
            'service_center',
            'scheduled_date',
            'scheduled_time',
            'status',
            'notes',
        ]


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