from django.shortcuts import render, get_object_or_404, redirect, HttpResponse
from django.core.paginator import Paginator

from .models import *
from ums.models import (
    CampaignTracker,
    CampaignDuplicate,
    UserProfile,
    UserSubscribtion,
)
import json
from django.http import Http404, JsonResponse
from ums.decorators import allowed_users
from .context_processor import fetch_msisdn
from ums import choices as ums_choices
from dateutil.relativedelta import relativedelta

from django.utils import timezone

from django.utils.crypto import get_random_string

import string, random

from ums.tasks import handle_occurence, handle_remarketing
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


# @allowed_users
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
    # print(returnData)
    return JsonResponse(returnData)


def echoView(request):
    return HttpResponse("YES, Gamezhood IS LIVE !!")


# @allowed_users
def game_play(request, slug=None):
    the_game = get_object_or_404(Game, slug=slug)

    template = "content/game_play.html"

    context = {
        "the_game": the_game,
        "page_title": f"Play {the_game.title}",
    }

    return render(request, template, context)


def run_helper_scripts(request):
    try:
        allGames = Game.objects.filter(verified=True).all()
        for game in allGames:
            url = game.game_url
            print("old url", url)
            # new_url = url.replace(
            #     "https://games.cloudintegratedinc.com", "https://scriptdesk.dev/games"
            # )
            game.game_url = url.replace(
                "https://games.cloudintegratedinc.com", "https://scriptdesk.dev/games"
            )
            game.save()
            print("new url", game.game_url)
    except Exception as e:
        print("exception", e)

    return HttpResponse(200)


def neth_campaign_url(request):
    try:
        partner = request.GET.get("partner", None)
        click_id = request.GET.get("clickid", None)
        telco = request.GET.get("telco", None)

        # new_promo_hit = CampaignTracker.objects.create(
        #     click_id=click_id, provider=ums_choices.CampaignProvider.NETH.value
        # )
        try:
            new_promo_hit = CampaignTracker.objects.get(
                click_id=click_id, provider=ums_choices.CampaignProvider.NETH.value
            )
        except CampaignTracker.DoesNotExist:
            new_promo_hit = CampaignTracker.objects.create(
                click_id=click_id, provider=ums_choices.CampaignProvider.NETH.value
            )
        except CampaignTracker.MultipleObjectsReturned:
            new_promo_hit = CampaignTracker.objects.filter(
                click_id=click_id, provider=ums_choices.CampaignProvider.NETH.value
            ).last()

        if partner:
            new_promo_hit.partner = partner
        if telco:
            new_promo_hit.telco = telco

        try:
            req_data = json.loads(request.body)

            new_promo_hit.req_body = f"{req_data}"
        except:
            pass
        new_promo_hit.save()

        if "Msisdn" in request.headers:
            msisdn = request.headers["Msisdn"]
            if msisdn.startswith("0") and len(msisdn) == 11:
                msisdn = msisdn.replace("0", "234", 1)
            new_promo_hit.msisdn = msisdn
            new_promo_hit.save()

            handle_occurence.delay(new_promo_hit.id)
            # check if user already exist in the system
            user_prof_qs = UserProfile.objects.filter(phone=msisdn)
            if user_prof_qs.exists():
                user_prof = user_prof_qs.first()
                print(f"{user_prof} exists")
                # check if user has active subscribtion
                now = timezone.now()
                one_month_ago = now - relativedelta(months=1)
                one_day_ago = now - relativedelta(hours=24)
                # user deactivated active subscribtion
                user_sub = UserSubscribtion.objects.filter(user=user_prof).first()
                if user_sub.ends_date and user_sub.ends_date <= one_day_ago:
                    print(f"debugging sub less than a month for {msisdn}")
                    try:
                        duplicate, _ = CampaignDuplicate.objects.get_or_create(
                            msisdn=msisdn,
                            provider=ums_choices.CampaignProvider.NETH.value,
                        )
                        duplicate.remarketed = True
                        duplicate.last_subscribtion = user_sub.ends_date
                        duplicate.save()
                    except Exception as ex:
                        print(ex)
                        pass
                    # redirect to secured D
                    new_promo_hit.is_convertable = False
                    new_promo_hit.save()
                    ### redirect as organic source
                    res = get_random_string(length=48)
                    traffic_source = "Organic Search"
                    redirect_url = f"http://ng-app.com/HML/GameSplash-24-No-23410220000027084-web?trfsrc={traffic_source}&trxId={res}"
                    return redirect(redirect_url)

                else:
                    return redirect("core:home")

        res = get_random_string(length=48)

        traffic_source = f"Traffic Company"
        redirect_url = f"http://ng-app.com/HML/GameSplash-24-No-23410220000027084-web?trfsrc={traffic_source}&trxId={res}"
        return redirect(redirect_url)

    except Exception as ex:
        print(ex)
        return redirect("core:home")


