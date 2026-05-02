from rest_framework import viewsets, status
from datetime import datetime, timedelta, date
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum, Q, Avg
from collections import defaultdict
from payments.services import create_payment as create_yookassa_payment
from payments.models import Payment
from rest_framework.permissions import IsAdminUser
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncDate
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from ..models import Employee


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
    UserRegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
    AvatarUploadSerializer,
    ProfileStatsSerializer,
    LoyaltyAccountSerializer,
    AdminAppointmentSerializer,
    AdminReviewSerializer,
    AdminServiceTypeSerializer,
    AdminServiceCenterSerializer,
    ChangeStatusSerializer,
    AdminWorkingHoursSerializer,
    AdminClientListSerializer
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
    
    @action(detail=True, methods=['post'])
    def sync_payment_status(self, request, pk=None):
        """Принудительно синхронизировать статус платежа с ЮKassa"""
        from payments.services import check_payment_status
        
        appointment = self.get_object()
        
        payments = Payment.objects.filter(
            appointment=appointment,
            status__in=['pending', 'waiting_for_capture']
        )
        
        for payment in payments:
            check_payment_status(payment)
        
        latest_payment = Payment.objects.filter(
            appointment=appointment
        ).order_by('-created_at').first()
        
        if latest_payment:
            check_payment_status(latest_payment)
        
        return Response({
            'is_paid': Payment.objects.filter(
                appointment=appointment, 
                status='succeeded'
            ).exists(),
            'payment_status': latest_payment.status if latest_payment else None
        })

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

    @action(detail=True, methods=['post'])
    def create_payment(self, request, pk=None):
        """Создать платеж и вернуть URL для оплаты"""
        from decimal import Decimal
        from loyalty_program.models import LoyaltyAccount
        
        appointment = self.get_object()
        
        if appointment.status == "CANCELLED":
            return Response({
                'error': 'Невозможно оплатить отмененную запись'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        existing_payment = Payment.objects.filter(
            appointment=appointment, 
            status="succeeded"
        ).first()
        
        if existing_payment:
            return Response({
                'error': 'Эта запись уже оплачена'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            loyalty_account, _ = LoyaltyAccount.objects.get_or_create(user=request.user)
            bonus_to_use = Decimal(request.data.get('bonus_amount', '0') or '0')
            
            base_price = appointment.get_base_price()
            discount_amount = loyalty_account.calculate_discount(base_price)
            final_price = loyalty_account.calculate_final_price(base_price, bonus_to_use)
            
            max_bonus = loyalty_account.calculate_max_bonus_usage(base_price - discount_amount)
            actual_bonus_used = min(bonus_to_use, max_bonus, loyalty_account.bonus_balance)
            
            return_url = request.build_absolute_uri(f'/api/appointments/{appointment.id}/payment/callback/')
            
            payment = create_yookassa_payment(
                appointment=appointment,
                return_url=return_url,
                original_amount=base_price,
                discount_applied=discount_amount,
                bonus_used=actual_bonus_used,
                final_amount=final_price,
            )
            
            return Response({
                'payment_id': str(payment.id),
                'payment_url': payment.confirmation_url,
                'amount': float(payment.amount),
                'status': payment.status
            })
            
        except Exception as e:
            return Response({
                'error': f'Ошибка создания платежа: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def payment_status(self, request, pk=None):
        """Проверить статус платежа"""
        from payments.services import check_payment_status
        
        appointment = self.get_object()
        latest_payment = Payment.objects.filter(
            appointment=appointment
        ).order_by('-created_at').first()
        
        if not latest_payment:
            return Response({
                'status': None,
                'message': 'Платеж не найден'
            })
        
        check_payment_status(latest_payment)
        
        return Response({
            'payment_id': str(latest_payment.id),
            'status': latest_payment.status,
            'status_display': latest_payment.get_status_display(),
            'paid_at': latest_payment.paid_at,
            'amount': float(latest_payment.amount),
            'appointment_status': appointment.status
        })
    
    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def payment_callback(self, request, pk=None):
        """Callback для возврата из ЮKassa после оплаты"""
        appointment = self.get_object()
    
        latest_payment = Payment.objects.filter(
            appointment=appointment
        ).order_by('-created_at').first()
    
        if latest_payment:
            from payments.services import check_payment_status
            check_payment_status(latest_payment)
        
            return Response({
                'success': latest_payment.status == 'succeeded',
                'status': latest_payment.status,
                'appointment_id': str(appointment.id)
            })
    
        return Response({
            'success': False,
            'status': 'not_found'
        }, status=status.HTTP_404_NOT_FOUND)

class ProfileViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'update':
            return UserUpdateSerializer
        elif self.action == 'upload_avatar':
            return AvatarUploadSerializer
        elif self.action == 'stats':
            return ProfileStatsSerializer
        elif self.action == 'loyalty':
            return LoyaltyAccountSerializer
        return UserSerializer
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Получить данные текущего пользователя"""
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Обновить профиль"""
        serializer = UserUpdateSerializer(
            request.user, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            user = serializer.update(request.user, serializer.validated_data)
            return Response({
                'success': True,
                'message': 'Профиль обновлен',
                'data': UserSerializer(user, context={'request': request}).data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_avatar(self, request):
        """Загрузить аватар"""
        serializer = AvatarUploadSerializer(data=request.data)
        
        if serializer.is_valid():
            profile = serializer.save(request.user)
            return Response({
                'success': True,
                'message': 'Аватар обновлен',
                'avatar_url': profile.avatar.url if profile.avatar else None
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['delete'])
    def delete_avatar(self, request):
        """Удалить аватар"""
        profile = request.user.userprofile
        if profile.avatar:
            profile.avatar.delete(save=False)
            profile.avatar = None
            profile.save()
        
        return Response({
            'success': True,
            'message': 'Аватар удален'
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Получить статистику пользователя"""
        user = request.user
        appointments = Appointment.objects.filter(car__owner=user)
        
        total = appointments.count()
        completed = appointments.filter(status='COMPLETED').count()
        cancelled = appointments.filter(status='CANCELLED').count()
        total_spent = sum(a.get_final_price() for a in appointments.filter(status='COMPLETED'))
        average_check = total_spent / completed if completed > 0 else 0
        
        first = appointments.order_by('scheduled_date').first()
        last = appointments.filter(status='COMPLETED').order_by('-scheduled_date').first()
        
        today = timezone.now().date()
        visits_by_month = {}
        for i in range(11, -1, -1):
            month_date = today - timedelta(days=30 * i)
            month_key = f"{month_date.year}-{month_date.month:02d}"
            visits_by_month[month_key] = 0
        
        for app in appointments:
            month_key = f"{app.scheduled_date.year}-{app.scheduled_date.month:02d}"
            if month_key in visits_by_month:
                visits_by_month[month_key] += 1
        
        top_services = list(
            appointments.values('service_type__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
            .values_list('service_type__name', 'count')
        )
        
        top_centers = list(
            appointments.values('service_center__address')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
            .values_list('service_center__address', 'count')
        )
        
        weekday_counts = [0] * 7
        for app in appointments:
            wd = app.scheduled_date.weekday()
            weekday_counts[wd] += 1
        
        hour_counts = [0] * 24
        for app in appointments:
            hour_counts[app.scheduled_time.hour] += 1
        
        return Response({
            'total_appointments': total,
            'completed_appointments': completed,
            'cancelled_appointments': cancelled,
            'total_spent': float(total_spent),
            'average_check': float(average_check),
            'first_visit': first.scheduled_date if first else None,
            'last_visit': last.scheduled_date if last else None,
            'visits_by_month': visits_by_month,
            'top_services': [{'name': name, 'count': count} for name, count in top_services],
            'top_centers': [{'name': name, 'count': count} for name, count in top_centers],
            'by_weekday': weekday_counts,
            'by_hour': hour_counts
        })
    
    @action(detail=False, methods=['get'])
    def loyalty(self, request):
        """Получить информацию о программе лояльности"""
        from loyalty_program.models import LoyaltyAccount, LoyaltySettings

        account, _ = LoyaltyAccount.objects.get_or_create(user=request.user)
        settings = LoyaltySettings.get_settings()

        status_order = ['NONE', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM']

        current_idx = status_order.index(account.status) if account.status in status_order else 0
        next_status = status_order[current_idx + 1] if current_idx < len(status_order) - 1 else None

        progress = 100
        if next_status:
            thresholds = {
                'BRONZE': settings.bronze_threshold if hasattr(settings, 'bronze_threshold') else 0,
                'SILVER': settings.silver_threshold if hasattr(settings, 'silver_threshold') else 10000,
                'GOLD': settings.gold_threshold if hasattr(settings, 'gold_threshold') else 50000,
                'PLATINUM': settings.platinum_threshold if hasattr(settings, 'platinum_threshold') else 100000
            }
            threshold = thresholds.get(next_status, 0)
            if threshold > 0:
                progress = min((account.total_spent / threshold) * 100, 100)

        status_discounts = {
            'NONE': 0,
            'BRONZE': settings.bronze_discount_percent if hasattr(settings, 'bronze_discount_percent') else 0,
            'SILVER': settings.silver_discount_percent if hasattr(settings, 'silver_discount_percent') else 3,
            'GOLD': settings.gold_discount_percent if hasattr(settings, 'gold_discount_percent') else 5,
            'PLATINUM': settings.platinum_discount_percent if hasattr(settings, 'platinum_discount_percent') else 7
        }

        status_discount = status_discounts.get(account.status, 0)

        return Response({
            'status': account.status,
            'status_display': account.get_status_display() if account.status != 'NONE' else 'Новый',
            'bonus_balance': float(account.bonus_balance),
            'total_spent': float(account.total_spent),
            'next_status': next_status,
            'next_status_progress': round(progress, 1),
            'personal_discount': float(account.personal_discount_percent),
            'status_discount': float(status_discount),
            'total_discount': float(account.personal_discount_percent + status_discount)
        })

class AdminAppointmentViewSet(viewsets.ModelViewSet):
    """API для управления записями (админ)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = AdminAppointmentSerializer
    queryset = Appointment.objects.all().select_related(
        'car__model__brand', 'car__owner__userprofile',
        'service_type', 'service_center'
    ).order_by('-scheduled_date', 'scheduled_time')
    
    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        """Добавить комментарий админа"""
        appointment = self.get_object()
        note = request.data.get('note', '').strip()
        
        if note:
            prefix = "admin: "
            appointment.notes = (appointment.notes + "\n" if appointment.notes else "") + prefix + note
            appointment.save(update_fields=['notes', 'updated_at'])
        
        return Response({
            'success': True,
            'notes': appointment.notes
        })

    def get_queryset(self):
        queryset = super().get_queryset()
        
        center_id = self.request.query_params.get('center_id')
        if center_id:
            queryset = queryset.filter(service_center_id=center_id)
        
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(scheduled_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(scheduled_date__lte=date_to)
        
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        search = self.request.query_params.get('search')
        if search:
            search_terms = search.split()
            
            search_filter = Q()
            for term in search_terms:
                search_filter |= (
                    Q(car__owner__first_name__icontains=term) |
                    Q(car__owner__last_name__icontains=term) |
                    Q(car__owner__username__icontains=term) |
                    Q(car__license_plate__icontains=term) |
                    Q(car__model__name__icontains=term) |
                    Q(car__model__brand__name__icontains=term)
                )
            
            queryset = queryset.filter(search_filter)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Изменить статус записи"""
        appointment = self.get_object()
        serializer = ChangeStatusSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        
        new_status = serializer.validated_data['status']
        old_status = appointment.status
        
        appointment.status = new_status
        appointment.save(update_fields=['status', 'updated_at'])
        
        if new_status == 'COMPLETED' and appointment.paid_amount is None:
            appointment.paid_amount = appointment.get_base_price()
            appointment.save(update_fields=['paid_amount'])
        
        return Response({
            'success': True,
            'status': appointment.status,
            'status_display': appointment.get_status_display()
        })
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Записи на сегодня"""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(scheduled_date=today).order_by('scheduled_time')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """Записи для календаря (по дням)"""
        month = request.query_params.get('month')
        center_id = request.query_params.get('center_id')
        
        if not month:
            return Response({'error': 'Параметр month обязателен (YYYY-MM)'}, status=400)
        
        queryset = Appointment.objects.all()
        if center_id:
            queryset = queryset.filter(service_center_id=center_id)
        
        queryset = queryset.filter(scheduled_date__startswith=month)
        
        days = {}
        for app in queryset:
            date_key = app.scheduled_date.strftime('%Y-%m-%d')
            if date_key not in days:
                days[date_key] = {
                    'total': 0,
                    'completed': 0,
                    'scheduled': 0,
                }
            days[date_key]['total'] += 1
            if app.status == 'COMPLETED':
                days[date_key]['completed'] += 1
            elif app.status == 'SCHEDULED':
                days[date_key]['scheduled'] += 1
        
        return Response(days)


class AdminStatsViewSet(viewsets.GenericViewSet):
    """API для статистики (админ)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def center_visits(self, request):
        """Посещаемость по дням для конкретного филиала"""
        center_id = request.query_params.get('center_id')
        period = request.query_params.get('period', 'week')
        
        if not center_id:
            return Response({'error': 'center_id обязателен'}, status=400)
        
        today = timezone.now().date()
        
        if period == 'week':
            start_date = today - timedelta(days=6)
        elif period == 'month':
            start_date = today - timedelta(days=29)
        else:
            start_date = today - timedelta(days=6)
        
        appointments = Appointment.objects.filter(
            service_center_id=center_id,
            scheduled_date__gte=start_date,
            scheduled_date__lte=today
        )
        
        visits_by_date = {}
        current = start_date
        while current <= today:
            visits_by_date[current.strftime('%Y-%m-%d')] = 0
            current += timedelta(days=1)
        
        for app in appointments:
            date_key = app.scheduled_date.strftime('%Y-%m-%d')
            if date_key in visits_by_date:
                visits_by_date[date_key] += 1
        
        labels = []
        data = []
        for date_str, count in visits_by_date.items():
            labels.append(datetime.strptime(date_str, '%Y-%m-%d').strftime('%d.%m'))
            data.append(count)
        
        return Response({
            'center_id': center_id,
            'period': period,
            'labels': labels,
            'data': data
        })

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Основной дашборд"""
        center_id = request.query_params.get('center_id')
        
        appointments = Appointment.objects.all()
        if center_id:
            appointments = appointments.filter(service_center_id=center_id)
        
        today = timezone.now().date()
        today_appointments = appointments.filter(scheduled_date=today)
        
        from payments.models import Payment
        completed = appointments.filter(status='COMPLETED')
        revenue = completed.aggregate(
            total=Sum('paid_amount')
        )['total'] or 0
        
        return Response({
            'today_appointments': today_appointments.count(),
            'today_completed': today_appointments.filter(status='COMPLETED').count(),
            'today_in_progress': today_appointments.filter(status='IN_PROGRESS').count(),
            'today_scheduled': today_appointments.filter(status='SCHEDULED').count(),
            'today_revenue': float(revenue),
            'pending_count': appointments.filter(status='SCHEDULED').count(),
            'in_progress_count': appointments.filter(status='IN_PROGRESS').count(),
            'total_clients': User.objects.filter(car__appointment__isnull=False).distinct().count(),
            'average_rating': Review.objects.filter(
                service_center_id=center_id if center_id else None
            ).aggregate(avg=Avg('rating'))['avg'] or 0,
        })
    
    @action(detail=False, methods=['get'])
    def statuses(self, request):
        period = request.query_params.get('period', 'week')
        center_id = request.query_params.get('center_id')
        
        today = timezone.now().date()
        if period == 'week':
            start_date = today - timedelta(days=6)
        elif period == 'month':
            start_date = today - timedelta(days=29)
        else:
            start_date = None
        
        queryset = Appointment.objects.all()
        if center_id:
            queryset = queryset.filter(service_center_id=center_id)
        if start_date:
            queryset = queryset.filter(scheduled_date__gte=start_date, scheduled_date__lte=today)
        
        status_counts = {}
        for code, label in Appointment.STATUS_CHOICES:
            count = queryset.filter(status=code).count()
            status_counts[code] = {'label': label, 'count': count}
        
        return Response({
            'period': period,
            'statuses': status_counts,
            'total': queryset.count()
        })

    @action(detail=False, methods=['get'])
    def attendance(self, request):
        period = request.query_params.get('period', 'week')
        today = timezone.now().date()
        
        if period == 'week':
            start_date = today - timedelta(days=6)
        elif period == 'month':
            start_date = today - timedelta(days=29)
        else:
            start_date = None
        
        centers = ServiceCenter.objects.all()
        result = []
        for center in centers:
            queryset = Appointment.objects.filter(service_center=center)
            if start_date:
                queryset = queryset.filter(scheduled_date__gte=start_date, scheduled_date__lte=today)
            result.append({
                'id': str(center.id),
                'address': center.address,
                'count': queryset.count()
            })
        
        result.sort(key=lambda x: x['count'], reverse=True)
        return Response({'period': period, 'centers': result})

    @action(detail=False, methods=['get'])
    def service_popularity(self, request):
        period = request.query_params.get('period', 'month')
        center_id = request.query_params.get('center_id')
        today = timezone.now().date()
        
        if period == 'week':
            start_date = today - timedelta(days=6)
        elif period == 'month':
            start_date = today - timedelta(days=29)
        else:
            start_date = None
        
        queryset = Appointment.objects.all()
        if center_id:
            queryset = queryset.filter(service_center_id=center_id)
        if start_date:
            queryset = queryset.filter(scheduled_date__gte=start_date, scheduled_date__lte=today)
        
        services = queryset.values('service_type__name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        total = sum(s['count'] for s in services)
        result = []
        for s in services:
            result.append({
                'name': s['service_type__name'],
                'count': s['count'],
                'percentage': round(s['count'] / total * 100, 1) if total > 0 else 0
            })
        
        return Response({'period': period, 'services': result})

    @action(detail=False, methods=['get'])
    def revenue(self, request):
        """Статистика по выручке"""
        days = request.query_params.get('days', '7')
        center_id = request.query_params.get('center_id')
        
        try:
            days = int(days)
        except ValueError:
            days = 7
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        appointments = Appointment.objects.filter(
            scheduled_date__gte=start_date,
            status='COMPLETED'
        )
        if center_id:
            appointments = appointments.filter(service_center_id=center_id)
        
        daily_revenue = {}
        for i in range(days):
            date = start_date + timedelta(days=i)
            daily_revenue[date.strftime('%Y-%m-%d')] = 0
        
        for app in appointments:
            date_key = app.scheduled_date.strftime('%Y-%m-%d')
            if date_key in daily_revenue:
                daily_revenue[date_key] += float(app.get_final_price())
        
        return Response({
            'labels': list(daily_revenue.keys()),
            'values': list(daily_revenue.values()),
            'total': sum(daily_revenue.values())
        })
    
    @action(detail=False, methods=['get'])
    def top_services(self, request):
        """Топ услуг"""
        center_id = request.query_params.get('center_id')
        
        queryset = Appointment.objects.all()
        if center_id:
            queryset = queryset.filter(service_center_id=center_id)
        
        top = queryset.values('service_type__name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return Response([
            {'name': item['service_type__name'], 'count': item['count']}
            for item in top
        ])


class AdminReviewViewSet(viewsets.ModelViewSet):
    """API для управления отзывами (админ)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = AdminReviewSerializer
    queryset = Review.objects.all().select_related('user__userprofile', 'service_center').order_by('-created_at')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        center_id = self.request.query_params.get('center_id')
        if center_id:
            queryset = queryset.filter(service_center_id=center_id)
        
        rating = self.request.query_params.get('rating')
        if rating:
            try:
                queryset = queryset.filter(rating=int(rating))
            except ValueError:
                pass
        
        unanswered = self.request.query_params.get('unanswered')
        if unanswered == 'true':
            queryset = queryset.filter(admin_reply__isnull=True)
        elif unanswered == 'false':
            queryset = queryset.exclude(admin_reply__isnull=True)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__username__icontains=search) |
                Q(comment__icontains=search)
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """Ответить на отзыв"""
        review = self.get_object()
        reply_text = request.data.get('reply', '').strip()
        
        review.admin_reply = reply_text if reply_text else None
        review.admin_reply_at = timezone.now() if reply_text else None
        review.save(update_fields=['admin_reply', 'admin_reply_at', 'updated_at'])
        
        return Response({
            'success': True,
            'admin_reply': review.admin_reply,
            'admin_reply_at': review.admin_reply_at
        })
    
    def destroy(self, request, *args, **kwargs):
        """Удалить отзыв"""
        review = self.get_object()
        review.delete()
        return Response({'success': True, 'message': 'Отзыв удален'})


class AdminSlotViewSet(viewsets.GenericViewSet):
    """API для управления слотами (админ)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @action(detail=False, methods=['post'])
    def block(self, request):
        """Заблокировать слот"""
        serializer = BlockSlotSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        
        data = serializer.validated_data
        
        BlockedTimeSlot.objects.get_or_create(
            service_center_id=data['center_id'],
            date=data['date'],
            time=data['time'],
            defaults={
                'blocked_by': request.user,
                'reason': data.get('reason', '')
            }
        )
        
        return Response({'success': True, 'message': 'Слот заблокирован'})
    
    @action(detail=False, methods=['post'])
    def unblock(self, request):
        """Разблокировать слот"""
        center_id = request.data.get('center_id')
        date = request.data.get('date')
        time = request.data.get('time')
        
        deleted, _ = BlockedTimeSlot.objects.filter(
            service_center_id=center_id,
            date=date,
            time=time
        ).delete()
        
        if deleted:
            return Response({'success': True, 'message': 'Слот разблокирован'})
        
        return Response({'error': 'Слот не найден'}, status=404)
    
    @action(detail=False, methods=['get'])
    def blocked(self, request):
        """Список заблокированных слотов"""
        center_id = request.query_params.get('center_id')
        date = request.query_params.get('date')
        
        queryset = BlockedTimeSlot.objects.all()
        if center_id:
            queryset = queryset.filter(service_center_id=center_id)
        if date:
            queryset = queryset.filter(date=date)
        
        data = [{
            'id': str(slot.id),
            'date': slot.date,
            'time': slot.time.strftime('%H:%M'),
            'reason': slot.reason,
            'blocked_at': slot.blocked_at
        } for slot in queryset.order_by('date', 'time')]
        
        return Response(data)


class AdminClientViewSet(viewsets.ReadOnlyModelViewSet):
    """API для просмотра клиентов (админ)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = AdminClientListSerializer

    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_user(self, request, pk=None):
        """Удалить пользователя"""
        user = get_object_or_404(User, id=pk)
        username = user.username
        user.delete()
        return Response({'success': True, 'message': f'Пользователь {username} удалён'})

    @action(detail=True, methods=['put'], url_path='update')
    def update_user(self, request, pk=None):
        """Редактировать пользователя"""
        user = get_object_or_404(User, id=pk)
        
        username = request.data.get('username', user.username)
        first_name = request.data.get('first_name', user.first_name)
        last_name = request.data.get('last_name', user.last_name)
        email = request.data.get('email', user.email)
        phone = request.data.get('phone')
        address = request.data.get('address')
        is_staff = request.data.get('is_staff', user.is_staff)
        
        if username != user.username and User.objects.filter(username=username).exists():
            return Response({'errors': {'username': 'Логин уже занят'}}, status=400)
        if email != user.email and User.objects.filter(email=email).exists():
            return Response({'errors': {'email': 'Email уже занят'}}, status=400)
        
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.is_staff = is_staff
        user.save()
        
        profile = user.userprofile
        if phone is not None:
            profile.phone = phone
        if address is not None:
            profile.address = address
        profile.save()
    
        return Response({'success': True})

    @action(detail=False, methods=['post'])
    def create_user(self, request):
        """Создать нового пользователя"""
        username = request.data.get('username')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        email = request.data.get('email', '')
        password = request.data.get('password')
        password_confirm = request.data.get('password_confirm')
        phone = request.data.get('phone', '')
        address = request.data.get('address', '')
        is_staff = request.data.get('is_staff', False)
        
        errors = {}
        if password != password_confirm:
            errors['password_confirm'] = 'Пароли не совпадают'
        if not username:
            errors['username'] = 'Обязательное поле'
        elif User.objects.filter(username=username).exists():
            errors['username'] = 'Пользователь с таким логином уже существует'
        
        if not password or len(password) < 8:
            errors['password'] = 'Минимум 8 символов'
        
        if email and User.objects.filter(email=email).exists():
            errors['email'] = 'Email уже используется'
        
        if errors:
            return Response({'errors': errors}, status=400)
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff
        )
        
        from core.models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.phone = phone
        profile.address = address
        profile.save()
        
        return Response({
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
            'phone': phone,
            'address': address,
            'is_staff': user.is_staff,
            'cars_count': 0,
            'appointments_count': 0,
            'active_appointments_count': 0,
            'date_joined': timezone.localtime(user.date_joined).strftime('%d.%m.%Y %H:%M'),
        }, status=201)

    def get_queryset(self):
        queryset = User.objects.all().order_by('last_name')
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        email = self.request.query_params.get('email')
        if email:
            queryset = queryset.filter(email__icontains=email)
        
        phone = self.request.query_params.get('phone')
        if phone:
            queryset = queryset.filter(userprofile__phone__icontains=phone)
        
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(date_joined__date__gte=date_from)
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(date_joined__date__lte=date_to)
        
        has_cars = self.request.query_params.get('has_cars')
        if has_cars == 'true':
            queryset = queryset.filter(car__isnull=False).distinct()
        
        has_active = self.request.query_params.get('has_active')
        if has_active == 'true':
            queryset = queryset.filter(
                car__appointment__status__in=['SCHEDULED', 'IN_PROGRESS']
            ).distinct()
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def info(self, request, pk=None):
        user = get_object_or_404(User, id=pk)
        
        cars = Car.objects.filter(owner=user)
        appointments = Appointment.objects.filter(car__owner=user).order_by('-scheduled_date')
        
        total_appointments = appointments.count()
        completed = appointments.filter(status='COMPLETED')
        
        top_services = list(
            appointments.values('service_type__name')
            .annotate(count=Count('id')).order_by('-count')[:5]
        )
        
        top_centers = list(
            appointments.values('service_center__address')
            .annotate(count=Count('id')).order_by('-count')[:5]
        )
        
        weekday_counts = [0] * 7
        for app in appointments:
            weekday_counts[app.scheduled_date.weekday()] += 1
        
        hour_counts = [0] * 24
        for app in appointments:
            hour_counts[app.scheduled_time.hour] += 1
        
        from loyalty_program.models import LoyaltyAccount

        account, _ = LoyaltyAccount.objects.get_or_create(user=user)
        total_paid = account.total_spent
        
        return Response({
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
            'phone': user.userprofile.phone if hasattr(user, 'userprofile') else None,
            'address': user.userprofile.address if hasattr(user, 'userprofile') else None,
            'date_joined': user.date_joined.strftime('%d.%m.%Y %H:%M'),
            'is_staff': user.is_staff,
            'cars_count': cars.count(),
            'appointments_count': total_appointments,
            'total_paid': float(total_paid),
            'cars': [{
                'id': str(car.id),
                'name': f"{car.model.brand.name} {car.model.name}",
                'license_plate': car.license_plate,
                'year': car.year
            } for car in cars],
            'recent_appointments': AdminAppointmentSerializer(appointments[:5], many=True).data,
            'top_services': [{'name': s['service_type__name'], 'count': s['count']} for s in top_services],
            'top_centers': [{'name': s['service_center__address'], 'count': s['count']} for s in top_centers],
            'weekday_counts': weekday_counts,
            'hour_counts': hour_counts,
            'date_joined': timezone.localtime(user.date_joined).strftime('%d.%m.%Y %H:%M'),
        })

class AdminServiceTypeViewSet(viewsets.ModelViewSet):
    """API для управления услугами (админ)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = AdminServiceTypeSerializer

    @action(detail=False, methods=['get'])
    def unique(self, request):
        """Уникальные названия услуг (без привязки к филиалам)"""
        services = ServiceType.objects.filter(is_active=True).values('name').distinct().order_by('name')
        return Response([s['name'] for s in services])

    def get_queryset(self):
        queryset = ServiceType.objects.select_related('service_center').order_by('name')

        center_id = self.request.query_params.get('center_id')
        if center_id:
            queryset = queryset.filter(service_center_id=center_id)

        active_only = self.request.query_params.get('active_only')
        if active_only == 'true':
            queryset = queryset.filter(is_active=True)

        return queryset

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Включить/выключить услугу"""
        service = self.get_object()
        service.is_active = not service.is_active
        service.save(update_fields=['is_active', 'updated_at'] if hasattr(service, 'updated_at') else ['is_active'])

        return Response({
            'success': True,
            'is_active': service.is_active,
            'message': 'Услуга активирована' if service.is_active else 'Услуга деактивирована'
        })

    @action(detail=False, methods=['post'])
    def bulk_update_prices(self, request):
        """Массовое обновление цен (процент или фиксированная сумма)"""
        center_id = request.data.get('center_id')
        change_type = request.data.get('type', 'percent')
        value = request.data.get('value', 0)

        try:
            value = float(value)
        except (TypeError, ValueError):
            return Response({'error': 'Неверное значение'}, status=400)

        services = ServiceType.objects.all()
        if center_id:
            services = services.filter(service_center_id=center_id)

        updated = 0
        for service in services:
            if change_type == 'percent':
                service.price = service.price * (1 + value / 100)
            else:
                service.price = max(0, service.price + value)
            service.save(update_fields=['price'])
            updated += 1

        return Response({
            'success': True,
            'updated_count': updated,
            'message': f'Обновлено {updated} услуг'
        })


class AdminServiceCenterViewSet(viewsets.ModelViewSet):
    """API для управления филиалами (админ)"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = AdminServiceCenterSerializer

    def get_queryset(self):
        if self.action in ['retrieve', 'update', 'partial_update']:
            return ServiceCenter.objects.prefetch_related('working_hours', 'services')
        return ServiceCenter.objects.all().order_by('address')

    @action(detail=True, methods=['get'])
    def working_hours(self, request, pk=None):
        """Получить все рабочие часы филиала"""
        center = self.get_object()
        wh = center.working_hours.all().order_by('day_of_week')
        serializer = AdminWorkingHoursSerializer(wh, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def set_working_hours(self, request, pk=None):
        """Установить рабочие часы для дня"""
        center = self.get_object()
        serializer = AdminWorkingHoursSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)

        data = serializer.validated_data
        day = data['day_of_week']

        wh, created = WorkingHours.objects.update_or_create(
            service_center=center,
            day_of_week=day,
            defaults={
                'start_time': data['start_time'],
                'end_time': data['end_time'],
                'lunch_start': data.get('lunch_start'),
                'lunch_end': data.get('lunch_end'),
                'is_working': data.get('is_working', True)
            }
        )

        return Response({
            'success': True,
            'message': 'Рабочие часы обновлены',
            'data': AdminWorkingHoursSerializer(wh).data
        })

    @action(detail=True, methods=['post'])
    def update_photo(self, request, pk=None):
        """Обновить фото филиала"""
        center = self.get_object()

        if 'photo' not in request.FILES:
            return Response({'error': 'Файл photo обязателен'}, status=400)

        center.photo = request.FILES['photo']
        center.save()

        return Response({
            'success': True,
            'photo_url': center.get_photo_url()
        })


class AdminEmployeeViewSet(viewsets.ModelViewSet):
    """API для управления сотрудниками (админ)"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminCreateEmployeeSerializer
        return AdminEmployeeSerializer

    def get_queryset(self):
        return Employee.objects.select_related('user').order_by('user__last_name')

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def update_salary(self, request, pk=None):
        """Обновить зарплату сотрудника"""
        employee = self.get_object()
        new_salary = request.data.get('salary')

        try:
            new_salary = float(new_salary)
            if new_salary < 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response({'error': 'Неверная сумма зарплаты'}, status=400)

        employee.salary = new_salary
        employee.save(update_fields=['salary'])

        return Response({
            'success': True,
            'salary': float(employee.salary)
        })

    @action(detail=True, methods=['post'])
    def change_position(self, request, pk=None):
        """Изменить должность сотрудника"""
        employee = self.get_object()
        new_position = request.data.get('position')

        if new_position not in ['MECH', 'MAN', 'DIR']:
            return Response({'error': 'Неверная должность'}, status=400)

        employee.position = new_position
        employee.save(update_fields=['position'])

        return Response({
            'success': True,
            'position': employee.position,
            'position_display': employee.get_position_display()
        })


class AdminDashboardViewSet(viewsets.GenericViewSet):
    """Расширенный дашборд для админа"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @action(detail=False, methods=['get'])
    def full(self, request):
        """Полный дашборд — всё в одном запросе"""
        center_id = request.query_params.get('center_id')
        today = timezone.now().date()
        now_time = timezone.now().time()

        appointments = Appointment.objects.all()
        if center_id:
            appointments = appointments.filter(service_center_id=center_id)

        today_qs = appointments.filter(scheduled_date=today)

        today_data = {
            'total': today_qs.count(),
            'scheduled': today_qs.filter(status='SCHEDULED').count(),
            'in_progress': today_qs.filter(status='IN_PROGRESS').count(),
            'completed': today_qs.filter(status='COMPLETED').count(),
            'cancelled': today_qs.filter(status='CANCELLED').count(),
        }

        upcoming_qs = appointments.filter(
            status__in=['SCHEDULED', 'IN_PROGRESS'],
            scheduled_date__gte=today
        ).exclude(
            scheduled_date=today,
            scheduled_time__lt=now_time
        ).select_related(
            'car__owner', 'service_type', 'service_center'
        ).order_by('scheduled_date', 'scheduled_time')[:10]

        upcoming_data = []
        for app in upcoming_qs:
            upcoming_data.append({
                'id': str(app.id),
                'date': app.scheduled_date.strftime('%d.%m.%Y'),
                'time': app.scheduled_time.strftime('%H:%M'),
                'client': app.car.owner.get_full_name() or app.car.owner.username,
                'service': app.service_type.name,
                'car': str(app.car),
                'center': app.service_center.address if app.service_center else '',
                'status': app.status,
                'status_display': app.get_status_display(),
            })

        pending_qs = appointments.filter(status='SCHEDULED').order_by('scheduled_date', 'scheduled_time')
        pending_total = pending_qs.count()
        pending_today = pending_qs.filter(scheduled_date=today).count()
        pending_week = pending_qs.filter(
            scheduled_date__gte=today,
            scheduled_date__lte=today + timedelta(days=7)
        ).count()

        pending_data = {
            'total': pending_total,
            'today': pending_today,
            'this_week': pending_week,
        }

        from payments.models import Payment

        today_revenue = today_qs.filter(status='COMPLETED').aggregate(
            total=Sum('paid_amount')
        )['total'] or 0

        week_qs = appointments.filter(
            scheduled_date__gte=today - timedelta(days=7),
            scheduled_date__lte=today,
            status='COMPLETED'
        )
        week_revenue = week_qs.aggregate(total=Sum('paid_amount'))['total'] or 0

        month_start = today.replace(day=1)
        month_qs = appointments.filter(
            scheduled_date__gte=month_start,
            scheduled_date__lte=today,
            status='COMPLETED'
        )
        month_revenue = month_qs.aggregate(total=Sum('paid_amount'))['total'] or 0

        revenue_data = {
            'today': float(today_revenue),
            'week': float(week_revenue),
            'month': float(month_revenue),
        }

        chart_labels = []
        chart_appointments = []
        chart_revenue = []

        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            chart_labels.append(d.strftime('%d.%m'))
            day_qs = appointments.filter(scheduled_date=d)
            chart_appointments.append(day_qs.count())
            day_revenue = day_qs.filter(status='COMPLETED').aggregate(
                total=Sum('paid_amount')
            )['total'] or 0
            chart_revenue.append(float(day_revenue))

        chart_data = {
            'labels': chart_labels,
            'appointments': chart_appointments,
            'revenue': chart_revenue,
        }

        if center_id:
            centers_data = []
        else:
            centers_data = []
            all_centers = ServiceCenter.objects.all()
            for center in all_centers:
                center_qs = appointments.filter(service_center=center)
                center_today = center_qs.filter(scheduled_date=today)
                centers_data.append({
                    'id': str(center.id),
                    'address': center.address,
                    'today_total': center_today.count(),
                    'today_completed': center_today.filter(status='COMPLETED').count(),
                    'pending': center_qs.filter(status='SCHEDULED').count(),
                })

        reviews_pending = Review.objects.filter(admin_reply__isnull=True)
        if center_id:
            reviews_pending = reviews_pending.filter(service_center_id=center_id)

        return Response({
            'total_appointments': appointments.count(),
            'active_services': ServiceType.objects.filter(is_active=True).values('name').distinct().count(),
            'total_clients': User.objects.filter(car__appointment__isnull=False).distinct().count(),
            'total_centers': ServiceCenter.objects.count(),

            'today': today_data,
            'pending': pending_data,
            'revenue': revenue_data,
            'upcoming': upcoming_data,
            'chart': chart_data,
            'centers': centers_data,
            'reviews_pending': reviews_pending.count(),
        })

    @action(detail=False, methods=['get'])
    def export_appointments(self, request):
        """Экспорт записей в CSV"""
        import csv
        from django.http import HttpResponse
        from io import StringIO

        center_id = request.query_params.get('center_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        queryset = Appointment.objects.select_related(
            'car__model__brand', 'car__owner', 'service_type', 'service_center'
        ).order_by('-scheduled_date', 'scheduled_time')

        if center_id:
            queryset = queryset.filter(service_center_id=center_id)
        if date_from:
            queryset = queryset.filter(scheduled_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(scheduled_date__lte=date_to)

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'ID', 'Дата', 'Время', 'Клиент', 'Телефон',
            'Автомобиль', 'Гос.номер', 'Услуга', 'Филиал',
            'Статус', 'Сумма', 'Оплачено онлайн'
        ])

        for app in queryset:
            writer.writerow([
                str(app.id),
                app.scheduled_date,
                app.scheduled_time,
                app.car.owner.get_full_name() or app.car.owner.username,
                app.car.owner.userprofile.phone if hasattr(app.car.owner, 'userprofile') else '',
                f"{app.car.model.brand.name} {app.car.model.name}",
                app.car.license_plate,
                app.service_type.name,
                app.service_center.address if app.service_center else '',
                app.get_status_display(),
                float(app.get_final_price()),
                'Да' if Payment.objects.filter(appointment=app, status='succeeded').exists() else 'Нет'
            ])

        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="appointments.csv"'
        response.write('\ufeff')
        return response
    