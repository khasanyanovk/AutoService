from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from .serializers import (
    CarSerializer,
    CarBrandSerializer,
    CarModelSerializer,
    AppointmentSerializer,
    ServiceTypeSerializer,
    ServiceCenterSerializer,
    MyTokenObtainPairSerializer,
    UserRegisterSerializer
)
from ..models import Car, Appointment, ServiceType, ServiceCenter
from django.contrib.auth import login


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            login(request, user)
            return Response({"success": True, "id": user.id, "username": user.username}, status=status.HTTP_201_CREATED)
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


# JWT token view
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


# Автомобили пользователя
class CarViewSet(viewsets.ModelViewSet):
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Car.objects.filter(owner=self.request.user).select_related('model__brand')
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Стандартный create с улучшенной обработкой ошибок"""
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            self.perform_create(serializer)
        except IntegrityError as e:
            error_msg = str(e).lower()
            errors = {}
            if 'license_plate' in error_msg:
                errors['license_plate'] = ['Автомобиль с таким гос. номером уже существует.']
            elif 'vin' in error_msg:
                errors['vin'] = ['Автомобиль с таким VIN-кодом уже существует.']
            else:
                errors['non_field_errors'] = ['Ошибка целостности данных.']
            
            return Response({
                'success': False,
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        headers = self.get_success_headers(serializer.data)
        return Response({
            'success': True,
            'message': 'Автомобиль успешно добавлен',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """Обновление автомобиля с проверкой владельца"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            return Response({
                'success': True,
                'message': 'Автомобиль успешно обновлен',
                'data': serializer.data
            })
        except ValidationError as e:
            return Response({
                'success': False,
                'errors': e.message_dict
            }, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            error_msg = str(e).lower()
            if 'license_plate' in error_msg:
                return Response({
                    'success': False,
                    'errors': {'license_plate': 'Автомобиль с таким гос. номером уже существует.'}
                }, status=status.HTTP_400_BAD_REQUEST)
            elif 'vin' in error_msg:
                return Response({
                    'success': False,
                    'errors': {'vin': 'Автомобиль с таким VIN-кодом уже существует.'}
                }, status=status.HTTP_400_BAD_REQUEST)
            return Response({
                'success': False,
                'errors': {'non_field_errors': 'Автомобиль с таким гос. номером или VIN уже существует.'}
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        """Удаление автомобиля с проверкой"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'success': True,
            'message': 'Автомобиль успешно удален'
        }, status=status.HTTP_200_OK)

from ..models import CarBrand, CarModel

class CarBrandViewSet(viewsets.ReadOnlyModelViewSet):
    """Эндпоинт для получения списка марок автомобилей"""
    queryset = CarBrand.objects.all().order_by('name')
    serializer_class = CarBrandSerializer
    permission_classes = [AllowAny]


class CarModelViewSet(viewsets.ReadOnlyModelViewSet):
    """Эндпоинт для получения моделей по марке"""
    serializer_class = CarModelSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = CarModel.objects.all().select_related('brand').order_by('name')
        brand_id = self.request.query_params.get('brand_id', None)
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        return queryset

# Записи пользователя
class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(car__owner=self.request.user)


# Услуги
class ServiceTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceType.objects.all()
    serializer_class = ServiceTypeSerializer
    permission_classes = [AllowAny]


# Сервисные центры
class ServiceCenterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceCenter.objects.all()
    serializer_class = ServiceCenterSerializer
    permission_classes = [AllowAny]