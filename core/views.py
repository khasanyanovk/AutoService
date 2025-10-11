from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.utils import timezone
import json
from .models import (
    CarModel,
    UserProfile,
    Car,
    ServiceType,
    Appointment,
    WorkingHours,
    ServiceCenter,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import (
    UserRegisterForm,
    AppointmentForm,
    UserUpdateForm,
    ProfileUpdateForm,
    CarForm,
)
from django.http import JsonResponse
from datetime import datetime, date, timedelta, time


def home(request):
    return render(request, "core/index.html")


def about(request):
    return render(request, "core/about.html")


def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = UserRegisterForm()
    return render(request, "core/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")
    else:
        form = AuthenticationForm()
    return render(request, "core/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def profile(request):
    user_profile = UserProfile.objects.get(user=request.user)
    user_cars = Car.objects.filter(owner=request.user)

    context = {
        "profile": user_profile,
        "cars": user_cars,
    }
    return render(request, "core/profile.html", context)


@login_required
def profile_edit(request):
    if request.method == "POST":
        if "delete_avatar" in request.POST:
            profile = UserProfile.objects.get(user=request.user)
            if profile.avatar:
                profile.avatar.delete(save=False)
                profile.avatar = None
                profile.save()
            return redirect("profile_edit")
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(
            request.POST, request.FILES, instance=request.user.userprofile
        )

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "Ваш профиль успешно обновлен!")
            return redirect("profile")
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.userprofile)

    context = {"u_form": u_form, "p_form": p_form}

    return render(request, "core/profile_edit.html", context)


@login_required
def add_car(request):
    if request.method == "POST":
        form = CarForm(request.POST)
        if form.is_valid():
            try:
                form.save(request.user)
                messages.success(request, "Автомобиль успешно добавлен!")
                return redirect("profile")

            except IntegrityError:
                messages.error(
                    request, "Автомобиль с таким гос. номером или VIN уже существует."
                )
            except Exception as e:
                messages.error(request, f"Ошибка при добавлении автомобиля: {str(e)}")
    else:
        form = CarForm()

    return render(request, "core/add_car.html", {"form": form})


@login_required
def edit_car(request, car_id):
    car = get_object_or_404(Car, id=car_id, owner=request.user)

    if request.method == "POST":
        form = CarForm(request.POST)
        if form.is_valid():
            try:
                car.year = form.cleaned_data["year"]
                car.model = form.cleaned_data["model"]
                car.license_plate = form.cleaned_data["license_plate"]
                car.vin = form.cleaned_data.get("vin")
                car.save()

                messages.success(request, "Информация об автомобиле обновлена!")
                return redirect("profile")

            except IntegrityError:
                messages.error(
                    request, "Автомобиль с таким гос. номером или VIN уже существует."
                )
            except Exception as e:
                messages.error(request, f"Ошибка при обновлении автомобиля: {str(e)}")
    else:
        initial_data = {
            "brand": car.model.brand if car.model else None,
            "model": car.model,
            "year": car.year,
            "license_plate": car.license_plate,
            "vin": car.vin,
        }
        form = CarForm(initial=initial_data)

    return render(request, "core/edit_car.html", {"form": form, "car": car})


@login_required
def delete_car(request, car_id):
    car = get_object_or_404(Car, id=car_id, owner=request.user)

    if request.method == "POST":
        car.delete()
        messages.success(request, "Автомобиль удален!")
        return redirect("profile")

    return render(request, "core/delete_car.html", {"car": car})


def load_models(request):
    brand_id = request.GET.get("brand_id")
    if brand_id:
        try:
            models = CarModel.objects.filter(brand_id=brand_id).order_by("name")
            options = '<option value="">Выберите модель</option>'
            for model in models:
                options += f'<option value="{model.id}">{model.name}</option>'
            return JsonResponse({"options": options})
        except Exception:
            return JsonResponse(
                {"options": '<option value="">Ошибка загрузки</option>'}
            )
    else:
        return JsonResponse(
            {"options": '<option value="">Сначала выберите марку</option>'}
        )


@login_required
def service_booking(request):
    """Страница записи на услугу"""
    if request.method == "POST":
        form = AppointmentForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                car = form.cleaned_data["car"]
                service_center = form.cleaned_data["service_center"]
                service_type = form.cleaned_data["service_type"]
                scheduled_date = form.cleaned_data["scheduled_date"]
                scheduled_time_str = form.cleaned_data["scheduled_time"]
                notes = form.cleaned_data["notes"]

                scheduled_time = datetime.strptime(scheduled_time_str, "%H:%M").time()

                appointment = Appointment(
                    car=car,
                    service_center=service_center,
                    service_type=service_type,
                    scheduled_date=scheduled_date,
                    scheduled_time=scheduled_time,
                    notes=notes,
                )
                appointment.save()

                messages.success(
                    request,
                    f'Запись на услугу "{appointment.service_type}" успешно создана в {appointment.service_center} на {appointment.scheduled_date} в {appointment.scheduled_time}',
                )
                return redirect("appointment_list")

            except Exception as e:
                messages.error(request, f"Ошибка при создании записи: {str(e)}")
    else:
        form = AppointmentForm(user=request.user)

    service_centers = ServiceCenter.objects.all()

    context = {
        "form": form,
        "service_centers": service_centers,
        "min_date": date.today().isoformat(),
        "max_date": (date.today() + timedelta(days=30)).isoformat(),
    }

    return render(request, "core/service_booking.html", context)


