from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from ums.models import UserProfile


def unique_slug(instance, source, *, queryset=None):
    """Build an available slug from a model's name or title."""
    base_slug = slugify(source) or instance._meta.model_name
    slug = base_slug
    suffix = 2
    existing = queryset if queryset is not None else instance.__class__.objects.all()

    while existing.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    return slug


class GameCategory(models.Model):
    slug = models.SlugField(blank=True)
    name = models.CharField(max_length=120)

    def save(self, *args, **kwargs):
        self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class GameGenre(models.Model):
    slug = models.SlugField(blank=True)
    name = models.CharField(max_length=120)

    def save(self, *args, **kwargs):
        self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Game(models.Model):
    slug = models.SlugField(blank=True)
    title = models.CharField(max_length=120)
    category = models.ForeignKey(
        GameCategory, blank=True, null=True, on_delete=models.CASCADE
    )
    genre = models.ForeignKey(
        GameGenre, blank=True, null=True, on_delete=models.CASCADE
    )
    description = models.TextField()

    img_banner = models.ImageField(
        upload_to="gamesplash/content_images/banner/", blank=True
    )
    img_poster = models.ImageField(
        upload_to="gamesplash/content_images/poster/", blank=True
    )
    img_detail_poster = models.ImageField(
        upload_to="gamesplash/content_images/poster/", blank=True
    )
    img_detail_banner = models.ImageField(
        upload_to="gamesplash/content_images/banner/", blank=True
    )
    img_trailer = models.ImageField(
        upload_to="gamesplash/content_images/trailer/", blank=True
    )
    img_thumbnail = models.ImageField(
        upload_to="gamesplash/content_images/thumbnai/", blank=True
    )

    game_url = models.CharField(max_length=2000)

    timedelta = models.DurationField(null=True, blank=True)
    play_times = models.IntegerField(default=1)
    upload_date = models.DateField(blank=True)
    featured = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    modified = models.DateTimeField(auto_now=True)
    vendor = models.ForeignKey(
        "ums.VendorProfile", blank=True, null=True, on_delete=models.SET_NULL
    )

    def save(self, *args, **kwargs):
        self.slug = unique_slug(self, self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class PlayedGame(models.Model):
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="profile_content",
        blank=True,
        null=True,
    )
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="played_game",
        blank=True,
        null=True,
    )
    count = models.IntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user} - {self.game.title} - {self.count}"
