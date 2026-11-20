from django.db import migrations


def one_point(apps, schema_editor):
    """Every question is worth 1 point (stage 2 used to be 2 points per question)."""
    Question = apps.get_model("catalog", "Question")
    if Question.objects.filter(stage=2, points=2).update(points=1):
        from apps.catalog.cache import bump_catalog_version

        bump_catalog_version()  # cached question pools still carry the old points


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_academic_bank")]
    operations = [migrations.RunPython(one_point, migrations.RunPython.noop)]
