from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.db.models.functions import ExtractWeekDay
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
    ServiceCenterEditForm,
)
from django.http import JsonResponse
from datetime import datetime, date, timedelta, time


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_branches(request):
    """Список филиалов (автосервисов) в виде карточек с фото"""
    service_centers = ServiceCenter.objects.all().annotate(
        appointments_count=Count("appointment", distinct=False)
    )
    return render(
        request,
        "core/admin_branches.html",
        {"service_centers": service_centers},
    )


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
            return redirect("admin_branches" if user.is_staff else "home")
    else:
        form = UserRegisterForm()
    return render(request, "core/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("admin_branches" if request.user.is_staff else "home")
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("admin_branches" if user.is_staff else "home")
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
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
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

            now = timezone.localtime(timezone.now())
            if selected_date == now.date():
                all_slots = [
                    slot
                    for slot in all_slots
                    if datetime.strptime(slot, "%H:%M").time()
                    > (now + timedelta(minutes=15)).time()
                ]

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
    auto_update_appointments()
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

    upcoming_appointments = (
        Appointment.objects.filter(
            scheduled_date__gte=timezone.localtime(timezone.now()).date()
        )
        .select_related("service_center", "car", "service_type", "car__owner")
        .order_by("scheduled_date", "scheduled_time")[:12]
    )

    context = {
        "service_centers": service_centers,
        "total_appointments": total_appointments,
        "today_appointments": today_appointments,
        "pending_appointments": pending_appointments,
        "upcoming_appointments": upcoming_appointments,
    }
    return render(request, "core/admin_dashboard.html", context)


@login_required
@admin_required
def admin_service_center_detail(request, service_center_id):
    """Детальная страница автосервиса с календарем, расписанием на сегодня и статистикой"""
    service_center = get_object_or_404(ServiceCenter, id=service_center_id)

    today = timezone.localtime(timezone.now()).date()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))
    selected_date_str = request.GET.get("date")
    selected_date = (
        datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        if selected_date_str
        else today
    )
    period = request.GET.get("period", "week")

    appointments = (
        Appointment.objects.filter(
            scheduled_date__year=year,
            scheduled_date__month=month,
            service_center=service_center,
        )
        .select_related("car", "service_type", "car__owner")
        .order_by("scheduled_date", "scheduled_time")
    )

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
            scheduled_date__gte=start_date,
            scheduled_date__lte=today,
            service_center=service_center,
        )
        .values("service_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    stats_labels = [stat["service_type__name"] for stat in service_stats]
    stats_data = [stat["count"] for stat in service_stats]

    status_stats = (
        Appointment.objects.filter(service_center=service_center)
        .values("status")
        .annotate(count=Count("id"))
    )

    weekday_stats = (
        Appointment.objects.filter(
            scheduled_date__gte=start_date, service_center=service_center
        )
        .annotate(weekday=ExtractWeekDay("scheduled_date"))
        .values("weekday")
        .annotate(count=Count("id"))
        .order_by("weekday")
    )

    weekday_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    weekday_labels = []
    weekday_data = []
    for stat in weekday_stats:
        weekday_index = (int(stat["weekday"]) - 2) % 7
        weekday_labels.append(weekday_names[weekday_index])
        weekday_data.append(stat["count"])

    try:
        working_hours = WorkingHours.objects.get(day_of_week=selected_date.isoweekday())
    except WorkingHours.DoesNotExist:
        working_hours = None

    todays_schedule = []
    if working_hours and working_hours.is_working:
        all_slots = generate_time_slots(
            working_hours.start_time, working_hours.end_time
        )

        now = timezone.localtime(timezone.now())
        if selected_date == now.date():
            all_slots = [
                s
                for s in all_slots
                if datetime.strptime(s, "%H:%M").time()
                > (now + timedelta(minutes=0)).time()
            ]

        day_appointments = (
            Appointment.objects.filter(
                scheduled_date=selected_date,
                service_center=service_center,
                status__in=["SCHEDULED", "IN_PROGRESS"],
            )
            .select_related("car", "service_type", "car__owner")
            .order_by("scheduled_time")
        )

        last_app_id = None
        for slot in all_slots:
            slot_time = datetime.strptime(slot, "%H:%M").time()
            matched = None
            for a in day_appointments:
                # determine appointment interval
                end_t = a.end_time
                if not end_t and a.service_type and a.service_type.duration:
                    end_t = (
                        datetime.combine(selected_date, a.scheduled_time)
                        + timedelta(minutes=a.service_type.duration)
                    ).time()
                if not end_t:
                    end_t = a.scheduled_time

                if a.scheduled_time <= slot_time < end_t:
                    matched = a
                    break
            if matched:
                if str(matched.id) != str(last_app_id):
                    end_t = matched.end_time
                    if (
                        not end_t
                        and matched.service_type
                        and matched.service_type.duration
                    ):
                        end_t = (
                            datetime.combine(selected_date, matched.scheduled_time)
                            + timedelta(minutes=matched.service_type.duration)
                        ).time()
                    if not end_t:
                        end_t = matched.scheduled_time
                    todays_schedule.append(
                        {
                            "busy": True,
                            "start": matched.scheduled_time.strftime("%H:%M"),
                            "end": end_t.strftime("%H:%M"),
                            "title": f"{matched.service_type.name} — {matched.car}",
                            "status": matched.status,
                            "appointment_id": str(matched.id),
                        }
                    )
                    last_app_id = str(matched.id)
                # skip subsequent slots for the same appointment
            else:
                todays_schedule.append({"time": slot, "busy": False})

    # Диапазон для графика посещаемости
    if period == "month":
        chart_start = today - timedelta(days=29)
    else:
        chart_start = today - timedelta(days=6)

    visits_qs = (
        Appointment.objects.filter(
            scheduled_date__gte=chart_start,
            scheduled_date__lte=today,
            service_center=service_center,
        )
        .values("scheduled_date")
        .annotate(count=Count("id"))
        .order_by("scheduled_date")
    )
    visits_labels = []
    visits_data = []
    current = chart_start
    while current <= today:
        visits_labels.append(current.strftime("%d.%m"))
        found = next((v for v in visits_qs if v["scheduled_date"] == current), None)
        visits_data.append(found["count"] if found else 0)
        current += timedelta(days=1)

    status_label_map = {k: v for k, v in Appointment.STATUS_CHOICES}
    status_stats_list = [
        {
            "status": s["status"],
            "count": s["count"],
            "label": status_label_map.get(s["status"], s["status"]),
        }
        for s in status_stats
    ]

    # Empty-state flags
    status_total = sum(s["count"] for s in status_stats)
    has_service_stats = any(stats_data) if stats_data else False
    has_weekday_stats = any(weekday_data) if weekday_data else False
    has_visits_data = any(visits_data) if visits_data else False

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "visits_labels": visits_labels,
                "visits_data": visits_data,
            }
        )

    context = {
        "service_center": service_center,
        "calendar_events": json.dumps(calendar_events, ensure_ascii=False),
        "stats_labels": json.dumps(stats_labels, ensure_ascii=False),
        "stats_data": json.dumps(stats_data, ensure_ascii=False),
        "weekday_labels": json.dumps(weekday_labels, ensure_ascii=False),
        "weekday_data": json.dumps(weekday_data, ensure_ascii=False),
        "status_stats": status_stats_list,
        "current_year": year,
        "current_month": month,
        "selected_date": selected_date.isoformat(),
        "todays_schedule": todays_schedule,
        "period": period,
        "visits_labels": json.dumps(visits_labels, ensure_ascii=False),
        "visits_data": json.dumps(visits_data, ensure_ascii=False),
        "has_service_stats": has_service_stats,
        "has_weekday_stats": has_weekday_stats,
        "has_visits_data": has_visits_data,
        "status_total": status_total,
    }
    return render(request, "core/admin_service_center_detail.html", context)


