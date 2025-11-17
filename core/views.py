from django.contrib.auth import login, logout
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from .models import (
    CarModel,
    UserProfile,
    Car,
    ServiceType,
    Appointment,
    WorkingHours,
    ServiceCenter,
)
from django.db.models import Avg
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import (
    UserRegisterForm,
    AppointmentForm,
    UserUpdateForm,
    ProfileUpdateForm,
    CarForm,
    LoginForm,
    ReviewForm,
)
from django.http import JsonResponse
from django.template.loader import render_to_string
from datetime import datetime, date, timedelta
from django.db.models import Q, Count, Sum
from .email_service import (
    send_appointment_cancelled_email,
)


def home(request):
    return render(request, "core/index.html")


def about(request):
    return render(request, "core/about.html")


def branches(request):
    """Публичная страница со списком филиалов без редактирования."""
    search_query = (
        request.POST.get("search", "").strip() if request.method == "POST" else ""
    )

    centers = ServiceCenter.objects.all().prefetch_related("working_hours")
    if search_query:
        centers = centers.filter(
            Q(address__icontains=search_query) | Q(phone__icontains=search_query)
        )

    centers = centers.order_by("address")
    today_dow = timezone.localtime(timezone.now()).isoweekday()
    center_cards = []
    for c in centers:
        try:
            wh = WorkingHours.objects.filter(
                service_center=c, day_of_week=today_dow
            ).first()
        except Exception:
            wh = None
        center_cards.append({"center": c, "today_wh": wh})

    if request.headers.get("HX-Request"):
        return render(
            request, "core/_branches_cards.html", {"center_cards": center_cards}
        )

    return render(request, "core/branches.html", {"center_cards": center_cards})


def branch_detail(request, service_center_id):
    """Детальная страница филиала: услуги, график,
    отзывы и форма отзыва (если доступна)."""
    sc = get_object_or_404(
        ServiceCenter.objects.prefetch_related("working_hours"),
        id=service_center_id,
    )
    services = ServiceType.objects.filter(service_center=sc, is_active=True).order_by(
        "name"
    )
    from .models import Review

    reviews = (
        Review.objects.filter(service_center=sc)
        .select_related("user")
        .order_by("-created_at")
    )
    avg_rating = reviews.aggregate(avg=Avg("rating")).get("avg") or 0

    review_form = None
    can_review = False
    if request.user.is_authenticated:
        has_completed = Appointment.objects.filter(
            car__owner=request.user,
            service_center=sc,
            status="COMPLETED",
        ).exists()
        already = Review.objects.filter(service_center=sc, user=request.user).exists()
        can_review = has_completed and not already
        if request.method == "POST" and can_review:
            review_form = ReviewForm(request.POST)
            if review_form.is_valid():
                r = review_form.save(commit=False)
                r.user = request.user
                r.service_center = sc
                r.save()
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    html = render_to_string(
                        "core/_review_thanks.html",
                        {"service_center": sc, "review": r},
                        request=request,
                    )
                    return JsonResponse({"success": True, "html": html})
                messages.success(request, "Спасибо за отзыв!")
                return redirect("branch_detail", service_center_id=sc.id)
            else:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    form_html = render_to_string(
                        "core/_review_form.html",
                        {"review_form": review_form},
                        request=request,
                    )
                    return JsonResponse(
                        {"success": False, "form_html": form_html}, status=400
                    )
        else:
            review_form = ReviewForm()

    context = {
        "service_center": sc,
        "services": services,
        "reviews": reviews,
        "avg_rating": avg_rating,
        "can_review": can_review,
        "review_form": review_form,
    }
    return render(request, "core/branch_detail.html", context)


