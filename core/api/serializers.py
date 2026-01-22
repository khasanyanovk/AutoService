from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from ..models import Car, Appointment, ServiceType, ServiceCenter
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
    class Meta:
        model = Car
        fields = ['id', 'model', 'year', 'license_plate', 'vin', 'photo']


class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = ['id', 'name', 'description', 'duration', 'price']


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