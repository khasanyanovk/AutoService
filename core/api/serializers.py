from rest_framework import serializers
from ..models import Car, Appointment, ServiceType, ServiceCenter
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
