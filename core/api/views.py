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
    ServiceCenterDetailSerializer,
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
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        """Используем разные сериализаторы для списка и деталей"""
        if self.action == 'retrieve':
            return ServiceCenterDetailSerializer
        return ServiceCenterDetailSerializer
    
    def get_queryset(self):
        """Оптимизация запросов"""
        if self.action == 'list':
            return ServiceCenter.objects.all().order_by('address')
        elif self.action == 'retrieve':
            return ServiceCenter.objects.prefetch_related(
                'services',
                'working_hours',
                'reviews',
                'reviews__user__userprofile'
            )
        return super().get_queryset()
    
    @action(detail=True, methods=['get'])
    def services(self, request, pk=None):
        """Получить все услуги филиала"""
        service_center = self.get_object()
        services = service_center.services.filter(is_active=True)
        serializer = ServiceTypeSerializer(services, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def working_hours(self, request, pk=None):
        """Получить график работы филиала"""
        service_center = self.get_object()
        working_hours = service_center.working_hours.all().order_by('day_of_week')
        serializer = WorkingHoursSerializer(working_hours, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Получить отзывы о филиале с пагинацией"""
        service_center = self.get_object()
        reviews = service_center.reviews.select_related('user').order_by('-created_at')
        
        # Пагинация
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_review(self, request, pk=None):
        """Добавить отзыв о филиале"""
        service_center = self.get_object()
        user = request.user
        
        # Проверяем, может ли пользователь оставить отзыв
        has_completed_appointment = Appointment.objects.filter(
            car__owner=user,
            service_center=service_center,
            status='COMPLETED'
        ).exists()
        
        if not has_completed_appointment:
            return Response({
                'success': False,
                'error': 'Вы можете оставить отзыв только после выполненной услуги'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Проверяем, не оставлял ли уже отзыв
        existing_review = Review.objects.filter(
            service_center=service_center,
            user=user
        ).first()
        
        if existing_review:
            return Response({
                'success': False,
                'error': 'Вы уже оставили отзыв об этом филиале'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Валидация и сохранение
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                service_center=service_center,
                user=user
            )
            return Response({
                'success': True,
                'message': 'Спасибо за отзыв!',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def nearest(self, request):
        """Найти ближайшие филиалы (требуются координаты)"""
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius = request.query_params.get('radius', 10)  # км
        
        if not lat or not lng:
            return Response({
                'error': 'Необходимы параметры lat и lng'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Заглушка - возвращаем все филиалы
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)