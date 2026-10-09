import secrets
import time
import uuid

from django.conf import settings
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import F
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Draw, Prize


def prize_data(prize):
    return {
        "id": prize.id,
        "name": prize.name,
        "description": prize.description,
        "emoji": prize.emoji,
        "color": prize.color,
        "quantity": prize.quantity,
        "display_weight": float(prize.display_weight),
        "is_winning": prize.is_winning,
    }


def draw_data(draw):
    return {
        "id": str(draw.id),
        "created_at": draw.created_at.isoformat(),
        "cancelled": draw.voided_at is not None,
        "prize": {
            "id": draw.prize_id,
            "name": draw.prize_name,
            "description": draw.prize_description,
            "emoji": draw.prize_emoji,
            "color": draw.prize_color,
            "is_winning": draw.prize_is_winning,
        },
    }


class LotteryView(APIView):
    authentication_classes = []

    def get(self, request):
        used = Draw.objects.filter(is_campaign_draw=True, voided_at__isnull=True).count()
        slots_left = max(settings.LOTTERY_SPIN_LIMIT - used, 0)
        prizes = list(Prize.objects.filter(is_active=True, quantity__gt=0)) if slots_left else []
        return Response({
            "prizes": [prize_data(prize) for prize in prizes],
            "total_remaining": min(sum(prize.quantity for prize in prizes), slots_left),
            "spin_limit": settings.LOTTERY_SPIN_LIMIT,
            "spins_used": used,
        })


class DrawView(APIView):
    authentication_classes = []

    def post(self, request):
        if not isinstance(request.data, dict):
            return Response({"error": "Invalid draw request."}, status=400)

        try:
            draw_id = uuid.UUID(str(request.data.get("request_id", "")))
        except (ValueError, TypeError, AttributeError):
            return Response({"error": "Invalid draw request."}, status=400)

        previous = Draw.objects.select_related("prize").filter(pk=draw_id).first()
        if previous:
            return Response(draw_data(previous))

        # Conditional stock update prevents a prize from being awarded twice.
        # A fresh query on each retry accounts for another tablet taking the last item.
        for attempt in range(5):
            try:
                with transaction.atomic():
                    used = Draw.objects.filter(is_campaign_draw=True, voided_at__isnull=True).count()
                    if used >= settings.LOTTERY_SPIN_LIMIT:
                        return Response({"error": "All spins have been used."}, status=409)
                    prizes = list(Prize.objects.filter(is_active=True, quantity__gt=0))
                    total = sum(prize.quantity * prize.weight for prize in prizes)
                    if not total:
                        return Response({"error": "All spins have been used."}, status=409)

                    ticket = secrets.randbelow(total)
                    chosen = prizes[-1]
                    for prize in prizes:
                        ticket -= prize.quantity * prize.weight
                        if ticket < 0:
                            chosen = prize
                            break

                    updated = Prize.objects.filter(
                        pk=chosen.pk, is_active=True, quantity__gt=0
                    ).update(quantity=F("quantity") - 1)
                    if not updated:
                        continue

                    draw = Draw.objects.create(
                        id=draw_id,
                        prize=chosen,
                        prize_name=chosen.name,
                        prize_description=chosen.description,
                        prize_emoji=chosen.emoji,
                        prize_color=chosen.color,
                        prize_is_winning=chosen.is_winning,
                        is_campaign_draw=True,
                    )
                    return Response(draw_data(draw), status=201)
            except IntegrityError:
                previous = Draw.objects.select_related("prize").filter(pk=draw_id).first()
                if previous:
                    return Response(draw_data(previous))
            except OperationalError:
                if attempt == 4:
                    break
                time.sleep(0.05 * (attempt + 1))

        return Response({"error": "Please try again in a moment."}, status=503)

