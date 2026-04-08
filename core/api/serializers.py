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
    # Используем UUIDField для model_id вместо PrimaryKeyRelatedField
    model_id = serializers.UUIDField(write_only=True)
    model_name = serializers.SerializerMethodField(read_only=True)
    brand_name = serializers.SerializerMethodField(read_only=True)
    photo_url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Car
        fields = [
            'id', 
            'model_id',  # для создания/обновления (UUID)
            'model',      # для чтения (ID модели)
            'model_name', # для чтения (название модели)
            'brand_name', # для чтения (название марки)
            'year', 
            'license_plate', 
            'vin', 
            'photo',
            'photo_url'
        ]
        read_only_fields = ['id', 'model', 'photo_url', 'model_name', 'brand_name']
    
    def get_model_name(self, obj):
        return obj.model.name if obj.model else None
    
    def get_brand_name(self, obj):
        return obj.model.brand.name if obj.model else None
    
    def get_photo_url(self, obj):
        return obj.get_photo_url()
    
    def validate_model_id(self, value):
        """Проверяем, существует ли модель с таким UUID"""
        from ..models import CarModel
        try:
            model = CarModel.objects.get(id=value)
            return model
        except CarModel.DoesNotExist:
            raise serializers.ValidationError(f"Модель с ID {value} не существует")
    
    def create(self, validated_data):
        # Извлекаем model_id и заменяем на объект модели
        model = validated_data.pop('model_id')
        validated_data['model'] = model
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Для обновления тоже обрабатываем model_id
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