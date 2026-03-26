
import argparse
import random
from simulators.stats_simulator import StatsGameSimulator
from team import Team


def _parse_team_args(prefix: str, args) -> Team:
    """Create a Team instance from CLI args using the given prefix."""
    return Team(
        getattr(args, f"{prefix}_name"),
        getattr(args, f"{prefix}_seed"),
        getattr(args, f"{prefix}_conference"),
    )


def main() -> None:
    """Run a simple two-team stats simulation from the command line."""
    parser = argparse.ArgumentParser(
        description="Simulate a single game between two teams using the stats simulator."
    )
    parser.add_argument("--team1-name", required=True,
                        help="Name of the first team")
    parser.add_argument("--team1-seed", type=int, default=1,
                        help="Seed number for team 1")
    parser.add_argument(
        "--team1-conference",
        default="Unknown",
        help="Conference name for team 1 (optional)",
    )
    parser.add_argument("--team2-name", required=True,
                        help="Name of the second team")
    parser.add_argument("--team2-seed", type=int, default=16,
                        help="Seed number for team 2")
    parser.add_argument(
        "--team2-conference",
        default="Unknown",
        help="Conference name for team 2 (optional)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Number of simulated games to run (default: 1)",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="Seed for the random number generator (for reproducible results)",
    )

    args = parser.parse_args()

    if args.random_seed is not None:
        random.seed(args.random_seed)

    team1 = _parse_team_args("team1", args)
    team2 = _parse_team_args("team2", args)

    simulator = StatsGameSimulator()

    if args.iterations == 1:
        winner = simulator.simulate(team1, team2)
        print(f"Winner: {winner.name}")
        return

    wins = {team1.name: 0, team2.name: 0}
    for _ in range(args.iterations):
        winner = simulator.simulate(team1, team2)
        wins[winner.name] += 1

    print("Simulation results:")
    for team_name, count in wins.items():
        print(f"  {team_name}: {count} wins ({count / args.iterations:.1%})")


if __name__ == "__main__":
    main()