def mobplus_campaign_url_deprecated(request):
    try:
        partner = request.GET.get("partner", None)
        click_id = request.GET.get("clickid", None)
        telco = request.GET.get("telco", None)
        pubid = request.GET.get("pubid", None)
        amt = request.GET.get("amt", None)

        # new_promo_hit = CampaignTracker.objects.create(
        #     click_id=click_id, provider=ums_choices.CampaignProvider.MOBPLUS.value
        # )

        try:
            new_promo_hit = CampaignTracker.objects.get(
                click_id=click_id, provider=ums_choices.CampaignProvider.MOBPLUS.value
            )
        except CampaignTracker.DoesNotExist:
            new_promo_hit = CampaignTracker.objects.create(
                click_id=click_id, provider=ums_choices.CampaignProvider.MOBPLUS.value
            )
        except CampaignTracker.MultipleObjectsReturned:
            new_promo_hit = CampaignTracker.objects.filter(
                click_id=click_id, provider=ums_choices.CampaignProvider.MOBPLUS.value
            ).last()

        if partner:
            new_promo_hit.partner = partner
        if telco:
            new_promo_hit.telco = telco

        if pubid:
            new_promo_hit.pubid = pubid

        if amt:
            new_promo_hit.amt = amt

        new_promo_hit.currency = "USD"

        try:
            req_data = json.loads(request.body)

            new_promo_hit.req_body = f"{req_data}"
        except:
            pass
        new_promo_hit.save()

        if "Msisdn" in request.headers:
            msisdn = request.headers["Msisdn"]
            if msisdn.startswith("0") and len(msisdn) == 11:
                msisdn = msisdn.replace("0", "234", 1)

            new_promo_hit.msisdn = msisdn
            new_promo_hit.save()

            handle_occurence.delay(new_promo_hit.id)

            user_prof_qs = UserProfile.objects.filter(phone=msisdn)
            if user_prof_qs.exists():
                user_prof = user_prof_qs.first()
                # check if user has active subscribtion
                now = timezone.now()
                one_month_ago = now - relativedelta(months=1)
                one_day_ago = now - relativedelta(hours=24)
                # user deactivated active subscribtion
                user_sub = UserSubscribtion.objects.filter(user=user_prof).first()
                if user_sub.ends_date and user_sub.ends_date <= one_day_ago:
                    try:

                        duplicate, _ = CampaignDuplicate.objects.get_or_create(
                            msisdn=msisdn,
                            provider=ums_choices.CampaignProvider.MOBPLUS.value,
                        )
                        duplicate.remarketed = True
                        duplicate.last_subscribtion = user_sub.ends_date
                        duplicate.save()
                    except Exception as ex:
                        print(ex)
                        pass
                    # redirect to secured D
                    new_promo_hit.is_convertable = False
                    new_promo_hit.save()
                    ### redirect as organic source
                    res = get_random_string(length=48)
                    traffic_source = "Organic Search"
                    redirect_url = f"http://ng-app.com/HML/GameSplash-24-No-23410220000027084-web?trfsrc={traffic_source}&trxId={res}"
                    return redirect(redirect_url)

                else:
                    return redirect("core:home")

        res = get_random_string(length=48)

        traffic_source = f"MobPlus Cloud"

        redirect_url = f"http://ng-app.com/HML/GameSplash-24-No-23410220000027084-web?trfsrc={traffic_source}&trxId={res}"

        return redirect(redirect_url)
    except Exception as ex:
        print(ex)
        return redirect("core:home")


