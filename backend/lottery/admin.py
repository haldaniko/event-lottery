from django.conf import settings
from django.contrib import admin, messages
from django.db.models import Sum
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from .models import Draw, Prize
from .services import cancel_draws


@admin.register(Prize)
class PrizeAdmin(admin.ModelAdmin):
    change_list_template = "admin/lottery/prize/change_list.html"
    list_display = ("emoji", "name", "quantity", "is_winning", "is_active")
    list_display_links = ("name",)
    list_editable = ("quantity", "is_winning", "is_active")
    list_filter = ("is_active", "is_winning")
    search_fields = ("name", "description")
    ordering = ("sort_order", "id")
    fieldsets = (
        (None, {"fields": ("name", "quantity", "is_winning", "is_active")}),
        ("Wheel appearance", {
            "fields": ("emoji", "color", "description"),
            "classes": ("collapse",),
        }),
    )

    def changelist_view(self, request, extra_context=None):
        if request.method == "GET" and not request.GET:
            return redirect(f"{request.path}?is_active__exact=1")
        used = Draw.objects.filter(is_campaign_draw=True, voided_at__isnull=True).count()
        stock = Prize.objects.filter(is_active=True).aggregate(total=Sum("quantity"))["total"] or 0
        slots_left = max(settings.LOTTERY_SPIN_LIMIT - used, 0)
        context = {
            "spin_limit": settings.LOTTERY_SPIN_LIMIT,
            "spins_used": used,
            "slots_left": slots_left,
            "stock_total": stock,
            "stock_matches": stock == slots_left,
            "draw_history_url": reverse("admin:lottery_draw_changelist"),
        }
        context.update(extra_context or {})
        return super().changelist_view(request, extra_context=context)


@admin.register(Draw)
class DrawAdmin(admin.ModelAdmin):
    list_display = ("short_id", "prize_name", "draw_status", "created_at")
    list_filter = ("is_campaign_draw", ("voided_at", admin.EmptyFieldListFilter), "prize")
    search_fields = ("prize_name", "id")
    readonly_fields = (
        "id", "prize", "prize_name", "prize_description", "prize_emoji", "prize_color",
        "prize_is_winning", "is_campaign_draw", "created_at", "voided_at", "voided_by", "void_reason",
    )
    date_hierarchy = "created_at"
    actions = ("cancel_selected_draws",)

    def changelist_view(self, request, extra_context=None):
        if request.method == "GET" and not request.GET:
            return redirect(f"{request.path}?is_campaign_draw__exact=1")
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description="Number")
    def short_id(self, obj):
        return str(obj.id)[:8].upper()

    @admin.display(description="Status")
    def draw_status(self, obj):
        if obj.voided_at:
            return "Cancelled"
        return "Valid" if obj.is_campaign_draw else "Previous campaign"

    @admin.action(description="Cancel selected draws and return their outcomes", permissions=["change"])
    def cancel_selected_draws(self, request, queryset):
        eligible = list(queryset.filter(is_campaign_draw=True, voided_at__isnull=True))
        if not eligible:
            self.message_user(request, "No valid current-campaign draws were selected.", messages.WARNING)
            return None

        if request.POST.get("confirm") == "yes":
            count = cancel_draws([draw.pk for draw in eligible], request.user, request.POST.get("reason", ""))
            self.message_user(request, f"Cancelled {count} draw(s) and returned their outcomes to stock.", messages.SUCCESS)
            return None

        return TemplateResponse(request, "admin/lottery/draw/cancel_confirmation.html", {
            **self.admin_site.each_context(request),
            "title": "Confirm draw cancellation",
            "draws": eligible,
            "opts": self.model._meta,
        })

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
