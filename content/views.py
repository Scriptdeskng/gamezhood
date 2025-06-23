from django.shortcuts import render, get_object_or_404, HttpResponse
from django.core.paginator import Paginator

from .models import *
from ums.models import (
    UserProfile,
)
import json
from django.http import  JsonResponse
from ums.decorators import allowed_users
from .context_processor import fetch_msisdn




from django.db.models import Q

# Create your views here.


def error404(request, exception):
    return render(request, "errors/404.html", status=404)


def error500(request):
    return render(request, "errors/500.html")


def search_view(request):
    query = request.GET.get("q", "")  # Get the 'q' parameter from the URL
    allGames = []
    if query:
        allGames = Game.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
    return render(
        request, "content/search_result.html", {"query": query, "allGames": allGames}
    )


def homepage(request):
    template = "content/index.html"

    featuredGames = Game.objects.filter(featured=True, verified=True)[:7]
    allGames = Game.objects.filter(verified=True)

    context = {"featuredGames": featuredGames, "allGames": allGames}

    return render(request, template, context)


def game_category(request, slug):
    template = "content/category.html"

    category = get_object_or_404(GameCategory, slug=slug)
    allGames = Game.objects.filter(category=category, verified=True)

    context = {"category": category, "allGames": allGames}

    return render(request, template, context)


@allowed_users
def game_detail(request, slug=None):
    the_game = get_object_or_404(Game, slug=slug)

    other_games = Game.objects.filter(verified=True).exclude(slug=the_game.slug)
    try:
        the_game.play_times += 1
        the_game.save()

        user_profile = fetch_msisdn(request)
        msisdn = user_profile["msisdn"]
        if msisdn != "" or msisdn != None:
            fetch_profile = UserProfile.objects.get(phone=msisdn)
            # create watched content
            new_watched = PlayedGame.objects.get_or_create(
                user=fetch_profile, game=the_game
            )
            new_watched.count += 1
            new_watched.save()
        else:
            pass

    except:
        pass

    template = "content/game_details.html"

    context = {
        "the_game": the_game,
        "page_title": f"Play {the_game.title}",
        "other_games": other_games,
    }

    return render(request, template, context)


def getRequestInfo(request):
    theheaders = json.dumps(dict(request.headers))
    print(theheaders)
    print(type(theheaders))
    returnData = {"MSISDN": theheaders}
    return JsonResponse(returnData)


def echoView(request):
    return HttpResponse("YES, Gamezhood IS LIVE !!")


@allowed_users
def game_play(request, slug=None):
    the_game = get_object_or_404(Game, slug=slug)

    template = "content/game_play.html"

    context = {
        "the_game": the_game,
        "page_title": f"Play {the_game.title}",
    }

    return render(request, template, context)




def all_games(request):
    template = "content/all_games.html"

    # Get all games query
    games = Game.objects.filter(verified=True)

    # Get all genres and categories for filters
    genres = GameGenre.objects.all()
    categories = GameCategory.objects.all()

    # Get filter parameters
    sort = request.GET.get("sort", "latest")
    genre_id = request.GET.get("genre", "")
    category_id = request.GET.get("category", "")

    # Apply filters
    if genre_id:
        games = games.filter(genre_id=genre_id)

    if category_id:
        games = games.filter(category_id=category_id)

    # Apply sorting
    if sort == "oldest":
        games = games.order_by("created_at")
    elif sort == "name_asc":
        games = games.order_by("title")
    elif sort == "name_desc":
        games = games.order_by("-title")
    else:  # latest
        games = games.order_by("-created_at")

    # Pagination
    paginator = Paginator(games, 12)  # Show 12 games per page
    page = request.GET.get("page")
    games = paginator.get_page(page)

    context = {
        "games": games,
        "genres": genres,
        "categories": categories,
        "sort": sort,
        "selected_genre": int(genre_id) if genre_id else None,
        "selected_category": int(category_id) if category_id else None,
    }

    return render(request, template, context)
