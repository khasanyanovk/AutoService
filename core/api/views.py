from rest_framework import viewsets, status
from datetime import datetime, timedelta, date
from django.utils import timezone
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
    AppointmentCreateSerializer,
    AppointmentDetailSerializer,
    ServiceTypeSerializer,
    ServiceCenterSerializer,
    ServiceCenterDetailSerializer,
    WorkingHoursSerializer,
    ReviewSerializer,
    MyTokenObtainPairSerializer,
    UserRegisterSerializer
)
from ..models import (
    Car, Appointment, ServiceType, ServiceCenter,
    CarBrand, CarModel, WorkingHours, BlockedTimeSlot, Review
)
from django.contrib.auth import login


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            login(request, user)
            return Response(
                {"success": True, "id": user.id, "username": user.username},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class CarViewSet(viewsets.ModelViewSet):
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Car.objects.filter(owner=self.request.user).select_related('model__brand')
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    def create(self, request, *args, **kwargs):
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
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'success': True,
            'message': 'Автомобиль успешно удален'
        }, status=status.HTTP_200_OK)


class CarBrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CarBrand.objects.all().order_by('name')
    serializer_class = CarBrandSerializer
    permission_classes = [AllowAny]


class CarModelViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CarModelSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = CarModel.objects.all().select_related('brand').order_by('name')
        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        return queryset


class ServiceTypeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServiceTypeSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = ServiceType.objects.filter(is_active=True)
        service_center_id = self.request.query_params.get('service_center_id')
        if service_center_id:
            queryset = queryset.filter(service_center_id=service_center_id)
        return queryset.order_by('name')


class ServiceCenterViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ServiceCenterDetailSerializer
        return ServiceCenterSerializer
    
    def get_queryset(self):
        if self.action == 'list':
            return ServiceCenter.objects.all().order_by('address')
        elif self.action == 'retrieve':
            return ServiceCenter.objects.prefetch_related(
                'services',
                'working_hours',
                'reviews',
                'reviews__user__userprofile'
            )
        return ServiceCenter.objects.all()
    
    @action(detail=True, methods=['get'])
    def services(self, request, pk=None):
        service_center = self.get_object()
        services = service_center.services.filter(is_active=True)
        serializer = ServiceTypeSerializer(services, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def working_hours(self, request, pk=None):
        service_center = self.get_object()
        working_hours = service_center.working_hours.all().order_by('day_of_week')
        serializer = WorkingHoursSerializer(working_hours, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        service_center = self.get_object()
        reviews = service_center.reviews.select_related('user').order_by('-created_at')
        
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_review(self, request, pk=None):
        service_center = self.get_object()
        user = request.user
        
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
        
        existing_review = Review.objects.filter(
            service_center=service_center,
            user=user
        ).first()
        
        if existing_review:
            return Response({
                'success': False,
                'error': 'Вы уже оставили отзыв об этом филиале'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(service_center=service_center, user=user)
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
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        
        if not lat or not lng:
            return Response({
                'error': 'Необходимы параметры lat и lng'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AppointmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Appointment.objects.filter(
            car__owner=self.request.user
        ).select_related(
            'car__model__brand', 'service_type', 'service_center'
        ).order_by('-scheduled_date', 'scheduled_time')
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AppointmentCreateSerializer
        return AppointmentDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def available_services(self, request):
        """Получить доступные услуги филиала"""
        service_center_id = request.query_params.get('service_center_id')
        
        if not service_center_id:
            return Response({
                'error': 'Необходим параметр service_center_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        services = ServiceType.objects.filter(
            service_center_id=service_center_id,
            is_active=True
        ).order_by('name')
        
        serializer = ServiceTypeSerializer(services, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def available_time_slots(self, request):
        """Получить доступные временные слоты"""
        service_center_id = request.query_params.get('service_center_id')
        service_type_id = request.query_params.get('service_type_id')
        date_str = request.query_params.get('date')
        
        if not all([service_center_id, service_type_id, date_str]):
            return Response({
                'error': 'Необходимы параметры service_center_id, service_type_id и date'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            service_center = ServiceCenter.objects.get(id=service_center_id)
            service_type = ServiceType.objects.get(
                id=service_type_id,
                service_center_id=service_center_id,
                is_active=True
            )
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ServiceCenter.DoesNotExist:
            return Response({'error': 'Автосервис не найден'}, status=status.HTTP_404_NOT_FOUND)
        except ServiceType.DoesNotExist:
            return Response({'error': 'Услуга не найдена или недоступна'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({'error': 'Неверный формат даты. Используйте YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
        
        day_of_week = selected_date.isoweekday()
        
        try:
            working_hours = WorkingHours.objects.get(
                service_center=service_center,
                day_of_week=day_of_week
            )
            
            if not working_hours.is_working:
                return Response({
                    'slots': [],
                    'message': 'В этот день автосервис не работает'
                })
        except WorkingHours.DoesNotExist:
            return Response({
                'slots': [],
                'message': 'Нет расписания на этот день'
            })
        
        slots = self._generate_time_slots(
            working_hours.start_time,
            working_hours.end_time,
            service_type.duration,
            working_hours.lunch_start,
            working_hours.lunch_end
        )
        
        booked_appointments = Appointment.objects.filter(
            service_center=service_center,
            scheduled_date=selected_date,
            status__in=['SCHEDULED', 'IN_PROGRESS']
        )
        
        blocked_slots = BlockedTimeSlot.objects.filter(
            service_center=service_center,
            date=selected_date
        ).values_list('time', flat=True)
        
        blocked_times = set(blocked_slots)
        
        now = timezone.localtime(timezone.now())
        available_slots = []
        
        for slot_time in slots:
            if selected_date == now.date() and slot_time <= now.time():
                continue
            
            if slot_time in blocked_times:
                continue
            
            slot_end_time = (
                datetime.combine(selected_date, slot_time) + 
                timedelta(minutes=service_type.duration)
            ).time()
            
            is_available = True
            for appointment in booked_appointments:
                app_end = appointment.end_time or (
                    datetime.combine(selected_date, appointment.scheduled_time) +
                    timedelta(minutes=appointment.service_type.duration)
                ).time()
                
                if not (slot_end_time <= appointment.scheduled_time or slot_time >= app_end):
                    is_available = False
                    break
            
            if is_available:
                available_slots.append(slot_time.strftime('%H:%M'))
        
        return Response({
            'date': date_str,
            'slots': available_slots,
            'working_hours': {
                'start': working_hours.start_time.strftime('%H:%M'),
                'end': working_hours.end_time.strftime('%H:%M'),
                'lunch_start': working_hours.lunch_start.strftime('%H:%M') if working_hours.lunch_start else None,
                'lunch_end': working_hours.lunch_end.strftime('%H:%M') if working_hours.lunch_end else None,
            }
        })
    
    def _generate_time_slots(self, start_time, end_time, duration, lunch_start=None, lunch_end=None):
        slots = []
        current_time = datetime.combine(date.today(), start_time)
        end_datetime = datetime.combine(date.today(), end_time)
        step = timedelta(minutes=30)
        
        while current_time < end_datetime:
            slot_end = current_time + timedelta(minutes=duration)
            
            if slot_end.time() > end_time:
                break
            
            if lunch_start and lunch_end:
                lunch_start_dt = datetime.combine(date.today(), lunch_start)
                lunch_end_dt = datetime.combine(date.today(), lunch_end)
                
                if not (slot_end <= lunch_start_dt or current_time >= lunch_end_dt):
                    current_time += step
                    continue
            
            slots.append(current_time.time())
            current_time += step
        
        return slots
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        
        if appointment.status != 'SCHEDULED':
            return Response({
                'error': 'Можно отменить только запланированную запись'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        now = timezone.localtime(timezone.now())
        appointment_datetime = datetime.combine(
            appointment.scheduled_date, 
            appointment.scheduled_time
        )
        appointment_datetime = timezone.make_aware(appointment_datetime)
        
        if (appointment_datetime - now).total_seconds() <= 7200:
            return Response({
                'error': 'Нельзя отменить запись менее чем за 2 часа до начала'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        appointment.status = 'CANCELLED'
        appointment.save()
        
        return Response({
            'success': True,
            'message': 'Запись успешно отменена'
        })
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        now = timezone.localtime(timezone.now())
        today = now.date()
        
        upcoming = self.get_queryset().filter(
            status__in=['SCHEDULED', 'IN_PROGRESS'],
            scheduled_date__gte=today
        ).order_by('scheduled_date', 'scheduled_time').first()
        
        if upcoming:
            serializer = self.get_serializer(upcoming)
            return Response(serializer.data)
        
        return Response({'message': 'Нет предстоящих записей'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        queryset = self.get_queryset().filter(
            status__in=['COMPLETED', 'CANCELLED']
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)