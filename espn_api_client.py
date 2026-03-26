"""
ESPN API client for fetching NCAA basketball team statistics and historical data.

Provides functions to search for teams by name and retrieve per-team statistics
(scoring, defence, win/loss record) from the public ESPN college basketball API.
No API key is required.

Endpoints used:
  - Teams list  : GET /teams?limit=1000
  - Statistics  : GET /teams/{id}/statistics
  - Record      : GET /teams/{id}/record
"""

import asyncio
import json
from difflib import SequenceMatcher
from pathlib import Path
from sqlite3 import Date
from typing import Optional

import requests


CACHE_DIR = Path(__file__).resolve().parent / "espn_cache"
CACHE_DIR.mkdir(exist_ok=True)


class EspnApiClient:
    """
    Client for fetching NCAA basketball team data from the ESPN API.

    This client provides methods to fetch and parse team statistics and records,
    with caching to reduce redundant network calls.  The main entry point is
    :func:`get_team_data`, which returns a normalized stats dict for a given
    team name.

    Example usage::

        client = EspnApiClient()
        team_data = client.get_team_data("Duke")
        print(team_data["win_pct"])
    """

    BASE_URL = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball"

    def __init__(self, year: Optional[int] = None, force_refresh: bool = False):
        self.year = year or Date.today().year
        self.force_refresh = force_refresh
        self.cache_dir = CACHE_DIR / f"season_{self.year}"
        self.teams_cache_path = self.cache_dir / "espn_teams.json"
        self.unresolved_teams_cache_path = self.cache_dir / "espn_unresolved_teams.json"
        self.teams_cache_dir = self.cache_dir / "espn_teams_cache"
        self.stats_cache_dir = self.cache_dir / "espn_stats_cache"
        self.record_cache_dir = self.cache_dir / "espn_record_cache"

        self._setup_cache()

        self.url = f"{self.BASE_URL}/seasons/{self.year}"

    def _setup_cache(self):
        """Set up cache directories and paths."""
        self.cache_dir.mkdir(exist_ok=True)
        self.teams_cache_dir.mkdir(exist_ok=True)
        self.stats_cache_dir.mkdir(exist_ok=True)
        self.record_cache_dir.mkdir(exist_ok=True)

        if self.force_refresh:
            for path in [self.teams_cache_path, self.unresolved_teams_cache_path, self.teams_cache_dir, self.stats_cache_dir, self.record_cache_dir]:
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    for item in path.iterdir():
                        if item.is_file():
                            item.unlink()

    def get_team(self, team_id: str) -> Optional[dict]:
        """Fetch team data by ESPN team ID."""
        cache_path = self.teams_cache_dir / f"{team_id}.json"
        if cache_path.exists():
            try:
                team = json.loads(
                    cache_path.read_text(encoding="utf-8"))
                return team
            except Exception:
                # Fall back to network call if cache can't be read/parsed.
                pass

        url = f"{self.BASE_URL}/teams/{team_id}"
        response = requests.get(url, timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        try:
            cache_path.write_text(json.dumps(
                data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass  # We don't want caching failures to impact the caller.
        return data

    def _resolve_ref(self, res: dict) -> Optional[dict]:
        """Fetch data from an ESPN API reference URL."""
        ref = res.get("$ref")
        if not ref:
            return None
        url = ref.replace("http", "https")  # Ensure HTTPS
        response = requests.get(url, timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def get_season(self) -> dict:
        """Fetch season overview data."""
        url = f"{self.url}/seasons/{self.year}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    def _resolve_team_ref(self, ref: dict) -> Optional[dict]:
        """Resolve a team reference."""
        team = self._resolve_ref(ref)  # Ensure the team data is cached
        if team is None:
            return None
        cache_path = self.teams_cache_dir / f"{team.get('id')}.json"
        try:
            cache_path.write_text(json.dumps(
                team, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass  # We don't want caching failures to impact the caller.

        return team

    def _save_team_cache(self):
        """Save the full teams list to cache."""
        teams = [json.loads(f.read_text())
                 for f in self.teams_cache_dir.glob("*.json")]
        try:
            self.teams_cache_path.write_text(
                json.dumps(teams, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass  # We don't want caching failures to impact the caller.
        return teams

    def _load_teams_sync(self):
        try:
            teams = json.loads(
                self.unresolved_teams_cache_path.read_text(encoding="utf-8"))
        except Exception:
            return None  # Cache not available or unreadable

        for team in teams:
            self._resolve_team_ref(team)

        self._save_team_cache()

    async def _load_teams_async(self):
        """Asynchronously load the full teams list from the ESPN API."""
        try:
            teams = json.loads(
                self.unresolved_teams_cache_path.read_text(encoding="utf-8"))
        except Exception:
            return None  # Cache not available or unreadable

        async with asyncio.TaskGroup() as tg:
            for team in teams:
                tg.create_task(self._resolve_team_ref(team))

        self._save_team_cache()

    def fetch_all_teams(self, background: Optional[bool] = False):
        """Fetch a list of all NCAA basketball teams for the given year."""
        url = f"{self.url}/teams"
        limit_response = requests.get(url, params={"limit": 1}, timeout=10)
        limit_response.raise_for_status()
        limit = limit_response.json().get("count", 0)

        response = requests.get(url, params={"limit": limit}, timeout=10)
        response.raise_for_status()
        data = response.json()

        try:
            self.unresolved_teams_cache_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass  # We don't want caching failures to impact the caller.

        if background:
            asyncio.create_task(self._load_teams_async())
        else:
            self._load_teams_sync()

    def get_all_teams(self) -> list:
        """Fetch all NCAA Division I"""

        if self.teams_cache_path.exists():
            try:
                return json.loads(self.teams_cache_path.read_text(encoding="utf-8"))
            except Exception:
                # Fall back to network call if cache can't be read/parsed.
                pass
        self.fetch_all_teams()
        try:
            return json.loads(self.teams_cache_path.read_text(encoding="utf-8"))
        except Exception:
            # Fall back to network call if cache can't be read/parsed.
            pass
        return []

    def get_team_statistics(self, team_id: str) -> Optional[dict]:
        """Fetch season statistics for a single ESPN team by team ID."""
        cache_path = self.stats_cache_dir / f"{team_id}.json"
        if cache_path.exists():
            try:
                return json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                # Fall back to network call if cache can't be read/parsed.
                pass

        team = self.get_team(team_id)
        if team is None:
            return None
        stats_ref = team.get("statistics", {})
        if stats_ref is None:
            return None
        stats_data = self._resolve_ref(stats_ref)

        if stats_data is None:
            return None

        try:
            cache_path.write_text(json.dumps(
                stats_data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass  # We don't want caching failures to impact the caller.

        return stats_data

    def get_team_record(self, team_id: str) -> Optional[dict]:
        """Fetch season win/loss record for a single ESPN team by team ID."""
        cache_path = self.record_cache_dir / f"{team_id}.json"
        if cache_path.exists():
            try:
                return json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                # Fall back to network call if cache can't be read/parsed.
                pass

        team = self.get_team(team_id)
        if team is None:
            return None
        record_ref = team.get("record", {})
        if record_ref is None:
            return None
        record_data = self._resolve_ref(record_ref)

        if record_data is None:
            return None

        try:
            cache_path.write_text(json.dumps(
                record_data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass  # We don't want caching failures to impact the caller.

        return record_data

    def get_team_by_name(self, name: str) -> Optional[dict]:
        """Locate a team in the ESPN dataset by display name."""
        teams = self.get_all_teams()
        name_lower = name.lower()
        best_match: Optional[dict] = None
        best_score: float = 0.0

        team_match = None

        for team in teams:
            candidates = [
                team.get("displayName", ""),
                team.get("shortDisplayName", ""),
                team.get("name", ""),
                team.get("nickname", ""),
                team.get("abbreviation", ""),
            ]
            for candidate in candidates:
                if not candidate:
                    continue
                if candidate.lower() == name_lower:
                    team_match = team  # exact match — stop immediately
                    break
                score = SequenceMatcher(
                    None, name_lower, candidate.lower()).ratio()
                if score > best_score:
                    best_score = score
                    best_match = team

        team_match = best_match if best_score >= 0.6 else None
        team_id = team_match.get("id") if team_match else None
        if team_match is None or team_id is None:
            print(
                f"  Warning: No close match found for '{name}' in ESPN database.")
            return None
        # cache the matched team
        return self.get_team(team_id)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def parse_statistics(stats_data: dict) -> dict:
    """
    Flatten ESPN statistics response into a `{stat_name: float}` dict.

    The ESPN response nests stats inside `results.stats.categories[*].stats`.
    This function extracts every leaf `{name, value}` pair regardless of
    category.

    Args:
        stats_data: Raw dict returned by `fetch_team_statistics`.

    Returns:
        dict mapping stat name strings to float values.
    """
    parsed: dict = {}
    categories = (
        stats_data
        .get("results", {})
        .get("stats", {})
        .get("categories", [])
    )
    for category in categories:
        for stat in category.get("stats", []):
            stat_name = stat.get("name", "")
            raw_value = stat.get("value")
            if stat_name:
                try:
                    parsed[stat_name] = float(
                        raw_value) if raw_value is not None else 0.0
                except (TypeError, ValueError):
                    parsed[stat_name] = 0.0
    return parsed


def parse_record(overview_data: dict) -> dict:
    """
    Extract wins, losses, and win percentage from an ESPN overview response.

    Looks for the "total" item inside `overview_data["team"]["record"]["items"]`.

    Args:
        overview_data: Raw dict returned by `fetch_team_record`.

    Returns:
        dict with keys "wins" (float), "losses" (float),
        "win_pct" (float in [0, 1]).  Defaults to 0.5 win_pct when the record
        cannot be parsed.
    """
    record_data = overview_data.get("team", {}).get("record", {})
    for item in record_data.get("items", []):
        if item.get("type") == "total":
            stats = {s["name"]: s.get("value", 0)
                     for s in item.get("stats", [])}
            return get_win_data(stats)

    return {"wins": 0.0, "losses": 0.0, "win_pct": 0.5}


def get_win_data(stats: dict) -> dict:
    """
    Extract the win percentage from a stats dict, defaulting to 0.5 if not found.

    Args:
        stats: dict of statistics as returned by :func:`parse_statistics`.
    Returns:
        dict with keys ``"wins"``, ``"losses"``, and ``"win_pct"`` (float in [0, 1]).

    """
    win_pct = stats.get("winPercent")

    wins = float(stats.get("winPercent", 0))
    losses = float(stats.get("losses", 0))
    games = wins + losses
    win_pct = win_pct if win_pct is not None else (
        wins / games if games > 0 else 0.5)
    return {"wins": wins, "losses": losses, "win_pct": win_pct}


def get_point_data(stats: dict) -> dict:
    """
    Extract the points per game and points allowed per game from a stats dict.

    Args:
        stats: dict of statistics as returned by :func:`parse_statistics`.
    Returns:
        dict with keys ``"pts_per_game"`` and ``"pts_allowed_per_game"

    """
    pts_per_game = float(stats.get("avgPointsFor", 70.0))
    pts_allowed_per_game = float(stats.get("avgPointsAgainst", 70.0))
    return {"pts_per_game": pts_per_game, "pts_allowed_per_game": pts_allowed_per_game}


# ---------------------------------------------------------------------------
# High-level entry point
# ---------------------------------------------------------------------------

_client_instance: Optional[EspnApiClient] = None


def get_team_data(team_name: str, year: Optional[int] = None, force_refresh: bool = False) -> Optional[dict]:
    """
    Return a normalised stats dict for *team_name*, or *None* on failure.

    Fetches and combines team statistics and win/loss record.  Any individual
    API call that fails is silently swallowed so partial data is still usable.

    Args:
        team_name: Human-readable team name as it appears in the bracket CSV.
        year: Optional year for which to fetch team data.
        force_refresh: Whether to force refresh of cached data.

    Returns:
        dict with keys:

        * ``"id"``                   — ESPN team id string
        * ``"name"``                 — ESPN display name
        * ``"win_pct"``              — float in [0, 1]
        * ``"scoring_margin"``       — (pts/g scored) − (pts/g allowed)
        * ``"pts_per_game"``         — float
        * ``"pts_allowed_per_game"`` — float

        *None* is returned when the team cannot be matched in ESPN's database.
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = EspnApiClient(
            year=year, force_refresh=force_refresh)
    client = _client_instance
    team = client.get_team_by_name(team_name)
    if team is None:
        return None

    team_id = str(team.get("id"))

    # Defaults used when an individual API call fails
    pts_per_game: float = 70.0
    pts_allowed_per_game: float = 70.0
    win_pct: float = 0.5

    try:
        overview_data = client.get_team_record(team_id)
        if overview_data is None:
            return None
        record = parse_record(overview_data)
        win_pct = record["win_pct"]
        pts_per_game = record["pts_per_game"]
        pts_allowed_per_game = record["pts_allowed_per_game"]
    except Exception:
        pass  # fall back to default

    return {
        "id": team_id,
        "name": team.get("displayName", team_name),
        "win_pct": win_pct,
        "scoring_margin": pts_per_game - pts_allowed_per_game,
        "pts_per_game": pts_per_game,
        "pts_allowed_per_game": pts_allowed_per_game,
    }


def fetch_all_teams(year: Optional[int] = None, force_refresh: bool = False) -> list:
    """
    Fetch and return a list of all NCAA basketball teams for the given year.

    Each team is represented as a dict with keys "id" and "name".

    Args:
        year: Optional year for which to fetch team data.
        force_refresh: Whether to force refresh of cached data.
    Returns:
        List of dicts, each with keys "id" (ESPN team id string) and
        "name" (ESPN display name).
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = EspnApiClient(
            year=year, force_refresh=force_refresh)
    client = _client_instance
    teams_data = client.get_all_teams()
    teams = []
    for team_data in teams_data:
        team_info = team_data.get("team", {})
        teams.append({
            "id": str(team_info.get("id")),
            "name": team_info.get("displayName", "")
        })
    return teams
