from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
from balldontlie import BalldontlieAPI
from fastapi import Query
from fastapi.staticfiles import StaticFiles


api = BalldontlieAPI(api_key="YOUR_API_KEY")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/allplayers", response_class=HTMLResponse)
def get_all_players(request: Request, count: int = Query(100, ge=25, le=100)):
    players_raw = api.nba.players.list(per_page=count)

    # Extract only needed fields for each player
    players_filtered = []
    for player in players_raw.data:
        players_filtered.append({
            "player_id": player.id,
            "player_fname": player.first_name,
            "player_lname": player.last_name,
            "player_team_id": player.team.id ,
            "player_team_name": player.team.full_name
        })

    return templates.TemplateResponse("players.html", {"request": request, "players": players_filtered})

@app.get("/games/{season}", response_class=HTMLResponse)
def check_season(request: Request, season: int):
    api_url = f"https://api.balldontlie.io/v1/games?seasons[]={season}&per_page=100"
    api_key = "3ddb3105-2cf0-43cf-998f-d342d58e4f79"

    headers = {"Authorization": f"{api_key}"}

    response = requests.get(api_url, headers=headers)
    results = []

    if response.status_code == 200:
        games = response.json().get("data", [])

        for game in games:
            home_team = game["home_team"]["full_name"]
            visitor_team = game["visitor_team"]["full_name"]
            home_score = game["home_team_score"]
            visitor_score = game["visitor_team_score"]
            date = game["date"]

            if home_score > visitor_score:
                winner = home_team
                margin = home_score - visitor_score
            else:
                winner = visitor_team
                margin = visitor_score - home_score

            results.append({
                "date": date,
                "winner": winner,
                "margin": margin,
                "home_team": home_team,
                "visitor_team": visitor_team,
                "home_score": home_score,
                "visitor_score": visitor_score
            })

    return templates.TemplateResponse("games.html", {"request": request, "season": season, "game_results": results})

@app.get("/team-averages/{season}", response_class=HTMLResponse)
def team_averages(request: Request, season: int):
    api_url = f"https://api.balldontlie.io/v1/games?seasons[]={season}&per_page=100"
    headers = {"Authorization": "3ddb3105-2cf0-43cf-998f-d342d58e4f79"}

    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        return {"error": "Failed to fetch games"}

    data = response.json().get("data", [])

    team_stats = {}

    for game in data:
        home_team = game["home_team"]["full_name"]
        visitor_team = game["visitor_team"]["full_name"]
        home_score = game["home_team_score"]
        visitor_score = game["visitor_team_score"]

        # Update stats for home team
        if home_team not in team_stats:
            team_stats[home_team] = {"total_points": 0, "games_played": 0, "wins": 0}
        team_stats[home_team]["total_points"] += home_score
        team_stats[home_team]["games_played"] += 1
        if home_score > visitor_score:
            team_stats[home_team]["wins"] += 1

        # Update stats for visitor team
        if visitor_team not in team_stats:
            team_stats[visitor_team] = {"total_points": 0, "games_played": 0, "wins": 0}
        team_stats[visitor_team]["total_points"] += visitor_score
        team_stats[visitor_team]["games_played"] += 1
        if visitor_score > home_score:
            team_stats[visitor_team]["wins"] += 1

    # Create structured list
    avg_scores = []
    for team, stats in team_stats.items():
        avg = stats["total_points"] / stats["games_played"]
        win_pct = (stats["wins"] / stats["games_played"]) * 100
        avg_scores.append({
            "team": team,
            "games_played": stats["games_played"],
            "total_score": stats["total_points"],
            "average_score": round(avg, 2),
            "wins": stats["wins"],
            "win_pct": round(win_pct, 2)
        })

    # Sort by average score
    avg_scores.sort(key=lambda x: x["average_score"], reverse=True)

    return templates.TemplateResponse("team_averages.html", {
        "request": request,
        "season": season,
        "avg_scores": avg_scores
    })


