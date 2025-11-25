from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Count, Min
from django.db.models.functions import ExtractWeekDay
from django.utils import timezone
import json

from core.views import generate_time_slots
from core.models import (
    ServiceType,
    Appointment,
    WorkingHours,
    ServiceCenter,
    UserProfile,
    Review,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from admin_panel.forms import ServiceCenterEditForm, ServiceCenterCreateForm
from django.http import JsonResponse
from datetime import datetime, timedelta
from .decorators import admin_required
from django.core.paginator import Paginator
from django.db.models import Q
from core.forms import UserUpdateForm, ProfileUpdateForm
from .forms import (
    ServiceTypeForm,
    ServiceTypeBaseCreateForm,
    CarBrandForm,
    CarModelForm,
    UserCreateForm,
)
from core.models import CarBrand, CarModel
from django.template.loader import render_to_string
from django.conf import settings
from django.core.files.storage import default_storage


@login_required
@admin_required
def admin_reviews(request):
    """Управление отзывами: список с фильтрами, быстрый ответ/удаление."""
    _auto_cancel_overdue_appointments()
    reviews = Review.objects.select_related("user", "service_center").all()

    branch = request.GET.get("branch", "").strip()
    rating = request.GET.get("rating", "").strip()
    has_reply = request.GET.get("has_reply", "").strip()
    q = request.GET.get("q", "").strip()

    if branch:
        reviews = reviews.filter(service_center_id=branch)
    if rating:
        try:
            r_int = int(rating)
            reviews = reviews.filter(rating=r_int)
        except ValueError:
            pass
    if has_reply == "yes":
        reviews = reviews.exclude(admin_reply__isnull=True).exclude(
            admin_reply__exact=""
        )
    elif has_reply == "no":
        reviews = reviews.filter(Q(admin_reply__isnull=True) | Q(admin_reply__exact=""))
    if q:
        reviews = reviews.filter(
            Q(comment__icontains=q)
            | Q(user__username__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
        )

    reviews = reviews.order_by("-created_at")

    page = request.GET.get("page", 1)
    paginator = Paginator(reviews, 20)
    page_obj = paginator.get_page(page)

    branches = ServiceCenter.objects.all().order_by("address")

    context = {
        "page_obj": page_obj,
        "branches": branches,
        "filters": {
            "branch": branch,
            "rating": rating,
            "has_reply": has_reply,
            "q": q,
        },
    }
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string(
            "admin_panel/partials/_reviews_table.html",
            context=context,
            request=request,
        )
        return JsonResponse({"html": html, "count": page_obj.paginator.count})

    return render(request, "admin_panel/admin_reviews.html", context)


@login_required
@admin_required
def admin_review_reply(request, review_id):
    """POST: ответ администратора на отзыв"""
    _auto_cancel_overdue_appointments()
    review = get_object_or_404(Review, id=review_id)
    if request.method != "POST":
        return redirect("admin_panel:admin_reviews")

    reply_text = request.POST.get("admin_reply", "").strip()
    review.admin_reply = reply_text
    review.admin_reply_at = timezone.localtime(timezone.now()) if reply_text else None
    review.save(update_fields=["admin_reply", "admin_reply_at"])

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True})

    messages.success(request, "Ответ сохранен.")
    referer = request.META.get("HTTP_REFERER")
    return redirect(referer or "admin_panel:admin_reviews")


@login_required
@admin_required
def admin_review_delete(request, review_id):
    """POST: удаление отзыва администратором"""
    _auto_cancel_overdue_appointments()
    review = get_object_or_404(Review, id=review_id)
    if request.method == "POST":
        review.delete()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})

        messages.success(request, "Отзыв удален.")
        referer = request.META.get("HTTP_REFERER")
        return redirect(referer or "admin_panel:admin_reviews")
    return redirect("admin_panel:admin_reviews")


def _auto_cancel_overdue_appointments():
    """Set status=CANCELLED for overdue appointments that are still SCHEDULED.
    Overdue means: scheduled_date < today OR (scheduled_date == today and end_time <= now).
    """
    now = timezone.localtime(timezone.now())
    today = now.date()
    now_time = now.time()
    (
        Appointment.objects.filter(status="SCHEDULED")
        .filter(
            Q(scheduled_date__lt=today)
            | Q(scheduled_date=today, end_time__lte=now_time)
        )
        .update(status="CANCELLED", updated_at=now)
    )


