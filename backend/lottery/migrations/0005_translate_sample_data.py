from django.db import migrations


NAMES = {
    "Чаша": "Mug",
    "Тефтер": "Notebook",
    "Тест: чаша": "Test: mug",
    "Тест: тефтер": "Test: notebook",
    "Тест: чанта": "Test: bag",
    "Тест: ключодържател": "Test: keychain",
    "Тест: стикери": "Test: stickers",
    "Тест: шоколад": "Test: chocolate",
}


def translate_sample_names(apps, schema_editor):
    Prize = apps.get_model("lottery", "Prize")
    Draw = apps.get_model("lottery", "Draw")
    using = schema_editor.connection.alias
    for old, new in NAMES.items():
        Prize.objects.using(using).filter(name=old).update(name=new)
        Draw.objects.using(using).filter(prize_name=old).update(prize_name=new)


class Migration(migrations.Migration):
    dependencies = [
        ("lottery", "0004_initial_campaign"),
    ]

    operations = [
        migrations.RunPython(translate_sample_names, migrations.RunPython.noop),
    ]
