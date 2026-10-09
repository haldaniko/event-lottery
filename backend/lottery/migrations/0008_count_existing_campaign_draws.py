from django.db import migrations


def count_existing_campaign_draws(apps, schema_editor):
    Draw = apps.get_model("lottery", "Draw")
    using = schema_editor.connection.alias
    Draw.objects.using(using).filter(
        is_campaign_draw=False,
        prize__name__in=("No prize", "Small gift", "Keyboard", "Headphones"),
    ).update(is_campaign_draw=True)


class Migration(migrations.Migration):
    dependencies = [
        ("lottery", "0007_alter_prize_options"),
    ]

    operations = [
        migrations.RunPython(count_existing_campaign_draws, migrations.RunPython.noop),
    ]
