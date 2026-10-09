from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Draw, Prize


def cancel_draws(draw_ids, user, reason=""):
    """Return one outcome for each current-campaign draw cancelled exactly once."""
    cancelled = 0
    with transaction.atomic():
        draws = Draw.objects.select_for_update().filter(
            pk__in=draw_ids, is_campaign_draw=True, voided_at__isnull=True,
        )
        for draw in draws:
            draw.voided_at = timezone.now()
            draw.voided_by = user
            draw.void_reason = reason.strip()[:240]
            draw.save(update_fields=["voided_at", "voided_by", "void_reason"])
            Prize.objects.filter(pk=draw.prize_id).update(quantity=F("quantity") + 1)
            cancelled += 1
    return cancelled
