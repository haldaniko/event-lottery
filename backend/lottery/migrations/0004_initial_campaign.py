from django.db import migrations


OUTCOMES = (
    ("No prize", "○", "#D7DFE8", 140, False),
    ("Small gift", "🎁", "#FEC601", 50, True),
    ("Keyboard", "⌨️", "#EF5A4F", 5, True),
    ("Headphones", "🎧", "#57B5DC", 5, True),
)


def create_campaign(apps, schema_editor):
    Prize = apps.get_model("lottery", "Prize")
    using = schema_editor.connection.alias
    Prize.objects.using(using).filter(is_active=True).update(is_active=False)
    Prize.objects.using(using).bulk_create([
        Prize(
            name=name,
            emoji=emoji,
            color=color,
            quantity=quantity,
            weight=1,
            is_winning=is_winning,
            is_active=True,
            sort_order=index,
        )
        for index, (name, emoji, color, quantity, is_winning) in enumerate(OUTCOMES, 1)
    ])


class Migration(migrations.Migration):
    dependencies = [
        ("lottery", "0003_alter_draw_options_alter_prize_options_and_more"),
    ]

    operations = [
        migrations.RunPython(create_campaign, migrations.RunPython.noop),
    ]
