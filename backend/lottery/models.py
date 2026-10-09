import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


class Prize(models.Model):
    name = models.CharField("Name", max_length=120)
    description = models.CharField("Short description", max_length=240, blank=True)
    emoji = models.CharField("Symbol", max_length=8, default="🎁")
    color = models.CharField(
        "Color", max_length=7, default="#D8A75F",
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Enter a color such as #D8A75F.")],
    )
    quantity = models.PositiveIntegerField("Remaining spins", default=0)
    weight = models.PositiveIntegerField(
        "Chance weight", default=1, validators=[MinValueValidator(1)],
        help_text="Chance is proportional to remaining spins × this weight.",
    )
    display_weight = models.DecimalField(
        "Wheel display weight", max_digits=4, decimal_places=2, default=1,
        help_text="Changes only the sector size on screen, never the draw chance.",
    )
    is_winning = models.BooleanField("Winning outcome", default=True)
    is_active = models.BooleanField("Active", default=True)
    sort_order = models.PositiveIntegerField("Display order", default=0)
    created_at = models.DateTimeField("Created at", auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "Draw category"
        verbose_name_plural = "Draw categories"
        constraints = [
            models.CheckConstraint(condition=models.Q(weight__gte=1), name="prize_weight_positive"),
        ]

    def __str__(self):
        return self.name


class Draw(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prize = models.ForeignKey(Prize, on_delete=models.PROTECT, verbose_name="Outcome")
    prize_name = models.CharField("Name at draw", max_length=120)
    prize_description = models.CharField("Description at draw", max_length=240, blank=True)
    prize_emoji = models.CharField("Symbol at draw", max_length=8, default="🎁")
    prize_color = models.CharField("Color at draw", max_length=7, default="#D8A75F")
    prize_is_winning = models.BooleanField("Winning at draw", default=True)
    is_campaign_draw = models.BooleanField("Current campaign", default=False)
    voided_at = models.DateTimeField("Cancelled at", null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Cancelled by", related_name="cancelled_lottery_draws",
    )
    void_reason = models.CharField("Cancellation reason", max_length=240, blank=True)
    created_at = models.DateTimeField("Drawn at", auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Draw"
        verbose_name_plural = "Draw history"

    def __str__(self):
        return f"{self.prize_name} · {self.created_at:%d.%m.%Y %H:%M}"