@login_required
def get_available_services(request):
    """AJAX-функция для получения услуг по выбранному автосервису"""
    if (
        request.method == "GET"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        service_center_id = request.GET.get("service_center_id")

        try:
            services = ServiceType.objects.filter(
                service_center_id=service_center_id, is_active=True
            )
            options = '<option value="">Выберите услугу</option>'
            for service in services:
                options += f'<option value="{service.id}">{service.name} - {service.duration} мин. - {service.price} руб.</option>'
            return JsonResponse({"options": options})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def get_available_time_slots(request):
    """AJAX-функция для получения доступных временных слотов"""
    if (
        request.method == "GET"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):

        selected_date = request.GET.get("date")
        service_type_id = request.GET.get("service_type")
        service_center_id = request.GET.get("service_center")

        try:
            selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
            service_type = ServiceType.objects.get(id=service_type_id)
            service_center = ServiceCenter.objects.get(id=service_center_id)

            day_of_week = selected_date.isoweekday()
            try:
                working_hours = WorkingHours.objects.get(day_of_week=day_of_week)
                if not working_hours.is_working:
                    return JsonResponse({"available_slots": []})
            except WorkingHours.DoesNotExist:
                return JsonResponse({"available_slots": []})

            all_slots = generate_time_slots(
                working_hours.start_time, working_hours.end_time
            )

            booked_appointments = Appointment.objects.filter(
                scheduled_date=selected_date,
                status__in=["SCHEDULED", "IN_PROGRESS"],
                service_center=service_center,
            )

            available_slots = []
            for slot in all_slots:
                slot_time = datetime.strptime(slot, "%H:%M").time()
                slot_end_time = (
                    datetime.combine(selected_date, slot_time)
                    + timedelta(minutes=service_type.duration)
                ).time()

                is_available = True
                for appointment in booked_appointments:
                    app_start = appointment.scheduled_time
                    app_end = appointment.end_time

                    if not (slot_end_time <= app_start or slot_time >= app_end):
                        is_available = False
                        break

                if is_available:
                    available_slots.append(slot)

            return JsonResponse({"available_slots": available_slots})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


def generate_time_slots(start_time, end_time, slot_duration=30):
    """Генерирует список временных слотов"""
    slots = []
    start_datetime = datetime.combine(date.today(), start_time)
    end_datetime = datetime.combine(date.today(), end_time)

    current_time = start_datetime
    while current_time + timedelta(minutes=slot_duration) <= end_datetime:
        lunch_start = datetime.combine(date.today(), time(13, 0))
        lunch_end = datetime.combine(date.today(), time(14, 0))

        if not (lunch_start <= current_time < lunch_end):
            slots.append(current_time.strftime("%H:%M"))

        current_time += timedelta(minutes=slot_duration)

    return slots


@login_required
def appointment_list(request):
    """Список записей пользователя"""
    appointments = Appointment.objects.filter(car__owner=request.user).order_by(
        "-scheduled_date", "scheduled_time"
    )

    context = {"appointments": appointments}

    return render(request, "core/appointment_list.html", context)


@login_required
def cancel_appointment(request, appointment_id):
    """Отмена записи"""
    appointment = get_object_or_404(
        Appointment, id=appointment_id, car__owner=request.user
    )

    if request.method == "POST":
        if appointment.status == "SCHEDULED":
            appointment.status = "CANCELLED"
            appointment.save()
            messages.success(request, "Запись успешно отменена")
        else:
            messages.error(request, "Невозможно отменить запись в текущем статусе")

    return redirect("appointment_list")


def admin_required(view_func):
    """Декоратор для проверки прав администратора"""
    return user_passes_test(lambda u: u.is_staff)(view_func)


@login_required
@admin_required
def admin_dashboard(request):
    """Главная страница администратора"""
    service_centers = ServiceCenter.objects.all()

    total_appointments = Appointment.objects.count()
    today_appointments = Appointment.objects.filter(
        scheduled_date=timezone.now().date()
    ).count()
    pending_appointments = Appointment.objects.filter(status="SCHEDULED").count()

    context = {
        "service_centers": service_centers,
        "total_appointments": total_appointments,
        "today_appointments": today_appointments,
        "pending_appointments": pending_appointments,
    }
    return render(request, "core/admin_dashboard.html", context)


@login_required
@admin_required
def admin_service_center_detail(request, service_center_id):
    """Детальная страница автосервиса с календарем и статистикой"""
    service_center = get_object_or_404(ServiceCenter, id=service_center_id)

    today = timezone.now().date()
    year = request.GET.get("year", today.year)
    month = request.GET.get("month", today.month)

    appointments = Appointment.objects.filter(
        scheduled_date__year=year, scheduled_date__month=month
    ).select_related("car", "service_type", "car__owner")

    calendar_events = []
    for appointment in appointments:
        calendar_events.append(
            {
                "id": str(appointment.id),
                "title": f"{appointment.car} - {appointment.service_type.name}",
                "start": f"{appointment.scheduled_date}T{appointment.scheduled_time}",
                "end": (
                    f"{appointment.scheduled_date}T{appointment.end_time}"
                    if appointment.end_time
                    else f"{appointment.scheduled_date}T{appointment.scheduled_time}"
                ),
                "status": appointment.status,
                "user": appointment.car.owner.get_full_name()
                or appointment.car.owner.username,
                "car": str(appointment.car),
                "service": appointment.service_type.name,
            }
        )

    start_date = today - timedelta(days=30)
    service_stats = (
        Appointment.objects.filter(
            scheduled_date__gte=start_date, scheduled_date__lte=today
        )
        .values("service_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    stats_labels = [stat["service_type__name"] for stat in service_stats]
    stats_data = [stat["count"] for stat in service_stats]

    status_stats = Appointment.objects.values("status").annotate(count=Count("id"))

    weekday_stats = (
        Appointment.objects.filter(scheduled_date__gte=start_date)
        .extra({"weekday": "EXTRACT(dow FROM scheduled_date)"})
        .values("weekday")
        .annotate(count=Count("id"))
        .order_by("weekday")
    )

    weekday_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    weekday_labels = []
    weekday_data = []
    for stat in weekday_stats:
        weekday_index = int(stat["weekday"])
        if 0 <= weekday_index < len(weekday_names):
            weekday_labels.append(weekday_names[weekday_index])
            weekday_data.append(stat["count"])

    context = {
        "service_center": service_center,
        "calendar_events": json.dumps(calendar_events, ensure_ascii=False),
        "stats_labels": json.dumps(stats_labels, ensure_ascii=False),
        "stats_data": json.dumps(stats_data, ensure_ascii=False),
        "weekday_labels": json.dumps(weekday_labels, ensure_ascii=False),
        "weekday_data": json.dumps(weekday_data, ensure_ascii=False),
        "status_stats": status_stats,
        "current_year": year,
        "current_month": month,
    }
    return render(request, "core/admin_service_center_detail.html", context)


@login_required
@admin_required
def admin_appointment_detail(request, appointment_id):
    """Детальная информация о записи"""
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in dict(Appointment.STATUS_CHOICES):
            appointment.status = new_status
            appointment.save()
            messages.success(request, "Статус записи обновлен!")

    context = {
        "appointment": appointment,
        "status_choices": Appointment.STATUS_CHOICES,
    }
    return render(request, "core/admin_appointment_detail.html", context)


@login_required
@admin_required
def admin_api_appointments(request):
    """API для получения записей (для календаря)"""
    start_date = request.GET.get("start")
    end_date = request.GET.get("end")

    appointments = Appointment.objects.all()

    if start_date:
        appointments = appointments.filter(scheduled_date__gte=start_date)
    if end_date:
        appointments = appointments.filter(scheduled_date__lte=end_date)

    events = []
    for appointment in appointments:
        events.append(
            {
                "id": str(appointment.id),
                "title": f"{appointment.car} - {appointment.service_type.name}",
                "start": f"{appointment.scheduled_date}T{appointment.scheduled_time}",
                "end": (
                    f"{appointment.scheduled_date}T{appointment.end_time}"
                    if appointment.end_time
                    else f"{appointment.scheduled_date}T{appointment.scheduled_time}"
                ),
                "status": appointment.status,
                "user": appointment.car.owner.get_full_name()
                or appointment.car.owner.username,
                "className": f"appointment-status-{appointment.status.lower()}",
            }
        )

    return JsonResponse(events, safe=False)


def get_service_details(request):
    service_id = request.GET.get("service_id")

    try:
        service = ServiceType.objects.get(id=service_id)
        service_data = {
            "id": service.id,
            "name": service.name,
            "description": service.description,
            "duration": service.duration,
            "price": service.price,
        }
        return JsonResponse({"service": service_data})
    except ServiceType.DoesNotExist:
        return JsonResponse({"error": "Service not found"}, status=404)