def mobplus_campaign_url(request):
    try:
        partner = request.GET.get("partner", None)
        click_id = request.GET.get("clickid", None)
        telco = request.GET.get("telco", None)
        pubid = request.GET.get("pubid", None)

        if "Msisdn" in request.headers:
            msisdn = request.headers["Msisdn"]
            if msisdn.startswith("0") and len(msisdn) == 11:
                msisdn = msisdn.replace("0", "234", 1)

            new_promo_hit = None

            new_promo_hit_qs = CampaignTracker.objects.filter(
                click_id=click_id, provider=ums_choices.CampaignProvider.MOBPLUS.value
            )

            if new_promo_hit_qs.exists():
                new_promo_hit = new_promo_hit_qs.last()
            else:
                new_promo_hit = CampaignTracker.objects.create(
                    click_id=click_id,
                    msisdn=msisdn,
                    provider=ums_choices.CampaignProvider.MOBPLUS.value,
                    currency="USD",
                )

            if partner:
                new_promo_hit.partner = partner
            if telco:
                new_promo_hit.telco = telco
            if pubid:
                new_promo_hit.pubid = pubid

            unique_sub_ref = get_random_string(length=48)

            user_prof_qs = UserProfile.objects.filter(phone=msisdn)
            if user_prof_qs.exists():
                user_prof = user_prof_qs.first()
                # check if user has active subscribtion
                now = timezone.now()
                one_month_ago = now - relativedelta(months=2)
                one_day_ago = now - relativedelta(hours=24)
                # user deactivated active subscribtion
                user_sub = UserSubscribtion.objects.filter(user=user_prof).first()
                if user_sub.ends_date and user_sub.ends_date <= one_day_ago:

                    handle_remarketing.apply_async(
                        args=[msisdn, ums_choices.CampaignProvider.MOBPLUS.value],
                        countdown=120,
                    )

                    # redirect to secured D
                    new_promo_hit.is_convertable = False

                    ### redirect as organic source

                    traffic_source = "Organic Search"
                    redirect_url = f"http://ng-app.com/HML/GameSplash-24-No-23410220000027084-web?trfsrc={traffic_source}&trxId={unique_sub_ref}"
                    return redirect(redirect_url)
                else:
                    return redirect("core:home")

            new_promo_hit.save()
            handle_occurence.apply_async(args=[new_promo_hit.id], countdown=120)
            traffic_source = "MobPlus Cloud"

            redirect_url = f"http://ng-app.com/HML/GameSplash-24-No-23410220000027084-web?trfsrc={traffic_source}&trxId={unique_sub_ref}"
            return redirect(redirect_url)
        else:
            return redirect("core:home")
    except Exception:
        return redirect("core:home")


def mobedia_campaign_url(request):
    try:

        click_id = request.GET.get("clickid", None)
        telco = request.GET.get("telco", None)

        try:
            new_promo_hit = CampaignTracker.objects.get(
                click_id=click_id, provider=ums_choices.CampaignProvider.MOBIDEA.value
            )
        except CampaignTracker.DoesNotExist:
            new_promo_hit = CampaignTracker.objects.create(
                click_id=click_id, provider=ums_choices.CampaignProvider.MOBIDEA.value
            )
        except CampaignTracker.MultipleObjectsReturned:
            new_promo_hit = CampaignTracker.objects.filter(
                click_id=click_id, provider=ums_choices.CampaignProvider.MOBIDEA.value
            ).last()

        if telco:
            new_promo_hit.telco = telco

        new_promo_hit.currency = "USD"

        try:
            req_data = json.loads(request.body)

            new_promo_hit.req_body = f"{req_data}"
        except:
            pass

        unique_sub_ref = get_random_string(length=48)

        if "Msisdn" in request.headers:
            msisdn = request.headers["Msisdn"]
            if msisdn.startswith("0") and len(msisdn) == 11:
                msisdn = msisdn.replace("0", "234", 1)

            new_promo_hit.msisdn = msisdn

            user_prof_qs = UserProfile.objects.filter(phone=msisdn)
            if user_prof_qs.exists():
                user_prof = user_prof_qs.first()
                # check if user has active subscribtion
                now = timezone.now()
                one_month_ago = now - relativedelta(months=2)
                one_day_ago = now - relativedelta(hours=24)
                # user deactivated active subscribtion
                user_sub = UserSubscribtion.objects.filter(user=user_prof).first()
                if user_sub.ends_date and user_sub.ends_date <= one_day_ago:
                    try:

                        duplicate, _ = CampaignDuplicate.objects.get_or_create(
                            msisdn=msisdn,
                            provider=ums_choices.CampaignProvider.MOBIDEA.value,
                        )
                        duplicate.remarketed = True
                        duplicate.last_subscribtion = user_sub.ends_date
                        duplicate.save()
                    except Exception as ex:
                        print(ex)
                        pass

                    # redirect to secured D
                    new_promo_hit.is_convertable = False
                    new_promo_hit.save()
                    ### redirect as organic source

                    traffic_source = "Organic Search"
                    redirect_url = f"http://ng-app.com/HML/GameSplash-24-No-23410220000027084-web?trfsrc={traffic_source}&trxId={unique_sub_ref}"
                    return redirect(redirect_url)

                else:
                    return redirect("core:home")

        new_promo_hit.save()
        handle_occurence.delay(new_promo_hit.id)
        traffic_source = "MOBEDIA"
        redirect_url = f"http://ng-app.com/HML/GameSplash-24-No-23410220000027084-web?trfsrc={traffic_source}&trxId={unique_sub_ref}"
        return redirect(redirect_url)

    except Exception:

        return redirect("core:home")


