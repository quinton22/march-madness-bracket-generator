"""
Statistics-based game simulator for the March Madness bracket generator.

Uses real team statistics (scoring margin, win percentage) fetched from the
ESPN college basketball API to calculate win probabilities, producing more
historically-grounded bracket predictions than a pure coin-flip or
seed-based approach.

Win probability model
---------------------
For each matchup the simulator combines two signals:

1. **Scoring margin** – ``(points scored - points allowed) / game`` is a
   stronger predictor of future performance than win percentage alone.
   The difference in scoring margin between the two teams is passed through
   a logistic function (sigmoid), scaled so that a 10-point margin advantage
   corresponds to roughly a 73 % win probability.

2. **Win percentage (log5)** – Bill James' log5 formula converts each team's
   season win percentage into a head-to-head win probability:

       P(A beats B) = (P_A − P_A·P_B) / (P_A + P_B − 2·P_A·P_B)

The two signals are combined with weights 0.7 (margin) and 0.3 (win-pct).
Final probability is clamped to [0.05, 0.95] to preserve upset potential.

Fallback behaviour
------------------
* If a team cannot be matched in the ESPN database, seed-based probability
  ``P = seed_B / (seed_A + seed_B)`` is used instead.
* All API errors are caught; the simulator never crashes due to network issues.
"""

import math
import random
from typing import Optional

from api_client import fetch_all_teams, get_team_data


# ---------------------------------------------------------------------------
# Probability helpers
# ---------------------------------------------------------------------------

def _logistic(x: float) -> float:
    """Logistic (sigmoid) function: maps any real number to (0, 1)."""
    return 1.0 / (1.0 + math.exp(-x))


def _log5(p_a: float, p_b: float) -> float:
    """
    Bill James log5 formula.

    Returns the probability that team A beats team B given their individual
    win probabilities against a hypothetical average opponent.
    """
    denom = p_a + p_b - 2.0 * p_a * p_b
    if denom == 0.0:
        return 0.5
    return (p_a - p_a * p_b) / denom


def calculate_win_probability(stats1: dict, stats2: dict) -> float:
    """
    Calculate the probability that the team represented by *stats1* wins
    against the team represented by *stats2*.

    Args:
        stats1: Stats dict for team 1 (as returned by :func:`api_client.get_team_data`).
        stats2: Stats dict for team 2.

    Returns:
        float in [0.05, 0.95] representing team 1's win probability.
    """
    margin1: float = stats1.get("scoring_margin", 0.0)
    margin2: float = stats2.get("scoring_margin", 0.0)
    win_pct1: float = stats1.get("win_pct", 0.5)
    win_pct2: float = stats2.get("win_pct", 0.5)

    # --- Scoring margin component ---
    # Scale: 10-point margin diff → logistic(1.0) ≈ 0.73 win prob
    margin_prob = _logistic((margin1 - margin2) / 10.0)

    # --- Win-percentage component ---
    win_pct_prob = _log5(win_pct1, win_pct2)

    # Weighted combination
    combined = 0.7 * margin_prob + 0.3 * win_pct_prob

    # Clamp to preserve upset potential
    return max(0.05, min(0.95, combined))


# ---------------------------------------------------------------------------
# Simulator class
# ---------------------------------------------------------------------------

class StatsGameSimulator:
    """
    Simulate tournament games using ESPN API team statistics.

    Teams whose names cannot be resolved in the ESPN database automatically
    fall back to seed-based probability, so the simulator is always usable
    even without a network connection.

    Usage::

        simulator = StatsGameSimulator()
        simulator.preload_stats(teams)   # optional but recommended
        winner = simulator.simulate(team_a, team_b)
    """

    name = "stats"

    def __init__(self, options: Optional[dict] = None):
        self.options: dict = options or {}
        self._stats_cache: dict[str, Optional[dict]] = {}
        self._all_teams: Optional[list] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_teams_loaded(self) -> None:
        """Lazy-load the full ESPN teams list exactly once."""
        if self._all_teams is None:
            try:
                print("Fetching team list from ESPN API…")
                self._all_teams = fetch_all_teams()
                print(f"  Loaded {len(self._all_teams)} teams from ESPN.")
            except Exception as exc:
                print(f"  Warning: Could not fetch ESPN team list ({exc}). "
                      "Falling back to seed-based simulation.")
                self._all_teams = []

    def _fetch_stats(self, team) -> Optional[dict]:
        """Fetch stats for *team* from the ESPN API (with caching)."""
        return self._fetch_stats_by_name(team.name)

    def _fetch_stats_by_name(self, name: str) -> Optional[dict]:
        """Fetch stats for a team identified by *name* (with caching)."""
        if name not in self._stats_cache:
            self._ensure_teams_loaded()
            data = get_team_data(name, self._all_teams)
            if data is None:
                print(f"  Warning: '{name}' not found in ESPN database. "
                      "Using seed-based fallback.")
            self._stats_cache[name] = data
        return self._stats_cache[name]

    @staticmethod
    def _seed_fallback_probability(team1, team2) -> float:
        """
        Win probability based on tournament seeds when API data is unavailable.

        A lower seed number indicates a stronger team.  Using
        ``P = seed_B / (seed_A + seed_B)`` gives team 1 a higher probability
        when it has a lower (better) seed.
        """
        s1, s2 = team1.seed, team2.seed
        return s2 / (s1 + s2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def preload_stats(self, teams) -> None:
        """
        Pre-fetch and cache statistics for every team in *teams*.

        Call this before starting simulation to front-load all API traffic
        rather than hitting the network during each individual game.

        Args:
            teams: Iterable of :class:`bracket_generator.Team` objects.
        """
        self._ensure_teams_loaded()
        unique_names = {team.name for team in teams}
        total = len(unique_names)
        print(f"Pre-loading stats for {total} teams…")
        for i, name in enumerate(sorted(unique_names), 1):
            self._fetch_stats_by_name(name)
            print(f"  [{i}/{total}] {name}")
        print("Done loading stats.\n")

    def simulate(self, team1, team2):
        """
        Simulate a single game between *team1* and *team2*.

        Args:
            team1: :class:`bracket_generator.Team` — first team.
            team2: :class:`bracket_generator.Team` — second team.

        Returns:
            The winning :class:`bracket_generator.Team`.
        """
        stats1 = self._fetch_stats(team1)
        stats2 = self._fetch_stats(team2)

        if stats1 and stats2:
            probability = calculate_win_probability(stats1, stats2)
        else:
            probability = self._seed_fallback_probability(team1, team2)

        return team1 if random.random() < probability else team2
