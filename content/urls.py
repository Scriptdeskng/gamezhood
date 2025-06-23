from django.urls import path
from .views import *


app_name = "core"

urlpatterns = [
    path("", homepage, name="home"),
    path("headers/", getRequestInfo, name="getRequestInfo"),
    path("echo/", echoView, name="echo"),
    path("details/<slug>/", game_detail, name="game-detail"),
    path("play-game/<slug>/", game_play, name="game-play"),
    path("category/<slug>/", game_category, name="game-category"),
    path("search/", search_view, name="search"),
    path("all-games/", all_games, name="all-games"),
    # path("run_helper/", run_helper_scripts, name="run-helper"),
 
]
