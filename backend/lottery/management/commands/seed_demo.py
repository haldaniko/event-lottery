from django.core.management.base import BaseCommand

from lottery.models import Prize


DEMO_PRIZES = [
    ("Test: mug", "☕", "#F0C7A0", 8),
    ("Test: notebook", "📓", "#B9D4C4", 6),
    ("Test: bag", "👜", "#D9BED9", 5),
    ("Test: keychain", "🔑", "#BFD4E6", 12),
    ("Test: stickers", "⭐", "#F2DEA0", 15),
    ("Test: chocolate", "🍫", "#D5BAA8", 10),
]


class Command(BaseCommand):
    help = "Add sample prizes only when there are no outcomes yet."

    def handle(self, *args, **options):
        if Prize.objects.exists():
            self.stdout.write("Outcomes already exist. No changes made.")
            return

        Prize.objects.bulk_create([
            Prize(name=name, emoji=emoji, color=color, quantity=quantity, sort_order=index)
            for index, (name, emoji, color, quantity) in enumerate(DEMO_PRIZES, start=1)
        ])
        self.stdout.write(self.style.SUCCESS(f"Added {len(DEMO_PRIZES)} sample prizes."))
