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

from difflib import SequenceMatcher
from typing import Optional

import requests

ESPN_BASE_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
)
REQUEST_TIMEOUT = 10  # seconds


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _similarity(a: str, b: str) -> float:
    """Return a similarity ratio in [0, 1] between two strings (case-insensitive)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ---------------------------------------------------------------------------
# Raw API calls
# ---------------------------------------------------------------------------

def fetch_all_teams() -> list:
    """
    Fetch all NCAA Division I men's basketball teams from ESPN.

    Returns:
        list: A list of team-wrapper dicts, each containing a ``"team"`` key
              with id, displayName, abbreviation, etc.

    Raises:
        requests.HTTPError: If the ESPN server returns a non-2xx status.
        requests.ConnectionError: If the network is unavailable.
    """
    url = f"{ESPN_BASE_URL}/teams"
    response = requests.get(url, params={"limit": 1000}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    sports = data.get("sports", [])
    if not sports:
        return []
    leagues = sports[0].get("leagues", [])
    if not leagues:
        return []
    return leagues[0].get("teams", [])


def fetch_team_statistics(team_id: str) -> dict:
    """
    Fetch season statistics for a single ESPN team.

    Args:
        team_id: ESPN numeric team identifier (e.g. ``"52"`` for Duke).

    Returns:
        dict: Raw ESPN statistics response.

    Raises:
        requests.HTTPError: If the ESPN server returns a non-2xx status.
    """
    url = f"{ESPN_BASE_URL}/teams/{team_id}/statistics"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_team_record(team_id: str) -> dict:
    """
    Fetch the season win/loss record for a single ESPN team.

    Args:
        team_id: ESPN numeric team identifier.

    Returns:
        dict: Raw ESPN record response.

    Raises:
        requests.HTTPError: If the ESPN server returns a non-2xx status.
    """
    url = f"{ESPN_BASE_URL}/teams/{team_id}/record"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Team search
# ---------------------------------------------------------------------------

def find_team_by_name(name: str, all_teams: Optional[list] = None) -> Optional[dict]:
    """
    Locate a team in the ESPN dataset by display name.

    Attempts an exact case-insensitive match first against ``displayName``,
    ``shortDisplayName``, ``name``, ``nickname``, and ``abbreviation``.
    Falls back to fuzzy (SequenceMatcher) matching if no exact match is found,
    returning the best match with similarity >= 0.6.

    Args:
        name: Human-readable team name (e.g. ``"Duke"`` or ``"Duke Blue Devils"``).
        all_teams: Pre-fetched teams list; fetched automatically when *None*.

    Returns:
        The ESPN ``"team"`` dict, or *None* if no acceptable match found.
    """
    if all_teams is None:
        all_teams = fetch_all_teams()

    name_lower = name.lower()
    best_match: Optional[dict] = None
    best_score: float = 0.0

    for team_data in all_teams:
        team = team_data.get("team", {})
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
                return team  # exact match — stop immediately
            score = _similarity(name_lower, candidate.lower())
            if score > best_score:
                best_score = score
                best_match = team

    return best_match if best_score >= 0.6 else None


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_statistics(stats_data: dict) -> dict:
    """
    Flatten ESPN statistics response into a ``{stat_name: float}`` dict.

    The ESPN response nests stats inside ``results.stats.categories[*].stats``.
    This function extracts every leaf ``{name, value}`` pair regardless of
    category.

    Args:
        stats_data: Raw dict returned by :func:`fetch_team_statistics`.

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
                    parsed[stat_name] = float(raw_value) if raw_value is not None else 0.0
                except (TypeError, ValueError):
                    parsed[stat_name] = 0.0
    return parsed


def parse_record(record_data: dict) -> dict:
    """
    Extract wins, losses, and win percentage from an ESPN record response.

    Looks for the ``"total"`` item inside ``record_data["items"]``.

    Args:
        record_data: Raw dict returned by :func:`fetch_team_record`.

    Returns:
        dict with keys ``"wins"`` (float), ``"losses"`` (float),
        ``"win_pct"`` (float in [0, 1]).  Defaults to 0.5 win_pct when
        the record cannot be parsed.
    """
    for item in record_data.get("items", []):
        if item.get("type") == "total":
            stats = {s["name"]: s.get("value", 0) for s in item.get("stats", [])}
            wins = float(stats.get("wins", 0))
            losses = float(stats.get("losses", 0))
            games = wins + losses
            win_pct = wins / games if games > 0 else 0.5
            return {"wins": wins, "losses": losses, "win_pct": win_pct}
    return {"wins": 0.0, "losses": 0.0, "win_pct": 0.5}


# ---------------------------------------------------------------------------
# High-level entry point
# ---------------------------------------------------------------------------

def get_team_data(team_name: str, all_teams: Optional[list] = None) -> Optional[dict]:
    """
    Return a normalised stats dict for *team_name*, or *None* on failure.

    Fetches and combines team statistics and win/loss record.  Any individual
    API call that fails is silently swallowed so partial data is still usable.

    Args:
        team_name: Human-readable team name as it appears in the bracket CSV.
        all_teams: Pre-fetched ESPN teams list (fetched automatically if *None*).

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
    team = find_team_by_name(team_name, all_teams)
    if team is None:
        return None

    team_id = team.get("id")

    # Defaults used when an individual API call fails
    pts_per_game: float = 70.0
    pts_allowed_per_game: float = 70.0
    win_pct: float = 0.5

    try:
        stats_data = fetch_team_statistics(team_id)
        stats = parse_statistics(stats_data)
        # Defensive: check several candidate field names ESPN uses
        pts_per_game = float(
            stats.get("avgPointsPerGame")
            or stats.get("avgPoints")
            or stats.get("points")
            or pts_per_game
        )
        pts_allowed_per_game = float(
            stats.get("avgPointsAllowedPerGame")
            or stats.get("avgPointsAgainstPerGame")
            or stats.get("pointsAllowed")
            or pts_allowed_per_game
        )
    except Exception:
        pass  # fall back to defaults

    try:
        record_data = fetch_team_record(team_id)
        record = parse_record(record_data)
        win_pct = record["win_pct"]
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
