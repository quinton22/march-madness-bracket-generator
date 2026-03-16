# March Madness Bracket Generator

A Python application that simulates NCAA March Madness tournament brackets using
multiple strategies — from a simple coin flip to a statistics-driven model powered
by real team data from the **ESPN API**.

---

## Features

| Simulator | Description |
|-----------|-------------|
| `coinflip` | Random simulation with optional seed-based probability adjustments |
| `confidence` | Interactive simulation where you rate your confidence in each matchup |
| `stats` | Data-driven simulation using live team statistics and historical performance via the ESPN API |

---

## Requirements

- Python 3.9 or higher
- See [`requirements.txt`](requirements.txt) for package dependencies

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
python bracket_generator.py <generator_type> -i <teams_csv> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `generator_type` | One of `coinflip`, `confidence`, or `stats` |
| `-i / --input-file` | Path to the CSV file containing team data (required) |
| `-n / --num-iterations` | Number of brackets to generate (default: `1`) |
| `--seed-adjusted` | `light` or `heavy` — only applies to the `coinflip` generator |

### Examples

```bash
# Pure random coin flip
python bracket_generator.py coinflip -i teams.csv -n 10

# Coin flip adjusted by tournament seeding (light adjustment)
python bracket_generator.py coinflip -i teams.csv --seed-adjusted light -n 5

# Coin flip adjusted by tournament seeding (heavy adjustment)
python bracket_generator.py coinflip -i teams.csv --seed-adjusted heavy -n 5

# Interactive confidence-based simulation
python bracket_generator.py confidence -i teams.csv -n 1

# Statistics-based simulation using ESPN API data
python bracket_generator.py stats -i teams.csv -n 5
```

---

## Input File Format

The input CSV file must have the following columns:

| Column | Description |
|--------|-------------|
| `Team` | Team name — should closely match ESPN team names when using the `stats` simulator |
| `Seed` | Tournament seed (1–16) |
| `Conference` | Regional bracket assignment: `South`, `West`, `East`, or `Midwest` |

Example:

```csv
Team,Seed,Conference
Duke,1,East
Kentucky,2,East
North Carolina,3,East
...
```

> **Tip:** When using the `stats` simulator, team names should match (or be close
> to) the names used by ESPN (e.g. `"Duke Blue Devils"` or simply `"Duke"`).
> Fuzzy name matching handles minor variations automatically.

---

## Simulators

### Coinflip Simulator

Simulates each game using random probability. Optionally adjusts the probability
based on the difference in tournament seeds:

- **Default** — pure 50/50 random
- `--seed-adjusted light` — logarithmic adjustment: `P = 0.5 + 0.1 × log(|seed_diff| + 1)`
- `--seed-adjusted heavy` — proportional adjustment: `P = seed_B / (seed_A + seed_B)`

### Confidence Simulator

An interactive simulator where you choose the winner and assign a confidence level
(0–5) for each matchup. Results are cached so that repeated matchups across
multiple bracket iterations reuse your previous answers.

### Stats Simulator

Uses the **ESPN college basketball API** to fetch real team statistics for the
current season, then calculates win probabilities using a two-factor model:

1. **Scoring margin** — the difference in average scoring margin (points scored
   minus points allowed per game) between the two teams is the primary signal.
   It is passed through a logistic function scaled so a 10-point margin advantage
   corresponds to approximately a 73 % win probability.

2. **Win percentage (log5)** — Bill James' log5 formula converts each team's
   season win percentage into a head-to-head win probability:

   ```
   P(A beats B) = (P_A − P_A·P_B) / (P_A + P_B − 2·P_A·P_B)
   ```

The two signals are combined with a **70 / 30 weight** (margin / win-pct) and
clamped to \[0.05, 0.95\] to preserve the possibility of upsets.

#### Fallback behaviour

If a team cannot be found in the ESPN database (e.g. due to a name mismatch or
network error) the simulator falls back to seed-based probability so that
bracket generation always completes.

---

## ESPN API Integration

The `stats` simulator uses the public ESPN college basketball API — no API key
is required.

### Endpoints

| Purpose | URL |
|---------|-----|
| All teams | `GET /teams?limit=1000` |
| Team statistics | `GET /teams/{id}/statistics` |
| Win/loss record | `GET /teams/{id}/record` |

**Base URL:** `https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball`

Statistics are fetched once per team and cached for the duration of a run.  All
API calls include a 10-second timeout and handle errors gracefully.

---

## Output

Generated brackets are:

- **Printed to the console** in ASCII-art format showing all rounds and the
  Final Four.
- **Saved as text files** in the `sims/` directory:
  ```
  sims/1.txt
  sims/2.txt
  ...
  ```

Sample output (truncated):

```
South
Team A (1) --------\
                    Team A (1) ------\
Team B (16) -------/                 \
                                      Team A (1) ---
Team C (8) --------\                 /
                    Team D (9) ------/
Team D (9) --------/
```

---

## Project Structure

```
march-madness-bracket-generator/
├── bracket_generator.py   # Core application: CLI, Bracket class, all simulators
├── api_client.py          # ESPN API client (team search, statistics, records)
├── stats_simulator.py     # StatsGameSimulator using ESPN data
├── requirements.txt       # Python dependencies
├── bracket.txt            # ASCII bracket template reference
└── README.md              # This file
```

---

## License

This project is open source. See the repository for licence details.
