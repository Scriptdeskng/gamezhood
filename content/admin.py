from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import *

# Register your models here.


# admin.site.register(ContentCategory)##
admin.site.register(GameGenre)
# admin.site.register(Game)
admin.site.register(GameCategory)
admin.site.register(PlayedGame)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "category",
        "genre",
        "description",
        "game_url",
        "timedelta",
        "play_times",
        "upload_date",
    ]
