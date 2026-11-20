"""Replace the demo branches with Aziz Academy's 15 branches (in the centre's own order)."""
from django.db import migrations

BRANCHES = [
    "Niyozbosh", "Xalqabod", "Gulbahor", "Kasblar", "Kids 1", "Kids 2", "Do‘stobod", "Olmazor",
    "Chinoz", "Krasin", "Pitiletka", "Qo‘rg‘oncha", "Kids 3", "Oqqo‘rg‘on", "Qo‘shyog‘och",
]
OLD_DEMO = [
    "Chilonzor filiali", "Yunusobod filiali", "Mirzo Ulug'bek filiali",
    "Sergeli filiali", "Samarqand filiali", "Andijon filiali",
]


def forwards(apps, schema_editor):
    Branch = apps.get_model("catalog", "Branch")
    Attempt = apps.get_model("exams", "Attempt")
    for name in OLD_DEMO:
        branch = Branch.objects.filter(name=name).first()
        if branch is None:
            continue
        if Attempt.objects.filter(branch=branch).exists():
            branch.is_active = False  # keep old results readable, hide it from the entry form
            branch.sort_order = 1000
            branch.save(update_fields=["is_active", "sort_order"])
        else:
            branch.delete()
    for order, name in enumerate(BRANCHES):
        Branch.objects.update_or_create(name=name, defaults={"sort_order": order, "is_active": True})
    from apps.catalog.cache import bump_catalog_version

    bump_catalog_version()  # the entry form's cached branch list


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_one_point_per_question"),
        ("exams", "0001_initial"),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
