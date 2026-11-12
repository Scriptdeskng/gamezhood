from django.db import migrations
from django.utils.text import slugify


def populate_unique_slugs(apps, schema_editor):
    for model_name, source_field in (
        ("GameCategory", "name"),
        ("GameGenre", "name"),
        ("Game", "title"),
    ):
        model = apps.get_model("content", model_name)
        used_slugs = set()

        for instance in model.objects.all().order_by("pk").iterator():
            base_slug = slugify(getattr(instance, source_field)) or model_name.lower()
            slug = base_slug
            suffix = 2
            while slug in used_slugs:
                slug = f"{base_slug}-{suffix}"
                suffix += 1

            if instance.slug != slug:
                model.objects.filter(pk=instance.pk).update(slug=slug)
            used_slugs.add(slug)


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0003_alter_game_slug_alter_gamecategory_slug_and_more"),
    ]

    operations = [migrations.RunPython(populate_unique_slugs, migrations.RunPython.noop)]
