from decimal import Decimal

from django.db import migrations


def enlarge_rare_sectors(apps, schema_editor):
    Prize = apps.get_model("lottery", "Prize")
    Prize.objects.using(schema_editor.connection.alias).filter(
        name__in=("Keyboard", "Headphones"),
    ).update(display_weight=Decimal("1.50"))


class Migration(migrations.Migration):
    dependencies = [
        ("lottery", "0009_prize_display_weight"),
    ]

    operations = [
        migrations.RunPython(enlarge_rare_sectors, migrations.RunPython.noop),
    ]