@login_required
@admin_required
def admin_service_center_edit(request, service_center_id):
    """Редактирование информации об автосервисе"""
    service_center = get_object_or_404(ServiceCenter, id=service_center_id)

    if request.method == "POST":
        form = ServiceCenterEditForm(
            request.POST, request.FILES, instance=service_center
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Информация о филиале обновлена")
            return redirect(
                "admin_service_center_detail", service_center_id=service_center.id
            )
    else:
        form = ServiceCenterEditForm(instance=service_center)

    return render(
        request,
        "core/admin_service_center_edit.html",
        {"form": form, "service_center": service_center},
    )


@login_required
@admin_required
def admin_api_day_schedule(request, service_center_id):
    """JSON: расписание по слотам для выбранного дня"""
    date_str = request.GET.get("date")
    if not date_str:
        return JsonResponse({"error": "Missing date"}, status=400)
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Invalid date format"}, status=400)

    service_center = get_object_or_404(ServiceCenter, id=service_center_id)

    try:
        working_hours = WorkingHours.objects.get(day_of_week=selected_date.isoweekday())
    except WorkingHours.DoesNotExist:
        return JsonResponse({"slots": []})

    if not working_hours.is_working:
        return JsonResponse({"slots": []})

    all_slots = generate_time_slots(working_hours.start_time, working_hours.end_time)
    now = timezone.localtime(timezone.now())
    if selected_date == now.date():
        all_slots = [
            s
            for s in all_slots
            if datetime.strptime(s, "%H:%M").time()
            > (now + timedelta(minutes=0)).time()
        ]

    day_appointments = (
        Appointment.objects.filter(
            scheduled_date=selected_date,
            service_center=service_center,
            status__in=["SCHEDULED", "IN_PROGRESS"],
        )
        .select_related("car", "service_type", "car__owner")
        .order_by("scheduled_time")
    )

    slots = []
    last_app_id = None
    for slot in all_slots:
        slot_time = datetime.strptime(slot, "%H:%M").time()
        matched = None
        for a in day_appointments:
            end_t = a.end_time
            if not end_t and a.service_type and a.service_type.duration:
                end_t = (
                    datetime.combine(selected_date, a.scheduled_time)
                    + timedelta(minutes=a.service_type.duration)
                ).time()
            if not end_t:
                end_t = a.scheduled_time

            if a.scheduled_time <= slot_time < end_t:
                matched = a
                break
        if matched:
            if str(matched.id) != str(last_app_id):
                end_t = matched.end_time
                if not end_t and matched.service_type and matched.service_type.duration:
                    end_t = (
                        datetime.combine(selected_date, matched.scheduled_time)
                        + timedelta(minutes=matched.service_type.duration)
                    ).time()
                if not end_t:
                    end_t = matched.scheduled_time
                slots.append(
                    {
                        "busy": True,
                        "start": matched.scheduled_time.strftime("%H:%M"),
                        "end": end_t.strftime("%H:%M"),
                        "title": f"{matched.service_type.name} — {matched.car}",
                        "status": matched.status,
                        "appointment_id": str(matched.id),
                    }
                )
                last_app_id = str(matched.id)
            # skip subsequent slots for same appointment
        else:
            slots.append({"time": slot, "busy": False})

    return JsonResponse({"slots": slots})


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
    service_center_id = request.GET.get("service_center")

    appointments = Appointment.objects.all()

    if start_date:
        appointments = appointments.filter(scheduled_date__gte=start_date)
    if end_date:
        appointments = appointments.filter(scheduled_date__lte=end_date)
    if service_center_id:
        appointments = appointments.filter(service_center_id=service_center_id)

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


def auto_update_appointments():
    now = timezone.localtime(timezone.now())
    today = now.date()
    current_time = now.time()

    expired_appointments = Appointment.objects.filter(
        scheduled_date__lt=today, status__in=["SCHEDULED", "IN_PROGRESS"]
    ) | Appointment.objects.filter(
        scheduled_date=today,
        end_time__lt=current_time,
        status__in=["SCHEDULED", "IN_PROGRESS"],
    )

    for appointment in expired_appointments:
        appointment.status = "COMPLETED"
        appointment.save()
