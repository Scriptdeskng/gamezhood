from django.db import migrations, models
from django.utils.text import slugify


def populate_unique_slugs(apps, schema_editor):
    for model_name, source_field in (
        ("GameCategory", "name"),
        ("GameGenre", "name"),
        ("Game", "title"),
    ):
        model = apps.get_model("content", model_name)
        used_slugs = set()

        for instance in model.objects.all().order_by("pk"):
            base_slug = slugify(getattr(instance, source_field)) or model_name.lower()
            slug = base_slug
            suffix = 2
            while slug in used_slugs:
                slug = f"{base_slug}-{suffix}"
                suffix += 1

            if instance.slug != slug:
                instance.slug = slug
                instance.save(update_fields=["slug"])
            used_slugs.add(slug)


class Migration(migrations.Migration):
    dependencies = [("content", "0001_initial")]

    operations = [
        migrations.RunPython(populate_unique_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="gamecategory",
            name="slug",
            field=models.SlugField(blank=True, unique=True),
        ),
        migrations.AlterField(
            model_name="gamegenre",
            name="slug",
            field=models.SlugField(blank=True, unique=True),
        ),
        migrations.AlterField(
            model_name="game",
            name="slug",
            field=models.SlugField(blank=True, unique=True),
        ),
    ]