def angel_media_campaign_url(request):
    try:

        click_id = request.GET.get("clickid", None)
        telco = request.GET.get("telco", None)

        try:
            new_promo_hit = CampaignTracker.objects.get(
                click_id=click_id,
                provider=ums_choices.CampaignProvider.ANGELMEDIA.value,
            )
        except CampaignTracker.DoesNotExist:
            new_promo_hit = CampaignTracker.objects.create(
                click_id=click_id,
                provider=ums_choices.CampaignProvider.ANGELMEDIA.value,
            )
        except CampaignTracker.MultipleObjectsReturned:
            new_promo_hit = CampaignTracker.objects.filter(
                click_id=click_id,
                provider=ums_choices.CampaignProvider.ANGELMEDIA.value,
            ).last()

        if telco:
            new_promo_hit.telco = telco

        new_promo_hit.currency = "USD"

        try:
            req_data = json.loads(request.body)

            new_promo_hit.req_body = f"{req_data}"
        except:
            pass

        unique_sub_ref = get_random_string(length=48)

        if "Msisdn" in request.headers:
            msisdn = request.headers["Msisdn"]
            if msisdn.startswith("0") and len(msisdn) == 11:
                msisdn = msisdn.replace("0", "234", 1)

            new_promo_hit.msisdn = msisdn

            user_prof_qs = UserProfile.objects.filter(phone=msisdn)
            if user_prof_qs.exists():
                user_prof = user_prof_qs.first()
                # check if user has active subscribtion
                now = timezone.now()
                one_month_ago = now - relativedelta(months=2)
                # user deactivated active subscribtion
                one_day_ago = now - relativedelta(hours=24)
                user_sub = UserSubscribtion.objects.filter(user=user_prof).first()
                if user_sub.ends_date and user_sub.ends_date <= one_day_ago:
                    try:

                        duplicate, _ = CampaignDuplicate.objects.get_or_create(
                            msisdn=msisdn,
                            provider=ums_choices.CampaignProvider.ANGELMEDIA.value,
                        )
                        duplicate.remarketed = True
                        duplicate.last_subscribtion = user_sub.ends_date
                        duplicate.save()
                    except Exception as ex:
                        print(ex)
                        pass

                    # redirect to secured D
                    new_promo_hit.is_convertable = False
                    new_promo_hit.save()
                    ### redirect as organic source

                    traffic_source = "Organic Search"
                    redirect_url = f"http://ng-app.com/HML/GameSplash-24-No-23410220000027084-web?trfsrc={traffic_source}&trxId={unique_sub_ref}"
                    return redirect(redirect_url)

                else:
                    return redirect("core:home")

        new_promo_hit.save()
        handle_occurence.delay(new_promo_hit.id)
        traffic_source = "Janx"
        # traffic_source = "ANGEL MEDIA"
        redirect_url = f"http://ng-app.com/HML/GameSplash-24-No-23410220000027084-web?trfsrc={traffic_source}&trxId={unique_sub_ref}"
        return redirect(redirect_url)

    except Exception:

        return redirect("core:home")


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