@login_required
@admin_required
def admin_dashboard(request):
    """Главная страница администратора"""
    _auto_cancel_overdue_appointments()
    service_centers = ServiceCenter.objects.all()

    today = timezone.localtime(timezone.now()).date()

    total_appointments = Appointment.objects.count()
    today_appointments = Appointment.objects.filter(scheduled_date=today).count()
    pending_appointments = Appointment.objects.filter(status="SCHEDULED").count()
    in_progress_appointments = Appointment.objects.filter(status="IN_PROGRESS").count()
    completed_30d = Appointment.objects.filter(
        status="COMPLETED", scheduled_date__gte=today - timedelta(days=30)
    ).count()
    cancelled_30d = Appointment.objects.filter(
        status="CANCELLED", scheduled_date__gte=today - timedelta(days=30)
    ).count()
    active_services = (
        ServiceType.objects.filter(is_active=True)
        .values_list("name", flat=True)
        .distinct()
        .count()
    )
    branches_count = ServiceCenter.objects.count()
    customers_count = Appointment.objects.values("car__owner").distinct().count()

    upcoming_appointments = (
        Appointment.objects.filter(
            scheduled_date__gte=timezone.localtime(timezone.now()).date(),
            status__in=["SCHEDULED", "IN_PROGRESS"],
        )
        .select_related("service_center", "car", "service_type", "car__owner")
        .order_by("scheduled_date", "scheduled_time")[:5]
    )

    chart_start = today - timedelta(days=6)
    visits_qs = (
        Appointment.objects.filter(
            scheduled_date__gte=chart_start, scheduled_date__lte=today
        )
        .values("scheduled_date")
        .annotate(count=Count("id"))
        .order_by("scheduled_date")
    )
    by_date = {row["scheduled_date"]: row["count"] for row in visits_qs}
    overall_visits_labels = []
    overall_visits_data = []
    current = chart_start
    while current <= today:
        overall_visits_labels.append(current.strftime("%d.%m"))
        overall_visits_data.append(by_date.get(current, 0))
        current += timedelta(days=1)

    services_qs = (
        Appointment.objects.filter(status__in=["SCHEDULED", "IN_PROGRESS", "COMPLETED"])
        .values("service_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    overall_service_labels = [s["service_type__name"] for s in services_qs]
    overall_service_data = [s["count"] for s in services_qs]

    status_label_map = {k: v for k, v in Appointment.STATUS_CHOICES}
    statuses_qs = Appointment.objects.values("status").annotate(count=Count("id"))
    counts_map = {row["status"]: row["count"] for row in statuses_qs}
    overall_statuses = [
        {
            "status": key,
            "label": status_label_map.get(key, key),
            "count": counts_map.get(key, 0),
        }
        for key, _ in Appointment.STATUS_CHOICES
    ]

    context = {
        "service_centers": service_centers,
        "total_appointments": total_appointments,
        "today_appointments": today_appointments,
        "pending_appointments": pending_appointments,
        "in_progress_appointments": in_progress_appointments,
        "completed_30d": completed_30d,
        "cancelled_30d": cancelled_30d,
        "active_services": active_services,
        "branches_count": branches_count,
        "customers_count": customers_count,
        "upcoming_appointments": upcoming_appointments,
        "overall_visits_labels": overall_visits_labels,
        "overall_visits_data": overall_visits_data,
        "overall_service_labels": overall_service_labels,
        "overall_service_data": overall_service_data,
        "overall_statuses": overall_statuses,
    }
    return render(request, "admin_panel/admin_dashboard.html", context)


@login_required
@admin_required
def admin_users(request):
    """Список пользователей: поиск по полям и дополнительные фильтры, пагинация"""
    _auto_cancel_overdue_appointments()
    username = request.GET.get("username", "").strip()
    name = request.GET.get("name", "").strip()
    email = request.GET.get("email", "").strip()
    phone = request.GET.get("phone", "").strip()
    has_cars = request.GET.get("has_cars")
    has_active_appts = request.GET.get("has_active_appts")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    qs = (
        User.objects.all()
        .select_related("userprofile")
        .annotate(
            cars_count=Count("car", distinct=True),
            appts_count=Count("car__appointment", distinct=True),
            active_appts_count=Count(
                "car__appointment",
                filter=Q(car__appointment__status__in=["SCHEDULED", "IN_PROGRESS"]),
                distinct=True,
            ),
        )
    )

    if username:
        qs = qs.filter(username__icontains=username)
    if name:
        qs = qs.filter(Q(first_name__icontains=name) | Q(last_name__icontains=name))
    if email:
        qs = qs.filter(email__icontains=email)
    if phone:
        qs = qs.filter(userprofile__phone__icontains=phone)
    if has_cars == "1":
        qs = qs.filter(cars_count__gt=0)
    if has_active_appts == "1":
        qs = qs.filter(active_appts_count__gt=0)
    if date_from:
        qs = qs.filter(date_joined__date__gte=date_from)
    if date_to:
        qs = qs.filter(date_joined__date__lte=date_to)

    qs = qs.order_by("username")

    page = request.GET.get("page", 1)
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(page)

    default_avatar = settings.STATIC_URL.rstrip("/") + "/core/img/default-avatar.png"
    for u in page_obj.object_list:
        avatar_url = ""
        try:
            up = getattr(u, "userprofile", None)
            avatar_field = getattr(up, "avatar", None) if up else None
            if avatar_field and getattr(avatar_field, "name", ""):
                if default_storage.exists(avatar_field.name):
                    avatar_url = avatar_field.url
        except Exception:
            avatar_url = ""
        setattr(u, "avatar_url", avatar_url or default_avatar)

    filters = {
        "username": username,
        "name": name,
        "email": email,
        "phone": phone,
        "has_cars": has_cars or "",
        "has_active_appts": has_active_appts or "",
        "date_from": date_from or "",
        "date_to": date_to or "",
    }

    return render(
        request,
        "admin_panel/admin_users.html",
        {"page_obj": page_obj, "filters": filters},
    )


@login_required
@admin_required
def admin_user_create(request):
    """Создание нового пользователя администратором"""
    _auto_cancel_overdue_appointments()

    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()

            from core.models import UserProfile

            UserProfile.objects.get_or_create(user=user)

            user_type = "администратор" if user.is_staff else "пользователь"
            messages.success(
                request, f'Пользователь "{user.username}" ({user_type}) успешно создан'
            )
            return redirect("admin_panel:admin_user_detail", user_id=user.id)
    else:
        form = UserCreateForm()

    return render(request, "admin_panel/admin_user_create.html", {"form": form})


@login_required
@admin_required
def admin_user_detail(request, user_id):
    """Детальный просмотр пользователя"""
    _auto_cancel_overdue_appointments()
    user = get_object_or_404(User.objects.select_related("userprofile"), pk=user_id)

    user_appointments = (
        Appointment.objects.filter(car__owner=user)
        .select_related("service_center", "service_type", "car")
        .order_by("-scheduled_date", "-scheduled_time")
    )
    total_appointments = user_appointments.count()
    last_appointment = user_appointments.first()
    recent_appointments = list(user_appointments[:5])

    default_avatar = settings.STATIC_URL.rstrip("/") + "/core/img/default-avatar.png"
    avatar_url = default_avatar
    try:
        up = getattr(user, "userprofile", None)
        avatar_field = getattr(up, "avatar", None) if up else None
        if avatar_field and getattr(avatar_field, "name", ""):
            if default_storage.exists(avatar_field.name):
                avatar_url = avatar_field.url
    except Exception:
        avatar_url = default_avatar

    resp = render(
        request,
        "admin_panel/admin_user_detail.html",
        {
            "user_obj": user,
            "total_appointments": total_appointments,
            "last_appointment": last_appointment,
            "recent_appointments": recent_appointments,
            "avatar_url": avatar_url,
        },
    )
    return resp


@login_required
@admin_required
def admin_user_edit(request, user_id):
    """Редактирование профиля пользователя (User + UserProfile)"""
    _auto_cancel_overdue_appointments()
    user = get_object_or_404(User, pk=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        u_form = UserUpdateForm(request.POST, instance=user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "Профиль обновлён")
            return redirect("admin_panel:admin_user_detail", user_id=user.pk)
    else:
        u_form = UserUpdateForm(instance=user)
        p_form = ProfileUpdateForm(instance=profile)

    return render(
        request,
        "admin_panel/admin_user_edit.html",
        {"u_form": u_form, "p_form": p_form, "user_obj": user},
    )


@login_required
@admin_required
def admin_user_delete(request, user_id):
    """Удаление пользователя с подтверждением"""
    _auto_cancel_overdue_appointments()
    user = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(request, f"Пользователь {username} удалён")
        return redirect("admin_panel:admin_users")

    return render(
        request,
        "admin_panel/admin_user_delete.html",
        {"user_obj": user},
    )


@login_required
@admin_required
def admin_user_stats(request, user_id):
    """Расширенная статистика пользователя: графики и агрегаты"""
    _auto_cancel_overdue_appointments()
    user = get_object_or_404(User, pk=user_id)

    appts = (
        Appointment.objects.filter(car__owner=user)
        .select_related("service_type", "service_center")
        .order_by("scheduled_date")
    )

    today = timezone.localtime(timezone.now()).date()
    from dateutil.relativedelta import relativedelta

    start_month = today.replace(day=1) - relativedelta(months=11)

    labels = []
    data = []
    current_month = start_month

    for _ in range(12):
        # Начало и конец текущего месяца
        month_start = current_month
        if current_month.month == 12:
            month_end = current_month.replace(day=31)
        else:
            next_month = current_month + relativedelta(months=1)
            month_end = next_month - timedelta(days=1)

        # Подсчет записей за месяц
        month_count = appts.filter(
            scheduled_date__gte=month_start, scheduled_date__lte=month_end
        ).count()

        labels.append(current_month.strftime("%b %Y"))
        data.append(month_count)
        current_month = current_month + relativedelta(months=1)

    top_services_qs = (
        appts.values("service_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    top_services_labels = [r["service_type__name"] for r in top_services_qs]
    top_services_data = [r["count"] for r in top_services_qs]

    top_centers_qs = (
        appts.values("service_center__address")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    top_centers_labels = [r["service_center__address"] for r in top_centers_qs]
    top_centers_data = [r["count"] for r in top_centers_qs]

    completed_qs = appts.filter(status="COMPLETED")
    total_cost = sum(a.service_type.price for a in completed_qs)

    weekday_counts = [0] * 7
    for row in appts.values("scheduled_date").annotate(count=Count("id")):
        wd = row["scheduled_date"].isoweekday()
        weekday_counts[(wd - 1) % 7] += row["count"]
    weekday_labels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    hour_counts = [0] * 24
    for row in appts.values("scheduled_time").annotate(count=Count("id")):
        hour = row["scheduled_time"].hour
        hour_counts[hour] += row["count"]

    context = {
        "user_obj": user,
        "labels": json.dumps(labels, ensure_ascii=False),
        "data": json.dumps(data, ensure_ascii=False),
        "top_services_labels": json.dumps(top_services_labels, ensure_ascii=False),
        "top_services_data": json.dumps(top_services_data, ensure_ascii=False),
        "top_centers_labels": json.dumps(top_centers_labels, ensure_ascii=False),
        "top_centers_data": json.dumps(top_centers_data, ensure_ascii=False),
        "total_cost": float(total_cost),
        "weekday_labels": json.dumps(weekday_labels, ensure_ascii=False),
        "weekday_data": json.dumps(weekday_counts, ensure_ascii=False),
        "hour_data": json.dumps(hour_counts, ensure_ascii=False),
    }

    return render(request, "admin_panel/admin_user_stats.html", context)


@login_required
@admin_required
def admin_appointments(request):
    """Страница управления всеми записями: фильтры, список, быстрые действия"""
    _auto_cancel_overdue_appointments()
    qs = Appointment.objects.select_related(
        "service_center", "car", "car__owner", "service_type"
    ).all()

    branch = request.GET.get("branch")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    statuses = request.GET.getlist("status")
    user_query = request.GET.get("user")
    plate_query = request.GET.get("plate")

    if branch:
        qs = qs.filter(service_center_id=branch)
    if date_from:
        qs = qs.filter(scheduled_date__gte=date_from)
    if date_to:
        qs = qs.filter(scheduled_date__lte=date_to)
    if statuses:
        qs = qs.filter(status__in=statuses)
    if user_query:
        qs = qs.filter(
            Q(car__owner__username__icontains=user_query)
            | Q(car__owner__first_name__icontains=user_query)
            | Q(car__owner__last_name__icontains=user_query)
            | Q(car__owner__email__icontains=user_query)
        )
    if plate_query:
        qs = qs.filter(car__license_plate__icontains=plate_query)

    qs = qs.order_by("-scheduled_date", "-scheduled_time")

    page = request.GET.get("page", 1)
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(page)

    branches = ServiceCenter.objects.all()
    status_choices = Appointment.STATUS_CHOICES

    context = {
        "page_obj": page_obj,
        "branches": branches,
        "status_choices": status_choices,
        "filters": {
            "branch": branch or "",
            "date_from": date_from or "",
            "date_to": date_to or "",
            "statuses": statuses or [],
            "user": user_query or "",
            "plate": plate_query or "",
        },
    }
    return render(request, "admin_panel/admin_appointments.html", context)


@login_required
@admin_required
def admin_api_update_appointment(request, appointment_id):
    """AJAX: Обновление статуса и добавление комментария администратора"""
    _auto_cancel_overdue_appointments()
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    appt = get_object_or_404(Appointment, id=appointment_id)
    new_status = request.POST.get("status")
    comment = request.POST.get("comment", "").strip()

    payload = {}
    if new_status and new_status in dict(Appointment.STATUS_CHOICES):
        appt.status = new_status
        payload["status"] = new_status
    if comment:
        prefix = "admin: "
        appt.notes = (appt.notes + "\n" if appt.notes else "") + prefix + comment
        payload["notes"] = appt.notes
    appt.save()

    return JsonResponse({"ok": True, **payload})


@login_required
@admin_required
def admin_api_overall_statuses(request):
    """AJAX: Статистика по статусам записей за период (неделя/месяц/все время) по всем филиалам"""
    from datetime import timedelta

    _auto_cancel_overdue_appointments()
    period = request.GET.get("period", "week")

    if period == "all":
        qs = Appointment.objects.values("status").annotate(count=Count("id"))
    else:
        today = timezone.localtime(timezone.now()).date()

        if period == "month":
            start_date = today - timedelta(days=29)
        else:
            start_date = today - timedelta(days=6)

        qs = (
            Appointment.objects.filter(
                scheduled_date__gte=start_date, scheduled_date__lte=today
            )
            .values("status")
            .annotate(count=Count("id"))
        )

    status_label_map = {k: v for k, v in Appointment.STATUS_CHOICES}
    counts_map = {row["status"]: row["count"] for row in qs}

    data = [
        {
            "status": key,
            "label": status_label_map.get(key, key),
            "count": counts_map.get(key, 0),
        }
        for key, _ in Appointment.STATUS_CHOICES
    ]
    return JsonResponse({"items": data})


@login_required
@admin_required
def admin_api_overall_visits(request):
    """AJAX: Общая посещаемость по всем филиалам для периода неделя/месяц/все время"""
    from datetime import timedelta

    _auto_cancel_overdue_appointments()
    today = timezone.localtime(timezone.now()).date()
    period = request.GET.get("period", "week")

    if period == "all":
        first_appointment = Appointment.objects.order_by("scheduled_date").first()
        if first_appointment:
            chart_start = first_appointment.scheduled_date
        else:
            chart_start = today - timedelta(days=6)
    elif period == "month":
        chart_start = today - timedelta(days=29)
    else:  # week
        chart_start = today - timedelta(days=6)

    visits_qs = (
        Appointment.objects.filter(
            scheduled_date__gte=chart_start, scheduled_date__lte=today
        )
        .values("scheduled_date")
        .annotate(count=Count("id"))
        .order_by("scheduled_date")
    )

    by_date = {row["scheduled_date"]: row["count"] for row in visits_qs}
    labels = []
    data = []
    current = chart_start

    if period == "all":
        total_days = (today - chart_start).days + 1
        if total_days > 90:
            step = 7
            while current <= today:
                week_end = min(current + timedelta(days=6), today)
                week_count = sum(
                    by_date.get(current + timedelta(days=i), 0)
                    for i in range((week_end - current).days + 1)
                )
                labels.append(current.strftime("%d.%m"))
                data.append(week_count)
                current += timedelta(days=step)
        else:
            while current <= today:
                labels.append(current.strftime("%d.%m"))
                data.append(by_date.get(current, 0))
                current += timedelta(days=1)
    else:
        while current <= today:
            labels.append(current.strftime("%d.%m"))
            data.append(by_date.get(current, 0))
            current += timedelta(days=1)

    return JsonResponse({"labels": labels, "data": data})


@login_required
@admin_required
def admin_service_center_detail(request, service_center_id):
    """Детальная страница автосервиса с календарем, расписанием на сегодня и статистикой"""
    _auto_cancel_overdue_appointments()
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
        working_hours = WorkingHours.objects.get(
            day_of_week=selected_date.isoweekday(), service_center=service_center
        )
    except WorkingHours.DoesNotExist:
        working_hours = None

    todays_schedule = []
    if working_hours and working_hours.is_working:
        now = timezone.localtime(timezone.now())
        if selected_date < now.date():
            day_appointments = (
                Appointment.objects.filter(
                    scheduled_date=selected_date,
                    service_center=service_center,
                    status__in=["COMPLETED"],
                )
                .select_related("car", "service_type", "car__owner")
                .order_by("scheduled_time")
            )
            for a in day_appointments:
                end_t = a.end_time
                if not end_t and a.service_type and a.service_type.duration:
                    end_t = (
                        datetime.combine(selected_date, a.scheduled_time)
                        + timedelta(minutes=a.service_type.duration)
                    ).time()
                if not end_t:
                    end_t = a.scheduled_time
                todays_schedule.append(
                    {
                        "busy": True,
                        "start": a.scheduled_time.strftime("%H:%M"),
                        "end": end_t.strftime("%H:%M"),
                        "title": f"{a.service_type.name} — {a.car}",
                        "status": a.status,
                        "appointment_id": str(a.id),
                    }
                )
        else:
            day_appointments = (
                Appointment.objects.filter(
                    scheduled_date=selected_date,
                    service_center=service_center,
                    status__in=["SCHEDULED", "IN_PROGRESS"],
                )
                .select_related("car", "service_type", "car__owner")
                .order_by("scheduled_time")
            )

            from core.models import BlockedTimeSlot

            blocked_slots = BlockedTimeSlot.objects.filter(
                service_center=service_center, date=selected_date
            )
            blocked_times = {bs.time: bs for bs in blocked_slots}

            all_slots = generate_time_slots(
                working_hours.start_time,
                working_hours.end_time,
                lunch_start=working_hours.lunch_start,
                lunch_end=working_hours.lunch_end,
            )
            if selected_date == now.date():
                all_slots = [
                    s
                    for s in all_slots
                    if datetime.strptime(s, "%H:%M").time()
                    > (now + timedelta(minutes=0)).time()
                ]

            last_app_id = None
            for slot in all_slots:
                slot_time = datetime.strptime(slot, "%H:%M").time()

                if slot_time in blocked_times:
                    blocked_slot = blocked_times[slot_time]
                    todays_schedule.append(
                        {
                            "time": slot,
                            "busy": False,
                            "blocked": True,
                            "blocked_id": str(blocked_slot.id),
                            "blocked_reason": blocked_slot.reason or "",
                            "selected_date": selected_date.isoformat(),
                        }
                    )
                    continue

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
                else:
                    todays_schedule.append(
                        {
                            "time": slot,
                            "busy": False,
                            "blocked": False,
                            "selected_date": selected_date.isoformat(),
                        }
                    )

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
    return render(request, "admin_panel/admin_service_center_detail.html", context)


@login_required
@admin_required
def admin_service_center_edit(request, service_center_id):
    """Редактирование информации об автосервисе"""
    _auto_cancel_overdue_appointments()
    service_center = get_object_or_404(ServiceCenter, id=service_center_id)

    if request.method == "POST":
        form = ServiceCenterEditForm(
            request.POST, request.FILES, instance=service_center
        )
        if form.is_valid():
            form.save()

            from core.models import WorkingHours

            for d in range(1, 8):
                start = request.POST.get(f"wh_{d}_start")
                end = request.POST.get(f"wh_{d}_end")
                lstart = request.POST.get(f"wh_{d}_lstart")
                lend = request.POST.get(f"wh_{d}_lend")
                work = request.POST.get(f"wh_{d}_work") == "on"

                if start and end:
                    WorkingHours.objects.update_or_create(
                        service_center=service_center,
                        day_of_week=d,
                        defaults={
                            "start_time": start,
                            "end_time": end,
                            "lunch_start": lstart if lstart else None,
                            "lunch_end": lend if lend else None,
                            "is_working": work,
                        },
                    )

            messages.success(request, "Информация о филиале обновлена")
            return redirect("admin_panel:admin_branches")
    else:
        form = ServiceCenterEditForm(instance=service_center)

    from core.models import WorkingHours

    weekdays_with_hours = []
    weekday_names = [
        (1, "Понедельник"),
        (2, "Вторник"),
        (3, "Среда"),
        (4, "Четверг"),
        (5, "Пятница"),
        (6, "Суббота"),
        (7, "Воскресенье"),
    ]

    for day_num, day_name in weekday_names:
        try:
            wh = WorkingHours.objects.get(
                service_center=service_center, day_of_week=day_num
            )
        except WorkingHours.DoesNotExist:
            wh = None
        weekdays_with_hours.append(
            {
                "day_num": day_num,
                "day_name": day_name,
                "working_hours": wh,
            }
        )

    return render(
        request,
        "admin_panel/admin_service_center_edit.html",
        {
            "form": form,
            "service_center": service_center,
            "weekdays_with_hours": weekdays_with_hours,
        },
    )


@login_required
@admin_required
def admin_service_center_delete(request, service_center_id):
    service_center = get_object_or_404(ServiceCenter, id=service_center_id)
    _auto_cancel_overdue_appointments()
    if request.method == "POST":
        appts = Appointment.objects.filter(service_center=service_center)
        for a in appts:
            a.status = "CANCELLED"
            a.save(update_fields=["status", "updated_at"])
        service_center.delete()
        messages.success(request, "Филиал удалён. Все записи в этом филиале отменены.")
        return redirect("admin_panel:admin_branches")
    return render(
        request,
        "admin_panel/admin_service_center_delete.html",
        {"service_center": service_center},
    )


@login_required
@admin_required
def admin_service_center_create(request):
    """Создание нового филиала с выбором услуг для него"""
    _auto_cancel_overdue_appointments()
    base_services = (
        ServiceType.objects.values("name")
        .annotate(default_duration=Min("duration"), default_price=Min("price"))
        .order_by("name")
    )

    if request.method == "POST":
        form = ServiceCenterCreateForm(request.POST, request.FILES)
        if form.is_valid():
            center = form.save()

            for d in range(1, 8):
                start = request.POST.get(f"wh_{d}_start")
                end = request.POST.get(f"wh_{d}_end")
                lstart = request.POST.get(f"wh_{d}_lstart")
                lend = request.POST.get(f"wh_{d}_lend")
                work = request.POST.get(f"wh_{d}_work") == "on"
                if start and end:
                    WorkingHours.objects.create(
                        service_center=center,
                        day_of_week=d,
                        start_time=start,
                        end_time=end,
                        lunch_start=lstart or None,
                        lunch_end=lend or None,
                        is_working=work,
                    )

            try:
                total_rows = int(request.POST.get("total_rows", "0"))
            except ValueError:
                total_rows = 0
            created = 0
            for i in range(total_rows):
                if request.POST.get(f"svc_sel_{i}") != "on":
                    continue
                name = request.POST.get(f"svc_name_{i}")
                duration_val = request.POST.get(f"svc_duration_{i}")
                price_val = request.POST.get(f"svc_price_{i}")
                desc_val = request.POST.get(f"svc_desc_{i}") or ""
                if not name:
                    continue
                try:
                    duration = int(duration_val) if duration_val else None
                except ValueError:
                    duration = None
                try:
                    price = float(price_val) if price_val else None
                except ValueError:
                    price = None
                ServiceType.objects.create(
                    name=name,
                    description=desc_val,
                    duration=duration or 60,
                    price=price or 0,
                    service_center=center,
                    is_active=True,
                )
                created += 1

            messages.success(
                request,
                f"Филиал создан. Добавлено услуг: {created}",
            )
            return redirect("admin_panel:admin_branches")
    else:
        form = ServiceCenterCreateForm()

    services_rows = []
    for idx, row in enumerate(base_services):
        services_rows.append(
            {
                "index": idx,
                "name": row["name"],
                "default_duration": row["default_duration"] or 60,
                "default_price": (
                    float(row["default_price"])
                    if row["default_price"] is not None
                    else 0.0
                ),
            }
        )

    weekdays = [
        (1, "Пн"),
        (2, "Вт"),
        (3, "Ср"),
        (4, "Чт"),
        (5, "Пт"),
        (6, "Сб"),
        (7, "Вс"),
    ]

    return render(
        request,
        "admin_panel/admin_service_center_create.html",
        {
            "form": form,
            "services_rows": services_rows,
            "total_rows": len(services_rows),
            "weekdays": weekdays,
        },
    )


@login_required
@admin_required
def admin_api_day_schedule(request, service_center_id):
    """JSON: расписание по слотам для выбранного дня"""
    _auto_cancel_overdue_appointments()
    date_str = request.GET.get("date")
    is_today_param = request.GET.get("is_today", "0")
    client_now_str = request.GET.get("client_now")
    if not date_str:
        return JsonResponse({"error": "Missing date"}, status=400)
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Invalid date format"}, status=400)

    service_center = get_object_or_404(ServiceCenter, id=service_center_id)

    try:
        working_hours = WorkingHours.objects.get(
            day_of_week=selected_date.isoweekday(), service_center=service_center
        )
    except WorkingHours.DoesNotExist:
        return JsonResponse({"slots": []})

    if not working_hours.is_working:
        return JsonResponse({"slots": []})

    now = timezone.localtime(timezone.now())

    client_now_time = None
    is_today_client = str(is_today_param).lower() in ("1", "true", "yes")
    if client_now_str:
        try:
            client_now_time = datetime.strptime(client_now_str, "%H:%M").time()
        except ValueError:
            client_now_time = None

    if selected_date < now.date():
        day_appointments = (
            Appointment.objects.filter(
                scheduled_date=selected_date,
                service_center=service_center,
                status__in=["COMPLETED"],
            )
            .select_related("car", "service_type", "car__owner")
            .order_by("scheduled_time")
        )
        slots = []
        for a in day_appointments:
            end_t = a.end_time
            if not end_t and a.service_type and a.service_type.duration:
                end_t = (
                    datetime.combine(selected_date, a.scheduled_time)
                    + timedelta(minutes=a.service_type.duration)
                ).time()
            if not end_t:
                end_t = a.scheduled_time
            slots.append(
                {
                    "busy": True,
                    "start": a.scheduled_time.strftime("%H:%M"),
                    "end": end_t.strftime("%H:%M"),
                    "title": f"{a.service_type.name} — {a.car}",
                    "status": a.status,
                    "appointment_id": str(a.id),
                }
            )
        return JsonResponse({"slots": slots})

    day_appointments = (
        Appointment.objects.filter(
            scheduled_date=selected_date,
            service_center=service_center,
            status__in=["SCHEDULED", "IN_PROGRESS"],
        )
        .select_related("car", "service_type", "car__owner")
        .order_by("scheduled_time")
    )

    from core.models import BlockedTimeSlot

    blocked_slots = BlockedTimeSlot.objects.filter(
        service_center=service_center, date=selected_date
    )
    blocked_times = {bs.time: bs for bs in blocked_slots}

    all_slots = generate_time_slots(
        working_hours.start_time,
        working_hours.end_time,
        lunch_start=working_hours.lunch_start,
        lunch_end=working_hours.lunch_end,
    )
    effective_now_time = None
    if is_today_client and client_now_time:
        effective_now_time = client_now_time
    elif selected_date == now.date():
        effective_now_time = (now + timedelta(minutes=0)).time()

    if effective_now_time:
        all_slots = [
            s
            for s in all_slots
            if datetime.strptime(s, "%H:%M").time() > effective_now_time
        ]

    slots = []
    last_app_id = None
    for slot in all_slots:
        slot_time = datetime.strptime(slot, "%H:%M").time()

        if slot_time in blocked_times:
            blocked_slot = blocked_times[slot_time]
            slots.append(
                {
                    "time": slot,
                    "busy": False,
                    "blocked": True,
                    "blocked_id": str(blocked_slot.id),
                    "blocked_reason": blocked_slot.reason or "",
                    "selected_date": selected_date.isoformat(),
                }
            )
            continue

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
        else:
            slots.append(
                {
                    "time": slot,
                    "busy": False,
                    "selected_date": selected_date.isoformat(),
                }
            )

    return JsonResponse({"slots": slots})


@login_required
@admin_required
def admin_appointment_detail(request, appointment_id):
    """Детальная информация о записи"""
    from payments.models import Payment

    _auto_cancel_overdue_appointments()
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in dict(Appointment.STATUS_CHOICES):
            appointment.status = new_status
            appointment.save()
            messages.success(request, "Статус записи обновлен!")

    # Получаем последний платёж для записи
    payment = (
        Payment.objects.filter(appointment=appointment).order_by("-created_at").first()
    )

    context = {
        "appointment": appointment,
        "status_choices": Appointment.STATUS_CHOICES,
        "payment": payment,
    }
    return render(request, "admin_panel/admin_appointment_detail.html", context)


@login_required
@admin_required
def admin_api_appointments(request):
    """API для получения записей (для календаря)"""
    _auto_cancel_overdue_appointments()
    start_date = request.GET.get("start")
    end_date = request.GET.get("end")
    service_center_id = request.GET.get("service_center")

    appointments = Appointment.objects.all()

    if start_date:
        from datetime import datetime

        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        appointments = appointments.filter(scheduled_date__gte=start_dt.date())
    if end_date:
        from datetime import datetime

        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        appointments = appointments.filter(scheduled_date__lte=end_dt.date())
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


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_branches(request):
    """Список филиалов (автосервисов) в виде карточек с фото"""
    _auto_cancel_overdue_appointments()
    today_dow = timezone.localtime(timezone.now()).isoweekday()
    centers = (
        ServiceCenter.objects.all()
        .prefetch_related("working_hours")
        .annotate(appointments_count=Count("appointment", distinct=False))
        .order_by("address")
    )
    center_cards = []
    for c in centers:
        try:
            wh = WorkingHours.objects.filter(
                service_center=c, day_of_week=today_dow
            ).first()
        except Exception:
            wh = None
        center_cards.append({"center": c, "today_wh": wh})
    return render(
        request,
        "admin_panel/admin_branches.html",
        {"center_cards": center_cards},
    )


@login_required
@admin_required
def admin_services(request):
    """Список всех услуг по всем филиалам"""
    _auto_cancel_overdue_appointments()
    services = (
        ServiceType.objects.select_related("service_center")
        .all()
        .order_by("name", "service_center__address")
    )
    return render(
        request,
        "admin_panel/admin_services.html",
        {"services": services},
    )


@login_required
@admin_required
def admin_service_edit(request, service_id):
    """Редактирование конкретной услуги (в рамках одного филиала)"""
    _auto_cancel_overdue_appointments()
    service = get_object_or_404(ServiceType, id=service_id)
    if request.method == "POST":
        form = ServiceTypeForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Услуга обновлена")
            return redirect("admin_panel:admin_services")
    else:
        form = ServiceTypeForm(instance=service)
    return render(
        request,
        "admin_panel/admin_service_edit.html",
        {"form": form, "service": service},
    )


@login_required
@admin_required
def admin_service_create(request):
    """Создание новой услуги: выбрать филиалы и задать цену для каждого"""
    _auto_cancel_overdue_appointments()
    centers = ServiceCenter.objects.all().order_by("address")
    if request.method == "POST":
        base_form = ServiceTypeBaseCreateForm(request.POST)
        center_prices = {}
        for c in centers:
            key = f"price_{c.id}"
            val = request.POST.get(key)
            if val is not None and val != "":
                try:
                    price = float(val)
                except ValueError:
                    price = None
                selected = request.POST.get(f"center_{c.id}") == "on"
                center_prices[str(c.id)] = {"selected": selected, "price": price}
        if base_form.is_valid():
            created = 0
            for c in centers:
                cp = center_prices.get(str(c.id))
                if not cp or not cp["selected"]:
                    continue
                ServiceType.objects.create(
                    name=base_form.cleaned_data["name"],
                    description=base_form.cleaned_data.get("description", ""),
                    duration=base_form.cleaned_data["duration"],
                    price=cp["price"] or 0,
                    service_center=c,
                    is_active=base_form.cleaned_data.get("is_active", True),
                )
                created += 1
            messages.success(
                request,
                f"Создано {created} записей услуги по филиалам",
            )
            return redirect("admin_panel:admin_services")
    else:
        base_form = ServiceTypeBaseCreateForm()
    return render(
        request,
        "admin_panel/admin_service_create.html",
        {"base_form": base_form, "centers": centers},
    )


@login_required
@admin_required
def admin_cars(request):
    """Список марок и моделей с действиями"""
    _auto_cancel_overdue_appointments()
    brands = CarBrand.objects.all().order_by("name").prefetch_related("carmodel_set")
    return render(
        request,
        "admin_panel/admin_cars.html",
        {"brands": brands},
    )


@login_required
@admin_required
def admin_brand_create(request):
    form = CarBrandForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Марка добавлена")
        return redirect("admin_panel:admin_cars")
    return render(
        request, "admin_panel/admin_brand_edit.html", {"form": form, "create": True}
    )


@login_required
@admin_required
def admin_brand_edit(request, brand_id):
    brand = get_object_or_404(CarBrand, id=brand_id)
    form = CarBrandForm(request.POST or None, instance=brand)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Марка обновлена")
        return redirect("admin_panel:admin_cars")
    return render(
        request, "admin_panel/admin_brand_edit.html", {"form": form, "brand": brand}
    )


@login_required
@admin_required
def admin_brand_delete(request, brand_id):
    brand = get_object_or_404(CarBrand, id=brand_id)
    if request.method == "POST":
        brand.delete()
        messages.success(request, "Марка удалена")
        return redirect("admin_panel:admin_cars")
    return render(request, "admin_panel/admin_brand_delete.html", {"brand": brand})


@login_required
@admin_required
def admin_model_create(request):
    initial = {}
    brand_id = request.GET.get("brand")
    if brand_id:
        try:
            brand = CarBrand.objects.get(id=brand_id)
            initial["brand"] = brand
        except CarBrand.DoesNotExist:
            pass
    form = CarModelForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Модель добавлена")
        return redirect("admin_panel:admin_cars")
    return render(
        request, "admin_panel/admin_model_edit.html", {"form": form, "create": True}
    )


@login_required
@admin_required
def admin_model_edit(request, model_id):
    model = get_object_or_404(CarModel, id=model_id)
    form = CarModelForm(request.POST or None, instance=model)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Модель обновлена")
        return redirect("admin_panel:admin_cars")
    return render(
        request, "admin_panel/admin_model_edit.html", {"form": form, "model": model}
    )


@login_required
@admin_required
def admin_model_delete(request, model_id):
    model = get_object_or_404(CarModel, id=model_id)
    if request.method == "POST":
        model.delete()
        messages.success(request, "Модель удалена")
        return redirect("admin_panel:admin_cars")
    return render(request, "admin_panel/admin_model_delete.html", {"model": model})


@login_required
@admin_required
def admin_toggle_slot_block(request, service_center_id):
    """API для блокировки/разблокировки временного слота"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    service_center = get_object_or_404(ServiceCenter, id=service_center_id)

    try:
        from core.models import BlockedTimeSlot

        date_str = request.POST.get("date")
        time_str = request.POST.get("time")
        action = request.POST.get("action")  # "block" or "unblock"

        if not date_str or not time_str or not action:
            return JsonResponse({"error": "Missing required fields"}, status=400)

        slot_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        slot_time = datetime.strptime(time_str, "%H:%M").time()

        if action == "block":
            blocked_slot, created = BlockedTimeSlot.objects.get_or_create(
                service_center=service_center,
                date=slot_date,
                time=slot_time,
                defaults={
                    "blocked_by": request.user,
                    "reason": request.POST.get("reason", ""),
                },
            )
            return JsonResponse(
                {"success": True, "action": "blocked", "id": str(blocked_slot.id)}
            )

        elif action == "unblock":
            BlockedTimeSlot.objects.filter(
                service_center=service_center, date=slot_date, time=slot_time
            ).delete()
            return JsonResponse({"success": True, "action": "unblocked"})
        else:
            return JsonResponse({"error": "Invalid action"}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
