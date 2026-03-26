"""
This module provides functionality to read teams from a CSV file, simulate matches between teams,
generate a tournament bracket, and print the bracket.

Functions:
  read_teams(file_path): Reads teams from a CSV file and returns a list of teams.
  simulate_match(team1, team2): Simulates a match between two teams and returns the winning team.
  generate_bracket(teams): Generates a tournament bracket from a list of teams.
  print_bracket(bracket): Prints the tournament bracket.

Usage:
  Run the module as a script to read teams from 'teams.csv', generate a bracket, and print it.
"""

import argparse
import csv
import os
from simulators.game_simulator import GameSimulator
from simulators.stats_simulator import StatsGameSimulator
from simulators.choice_simulator import ChoiceGameSimulator
from simulators.coinflip_simulator import CoinflipGameSimulator
from simulators.confidence_simulator import ConfidenceGameSimulator
from bracket import Bracket
from team import Team


def read_teams(file_path):
    """
    Reads a CSV file containing team information and returns a list of dictionaries.

    Args:
      file_path (str): The path to the CSV file containing the team data.

    Returns:
      list: A list of dictionaries, where each dictionary represents a team and its attributes.
    """
    teams = []
    with open(file_path, newline='', encoding='utf8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            teams.append(Team(row['Team'], row['Seed'], row['Conference']))
    return teams


def get_args():
    """
    Gets the command line arguments.

    Returns:
      tuple: A tuple containing the bracket type (str) and the number of iterations (int).
    """
    parser = argparse.ArgumentParser(
        description='Generate tournament brackets.')
    parser.add_argument('generator_type', choices=generator_types,
                        help='Type of generator to use',)
    parser.add_argument('--seed-adjusted', choices=['light', 'heavy'],
                        default=None,
                        help='Adjust the probability based on the seed for a coinflip generator.')
    parser.add_argument('-i', '--input-file', type=str, required=True,
                        help='The path to the CSV file containing team data.')
    parser.add_argument('-n', '--num-iterations', type=int, default=1,
                        help='The number of brackets to generate.')

    parser.add_argument('-y', '--year', type=int, default=None,
                        help='The year for which to fetch team data (used by the stats simulator).')

    parser.add_argument('--force-refresh', action='store_true',
                        help='Force refresh of cached data from the ESPN API.')

    args = parser.parse_args()

    return args


# def get_user_input():
#     """
#     Gets user input to determine the type of bracket to create and the number of iterations.

#     Returns:
#       tuple: A tuple containing the type of bracket (str) and the number of iterations (int).
#     """

#     questions = [
#         inquirer.List('bracket_type',
#                       message="Enter the type of bracket",
#                       choices=bracket_types,
#                       ),
#         inquirer.Text('iterations',
#                       message="Enter the number of brackets to generate",
#                       validate=lambda _, x: x.isdigit() and int(x) > 0
#                       )
#     ]

#     answers = inquirer.prompt(questions)

#     if answers is None:
#         return None, None

#     return answers['bracket_type'], int(answers['iterations'])


generator_types = ['coinflip', 'confidence', 'stats']


def main():
    """
    Main function
    """

    args = get_args()
    generator_type = args.generator_type
    year = args.year
    force_refresh = args.force_refresh
    input_file = args.input_file
    num_iterations = args.num_iterations

    options = {
        "seed_adjusted": args.seed_adjusted,
        "year": year,
        "force_refresh": force_refresh
    }

    teams = read_teams(input_file)

    game_simulator: GameSimulator

    if generator_type == 'coinflip':
        game_simulator = CoinflipGameSimulator(options=options)
    elif generator_type == 'confidence':
        game_simulator = ConfidenceGameSimulator()
    elif generator_type == 'choice':
        game_simulator = ChoiceGameSimulator()
    elif generator_type == 'stats':
        game_simulator = StatsGameSimulator(options=options)
    else:
        raise ValueError(f"Invalid generator type: {generator_type}")

    print("Simulating with simulator", game_simulator.name)
    print("Options: ", options)
    print("")
    brackets = [Bracket(teams) for _ in range(num_iterations)]

    # Pre-load team stats upfront when using the stats simulator so that all
    # API traffic happens before bracket simulation begins.
    if generator_type == 'stats':
        game_simulator.preload(teams)

    os.makedirs('sims', exist_ok=True)

    for i, bracket in enumerate(brackets):
        bracket.simulate(game_simulator)

        with open(f'sims/{i+1}.txt', 'w', encoding='utf8') as f:
            f.write(str(bracket))

        print(bracket)

    # teams = read_teams('teams.csv')
    # bracket = generate_bracket(teams)
    # print_bracket(bracket)


if __name__ == "__main__":
    main()