def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("admin_panel:admin_dashboard" if user.is_staff else "home")
    else:
        form = UserRegisterForm()
    return render(request, "core/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(
            "admin_panel:admin_dashboard" if request.user.is_staff else "home"
        )
    if request.method == "POST":
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("admin_panel:admin_dashboard" if user.is_staff else "home")
    else:
        form = LoginForm()
    return render(request, "core/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def profile(request):

    auto_update_appointments()
    user_profile = UserProfile.objects.get(user=request.user)
    user_cars = Car.objects.filter(owner=request.user)
    appointments = (
        Appointment.objects.filter(car__owner=request.user)
        .select_related("car", "service_type", "service_center")
        .order_by("-scheduled_date", "scheduled_time")
    )

    today = timezone.localtime(timezone.now()).date()
    start_date = today - timedelta(days=89)
    appt_qs = Appointment.objects.filter(
        car__owner=request.user,
        scheduled_date__gte=start_date,
        scheduled_date__lte=today,
    ).select_related("service_type", "service_center")

    def month_iter(end_date, months_back=11):
        y = end_date.year
        m = end_date.month
        seq = []
        total = months_back + 1
        for i in range(total - 1, -1, -1):
            yy = y
            mm = m - i
            while mm <= 0:
                yy -= 1
                mm += 12
            seq.append((yy, mm))
        return seq

    def first_day_of_month(y, m):
        return date(y, m, 1)

    months = month_iter(today, months_back=11)
    start_month = first_day_of_month(months[0][0], months[0][1])

    appt_qs_12m = Appointment.objects.filter(
        car__owner=request.user,
        scheduled_date__gte=start_month,
        scheduled_date__lte=today,
    )
    by_month = (
        appt_qs_12m.values("scheduled_date__year", "scheduled_date__month")
        .annotate(c=Count("id"))
        .values_list("scheduled_date__year", "scheduled_date__month", "c")
    )
    month_map = {(y, m): c for (y, m, c) in by_month}

    labels = [f"{mm:02d}.{yy}" for (yy, mm) in months]
    data = [month_map.get((yy, mm), 0) for (yy, mm) in months]

    total_cost = (
        appt_qs.filter(status="COMPLETED").aggregate(total=Sum("service_type__price"))[
            "total"
        ]
        or 0
    )

    top_services_qs = (
        appt_qs.values("service_type__name").annotate(c=Count("id")).order_by("-c")[:5]
    )
    top_services_labels = [row["service_type__name"] or "—" for row in top_services_qs]
    top_services_data = [row["c"] for row in top_services_qs]

    top_centers_qs = (
        appt_qs.values("service_center__address")
        .annotate(c=Count("id"))
        .order_by("-c")[:5]
    )
    top_centers_labels = [
        row["service_center__address"] or "—" for row in top_centers_qs
    ]
    top_centers_data = [row["c"] for row in top_centers_qs]

    weekday_counts = [0] * 7  # Mon=0 .. Sun=6
    hour_counts = [0] * 24
    for ap in appt_qs:
        try:
            wd = ap.scheduled_date.weekday()
            weekday_counts[wd] += 1
        except Exception:
            pass
        try:
            hr = ap.scheduled_time.hour
            hour_counts[hr] += 1
        except Exception:
            pass
    weekday_labels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    hour_data = hour_counts

    top_service_name = top_services_labels[0] if top_services_labels else "—"
    avg_cost = (
        appt_qs.filter(status="COMPLETED")
        .aggregate(avg=Avg("service_type__price"))
        .get("avg")
        or 0
    )
    now_local = timezone.localtime(timezone.now())
    upcoming_appt = (
        Appointment.objects.filter(
            car__owner=request.user, status__in=["SCHEDULED", "IN_PROGRESS"]
        )
        .filter(
            Q(scheduled_date__gt=today)
            | Q(scheduled_date=today, scheduled_time__gte=now_local.time())
        )
        .select_related("service_type", "service_center", "car")
        .order_by("scheduled_date", "scheduled_time")
        .first()
    )

    context = {
        "profile": user_profile,
        "cars": user_cars,
        "appointments": appointments,
        "labels": labels,
        "data": data,
        "visits_count_90": sum(data),
        "total_cost": total_cost,
        "top_service_name": top_service_name,
        "avg_cost": avg_cost,
        "upcoming_appt": upcoming_appt,
        "top_services_labels": top_services_labels,
        "top_services_data": top_services_data,
        "top_centers_labels": top_centers_labels,
        "top_centers_data": top_centers_data,
        "weekday_labels": weekday_labels,
        "weekday_data": weekday_counts,
        "hour_data": hour_data,
    }
    return render(request, "core/profile.html", context)


@login_required
def profile_edit(request):
    if request.method == "POST":
        if "delete_avatar" in request.POST:
            profile = UserProfile.objects.get(user=request.user)
            if profile.avatar:
                profile.avatar.delete(save=False)
                profile.avatar = None  # type: ignore[assignment]
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
        form = CarForm(request.POST, request.FILES)
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
        form = CarForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                car.year = form.cleaned_data["year"]
                car.model = form.cleaned_data["model"]
                car.license_plate = form.cleaned_data["license_plate"]
                car.vin = form.cleaned_data.get("vin")
                uploaded = (
                    getattr(form, "cleaned_data", {}).get("photo")
                    if hasattr(form, "cleaned_data")
                    else None
                ) or (form.files.get("photo") if hasattr(form, "files") else None)
                if uploaded:
                    car.photo = uploaded  # type: ignore[assignment]
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


@login_required
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
    auto_update_appointments()
    preselect_car_id = request.GET.get("car")
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
        initial = {}
        if preselect_car_id:
            try:
                if Car.objects.filter(id=preselect_car_id, owner=request.user).exists():
                    initial["car"] = int(preselect_car_id)
            except Exception:
                pass
        form = AppointmentForm(user=request.user, initial=initial)

    context = {
        "form": form,
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
        auto_update_appointments()
        selected_date = request.GET.get("date")
        service_type_id = request.GET.get("service_type")
        service_center_id = request.GET.get("service_center")
        is_today_param = request.GET.get("is_today", "0")
        client_now_str = request.GET.get("client_now")

        try:
            selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
            service_type = ServiceType.objects.get(id=service_type_id)
            service_center = ServiceCenter.objects.get(id=service_center_id)

            day_of_week = selected_date.isoweekday()
            try:
                working_hours = WorkingHours.objects.get(
                    service_center=service_center, day_of_week=day_of_week
                )
                if not working_hours.is_working:
                    return JsonResponse({"available_slots": []})
            except WorkingHours.DoesNotExist:
                return JsonResponse({"available_slots": []})

            all_slots = generate_time_slots(
                working_hours.start_time,
                working_hours.end_time,
                slot_duration=30,
                lunch_start=working_hours.lunch_start,
                lunch_end=working_hours.lunch_end,
            )

            now = timezone.localtime(timezone.now())
            effective_now_time = None
            is_today_client = str(is_today_param).lower() in ("1", "true", "yes")
            if client_now_str:
                try:
                    effective_now_time = datetime.strptime(
                        client_now_str, "%H:%M"
                    ).time()
                except ValueError:
                    effective_now_time = None
            if effective_now_time is None and selected_date == now.date():
                effective_now_time = now.time()
            if effective_now_time and (is_today_client or selected_date == now.date()):
                all_slots = [
                    slot
                    for slot in all_slots
                    if datetime.strptime(slot, "%H:%M").time() > effective_now_time
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

                try:
                    if slot_end_time > working_hours.end_time:
                        continue
                except Exception:
                    pass

                is_available = True
                for appointment in booked_appointments:
                    app_start = appointment.scheduled_time
                    app_end = appointment.end_time
                    if app_end is None:
                        try:
                            app_end = (
                                datetime.combine(selected_date, app_start)
                                + timedelta(minutes=appointment.service_type.duration)
                            ).time()
                        except Exception:
                            app_end = app_start
                    if not (slot_end_time <= app_start or slot_time >= app_end):
                        is_available = False
                        break

                if is_available:
                    available_slots.append(slot)

            return JsonResponse({"available_slots": available_slots})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


def generate_time_slots(
    start_time, end_time, slot_duration=30, lunch_start=None, lunch_end=None
):
    """Генерирует список временных слотов, исключая время обеда при наличии"""
    slots = []
    start_datetime = datetime.combine(date.today(), start_time)
    end_datetime = datetime.combine(date.today(), end_time)

    lunch_start_dt = (
        datetime.combine(date.today(), lunch_start) if lunch_start else None
    )
    lunch_end_dt = datetime.combine(date.today(), lunch_end) if lunch_end else None

    current_time = start_datetime
    step = timedelta(minutes=slot_duration)
    while current_time + step <= end_datetime:
        in_lunch = False
        if lunch_start_dt and lunch_end_dt:
            in_lunch = lunch_start_dt <= current_time < lunch_end_dt
        if not in_lunch:
            slots.append(current_time.strftime("%H:%M"))
        current_time += step

    return slots


@login_required
def appointment_list(request):
    """Список записей пользователя"""
    auto_update_appointments()
    appointments = (
        Appointment.objects.filter(car__owner=request.user)
        .select_related("service_center", "service_type", "car")
        .order_by("-scheduled_date", "scheduled_time")
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


@login_required
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
    """Auto-cancel overdue appointments that are still SCHEDULED.
    Overdue if scheduled_date < today OR (scheduled_date == today and end_time <= now).
    """
    now = timezone.localtime(timezone.now())
    today = now.date()
    current_time = now.time()
    qs = Appointment.objects.filter(status="SCHEDULED").filter(
        Q(scheduled_date__lt=today)
        | Q(scheduled_date=today, end_time__lte=current_time)
    )
    if qs.exists():
        overdue_ids = list(qs.values_list("id", flat=True))
        qs.update(status="CANCELLED", updated_at=now)
        try:
            for appt in Appointment.objects.filter(id__in=overdue_ids):
                try:
                    send_appointment_cancelled_email(appt)
                except Exception:
                    pass
        except Exception:
            pass


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_reply_review(request, review_id):
    from .models import Review

    review = get_object_or_404(Review, id=review_id)
    if request.method == "POST":
        reply = (request.POST.get("admin_reply") or "").strip()
        review.admin_reply = reply if reply else None
        review.admin_reply_at = timezone.localtime(timezone.now()) if reply else None
        review.save(update_fields=["admin_reply", "admin_reply_at", "updated_at"])
        messages.success(request, "Ответ сохранён")
    return redirect(
        "admin_panel:admin_service_center_detail",
        service_center_id=review.service_center.id,
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_delete_review(request, review_id):
    from .models import Review

    review = get_object_or_404(Review, id=review_id)
    sc_id = review.service_center.id
    if request.method == "POST":
        review.delete()
        messages.success(request, "Отзыв удалён")
    return redirect("admin_panel:admin_service_center_detail", service_center_id=sc_id)
