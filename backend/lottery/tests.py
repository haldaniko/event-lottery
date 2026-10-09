import uuid
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework.test import APITestCase

from .models import Draw, Prize


class LotteryTests(APITestCase):
    def setUp(self):
        Prize.objects.update(is_active=False)

    def test_only_active_in_stock_prizes_are_visible(self):
        available = Prize.objects.create(name="Book", quantity=2)
        Prize.objects.create(name="Out of stock", quantity=0)
        Prize.objects.create(name="Hidden", quantity=4, is_active=False)

        response = self.client.get("/api/lottery/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_remaining"], 2)
        self.assertEqual([prize["id"] for prize in response.data["prizes"]], [available.id])

    def test_draw_decrements_stock_and_cannot_repeat_last_prize(self):
        prize = Prize.objects.create(name="Book", quantity=1)

        first = self.client.post("/api/draw/", {"request_id": str(uuid.uuid4())})
        second = self.client.post("/api/draw/", {"request_id": str(uuid.uuid4())})

        prize.refresh_from_db()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["prize"]["name"], "Book")
        self.assertEqual(second.status_code, 409)
        self.assertEqual(prize.quantity, 0)
        self.assertEqual(Draw.objects.count(), 1)

    def test_repeated_request_returns_original_draw_without_using_more_stock(self):
        prize = Prize.objects.create(name="Book", quantity=2)
        request_id = str(uuid.uuid4())

        first = self.client.post("/api/draw/", {"request_id": request_id})
        prize.name = "New name"
        prize.save(update_fields=["name"])
        repeated = self.client.post("/api/draw/", {"request_id": request_id})

        prize.refresh_from_db()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.data["id"], first.data["id"])
        self.assertEqual(repeated.data["prize"], first.data["prize"])
        self.assertEqual(prize.quantity, 1)
        self.assertEqual(Draw.objects.count(), 1)

    def test_admin_session_does_not_block_public_draw(self):
        Prize.objects.create(name="Book", quantity=1)
        user = get_user_model().objects.create_user(username="admin", password="test-password")
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(user)

        response = client.post("/api/draw/", {"request_id": str(uuid.uuid4())}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Draw.objects.count(), 1)

    def test_empty_outcome_uses_one_spin_and_is_recorded_as_non_winning(self):
        empty = Prize.objects.create(name="No prize", quantity=1, is_winning=False)

        response = self.client.post("/api/draw/", {"request_id": str(uuid.uuid4())})

        empty.refresh_from_db()
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["prize"]["is_winning"])
        self.assertEqual(empty.quantity, 0)
        self.assertFalse(Draw.objects.get(pk=response.data["id"]).prize_is_winning)

    def test_visual_sector_weight_does_not_change_draw_chance(self):
        Prize.objects.create(name="No prize", quantity=1, is_winning=False)
        keyboard = Prize.objects.create(
            name="Keyboard", quantity=1, display_weight=Decimal("1.50")
        )
        sectors = self.client.get("/api/lottery/").data["prizes"]

        with patch("lottery.views.secrets.randbelow", return_value=1) as ticket:
            response = self.client.post("/api/draw/", {"request_id": str(uuid.uuid4())})

        ticket.assert_called_once_with(2)
        self.assertEqual(next(p["display_weight"] for p in sectors if p["id"] == keyboard.id), 1.5)
        self.assertEqual(response.data["prize"]["id"], keyboard.id)

    @override_settings(LOTTERY_SPIN_LIMIT=1)
    def test_spin_limit_stops_draws_even_when_stock_remains(self):
        prize = Prize.objects.create(name="Gift", quantity=2)

        first = self.client.post("/api/draw/", {"request_id": str(uuid.uuid4())})
        second = self.client.post("/api/draw/", {"request_id": str(uuid.uuid4())})
        lottery = self.client.get("/api/lottery/")

        prize.refresh_from_db()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(prize.quantity, 1)
        self.assertEqual(lottery.data["spins_used"], 1)
        self.assertEqual(lottery.data["total_remaining"], 0)
        self.assertEqual(lottery.data["prizes"], [])

    @override_settings(
        LOTTERY_SPIN_LIMIT=1,
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        },
    )
    def test_admin_can_cancel_accidental_draw_once_and_restore_spin(self):
        prize = Prize.objects.create(name="No prize", quantity=2, is_winning=False)
        draw_response = self.client.post("/api/draw/", {"request_id": str(uuid.uuid4())})
        draw_id = draw_response.data["id"]
        user = get_user_model().objects.create_superuser(
            username="organizer", email="organizer@example.com", password="test-password"
        )
        self.client.force_login(user)
        action_data = {"action": "cancel_selected_draws", "_selected_action": [draw_id], "index": "0"}

        confirmation = self.client.post("/admin/lottery/draw/", action_data)
        cancelled = self.client.post(
            "/admin/lottery/draw/", {**action_data, "confirm": "yes", "reason": "Accidental second spin"}
        )
        repeated = self.client.post("/admin/lottery/draw/", {**action_data, "confirm": "yes"})

        prize.refresh_from_db()
        draw = Draw.objects.get(pk=draw_id)
        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, "Confirm draw cancellation")
        self.assertEqual(cancelled.status_code, 302)
        self.assertEqual(repeated.status_code, 302)
        self.assertEqual(prize.quantity, 2)
        self.assertIsNotNone(draw.voided_at)
        self.assertEqual(draw.voided_by, user)
        self.assertEqual(draw.void_reason, "Accidental second spin")
        self.assertEqual(self.client.get("/api/lottery/").data["spins_used"], 0)

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        },
    )
    def test_category_admin_shows_stock_and_spin_summary(self):
        Prize.objects.create(name="No prize", quantity=140, is_winning=False)
        user = get_user_model().objects.create_superuser(
            username="organizer", email="organizer@example.com", password="test-password"
        )
        self.client.force_login(user)

        response = self.client.get("/admin/lottery/prize/", follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Total spins")
        self.assertContains(response, "Category stock")
        self.assertContains(response, "No prize")


