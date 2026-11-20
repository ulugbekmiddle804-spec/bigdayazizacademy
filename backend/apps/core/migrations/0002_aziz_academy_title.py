from django.db import migrations, models


def rename(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    SiteSettings.objects.filter(site_title="Online Test Platformasi").update(site_title="Aziz Academy")


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="site_title",
            field=models.CharField("Sayt nomi", max_length=120, default="Aziz Academy"),
        ),
        migrations.RunPython(rename, migrations.RunPython.noop),
    ]
