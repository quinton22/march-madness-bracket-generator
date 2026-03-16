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
from os import write
import random
import re
import inquirer
import math


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


generator_types = ['coinflip', 'confidence']


class Team:
    __slots__ = 'name', 'seed', 'conference'

    def __init__(self, name, seed, conference):
        self.name = name
        self.seed = int(seed)
        self.conference = conference


class GameSimulator:
    __slots__ = 'options'

    name: str

    def __init__(self, options={}):
        self.options = options

    def simulate(self, *teams: Team) -> Team:
        """
        Generates a tournament bracket by simulating matches between teams.
        """
        raise NotImplementedError(
            "generate_bracket method must be implemented")


class CoinflipGameSimulator(GameSimulator):

    name = 'coinflip'

    def generate_probability(self, *teams):
        team1, team2 = teams
        if str.lower(self.options["seed_adjusted"]) == 'heavy':
            probability = team2.seed / (team1.seed + team2.seed)
        elif str.lower(self.options["seed_adjusted"]) == 'light':
            # Adjust the probability based on the seed difference
            seed_diff = abs(team1.seed - team2.seed)
            probability = 0.5 + 0.1 * math.log(seed_diff + 1)
        else:
            probability = 0.5

        return probability

    def simulate(self, *teams):
        team1, team2 = teams
        probability = self.generate_probability(*teams)
        return team1 if random.random() < probability else team2


class ChoiceGameSimulator(GameSimulator):

    name = 'choice'

    def generate_probability(self, *teams):
        names = [f"{team.name} ({team.seed})" for team in teams]
        questions = [
            inquirer.List('winner',
                          message="Enter the winner",
                          choices=names
                          )
        ]

        answers = inquirer.prompt(questions)

        if answers is None:
            exit(0)

        return 1 if teams[names.index(answers['winner'])] == teams[0] else 0

    def simulate(self, *teams):
        probability = self.generate_probability(*teams)

        return teams[0] if probability == 1 else teams[1]


class ConfidenceGameSimulator(GameSimulator):
    __slots__ = 'confidences_cache'

    name = 'coinflip'

    def __init__(self):
        super().__init__()
        self.confidences_cache = {}

    def get_confidence(self, *teams):
        teams = [team.name for team in teams]
        key = ','.join(sorted(teams))

        if key in self.confidences_cache:
            return self.confidences_cache[key]

        return None

    def store_confidences(self, winner, loser, confidence):
        teams = [winner.name, loser.name]
        key = ','.join(sorted(teams))

        self.confidences_cache[key] = {
            'winner': winner,
            'confidence': confidence
        }

    def generate_probability(self, *teams):
        names = [f"{team.name} ({team.seed})" for team in teams]
        cache_value = self.get_confidence(*teams)
        if cache_value is not None:
            return cache_value['confidence'] if cache_value['winner'] == teams[0] else 1 - cache_value['confidence']

        questions = [
            inquirer.List('winner',
                          message="Enter the winner",
                          choices=names
                          ),
            inquirer.Text('confidence',
                          message="Enter your confidence level 0-5",
                          validate=lambda _, x: x.isdigit() and 0 <= int(x) <= 5
                          )
        ]

        answers = inquirer.prompt(questions)

        if answers is None:
            exit(0)  # todo

        team = teams[names.index(answers['winner'])]

        confidence = int(answers['confidence']) / 10 + 0.4

        self.store_confidences(
            team, teams[1 - names.index(answers['winner'])], confidence)

        return confidence if team == teams[0] else 1 - confidence

    def simulate(self, *teams):
        team1, team2 = teams
        confidence = self.generate_probability(*teams)
        return team1 if random.random() < confidence else team2


class Game:
    __slots__ = 'team1', 'team2', 'winner'

    def __init__(self, *teams, ):
        self.team1 = teams[0]
        self.team2 = teams[1]
        self.winner = None

    def __init__(self, team1, team2):
        self.team1 = team1
        self.team2 = team2
        self.winner = None


class Bracket:
    __slots__ = 'teams', 'rounds', '_current_round', '_current_game'

    seed_indices = {
        1: 0,
        16: 1,
        8: 2,
        9: 3,
        5: 4,
        12: 5,
        4: 6,
        13: 7,
        6: 8,
        11: 9,
        3: 10,
        14: 11,
        7: 12,
        10: 13,
        2: 14,
        15: 15
    }

    conf_indices = {
        'South': 0,
        'West': 1,
        'East': 2,
        'Midwest': 3
    }

    final_bracket_str = """
x01
~~~---\\  x05
x02    |~~~---\\
~~~---/...     \\
......          |  x07
x03...          |~~~---
~~~---\\  x06   /
x04    |~~~---/
~~~---/
"""

    conf_bracket_str = """
x01
~~~---\\  x17
x02    |~~~---\\
~~~---/...     \\
......          |  x25
x03...          |~~~---\\
~~~---\\  x18   /...     \\
x04    |~~~---/...       |
~~~---/......            |  x29
.........                |~~~---\\
x05......                |...    \\
~~~---\\  x19...          |...     |
x06    |~~~---\\...       |...     |
~~~---/...     \\...      |...     |
......          |  x26  /...      |
x07...          |~~~---/...       |
~~~---\\  x20   /......            |
x08    |~~~---/......             |
~~~---/.........                  |  x31
............                      |~~~---
x09.........                      |
~~~---\\  x21......                |
x10    |~~~---\\......             |
~~~---/...     \\......            |
......          |  x27...         |
x11...          |~~~---\\...       |
~~~---\\  x22   /...     \\...      |
x12    |~~~---/...       |...     |
~~~---/......            |  x30  /
.........                |~~~---/
x13......                |
~~~---\\  x23...          |
x14    |~~~---\\...       |
~~~---/...     \\...      |
......          |  x28  /
x15...          |~~~---/
~~~---\\  x24   /
x16    |~~~---/
~~~---/
"""

    def _get_position(self, seed, conf):
        return self.seed_indices[seed] + len(self.seed_indices) * self.conf_indices[conf]

    def __init__(self, teams: list[Team]):
        self.teams = teams
        self._current_round = 0
        self._current_game = 0

        initial_round = {}
        for team in teams:
            initial_round[self._get_position(
                team.seed, team.conference)] = team

        self.rounds: list[list[Team]] = [[team for _, team in sorted(
            initial_round.items(), key=lambda x: x[0])]]

    @property
    def current_round(self) -> int:
        return self._current_round

    @property
    def current_game(self) -> int:
        return self._current_game

    def simulate(self, game_simulator: GameSimulator):
        while len(self.rounds[-1]) > 1:
            next_round = []
            for i in range(0, len(self.rounds[-1]), 2):
                winner = game_simulator.simulate(
                    self.rounds[-1][i], self.rounds[-1][i + 1])
                next_round.append(winner)
            self.rounds.append(next_round)

    def __next__(self):
        if self.current_round >= len(self.rounds):
            raise StopIteration
        else:
            self._current_game += 1
            if (self.current_game * 2) >= len(self.rounds[self.current_round]):
                self._current_game = 0
                self._current_round += 1

            return self.rounds[self.current_round][self.current_game * 2], self.rounds[self.current_round][self.current_game * 2 + 1]

    def __iter__(self):
        return self

    def _get_longest_team_name(self):
        return max(len(team.name) for team in self.teams)

    def _get_padded_team_name(self, team, length):
        return f"{team.name} ({team.seed}){' ' * (length - len(team.name) - len(str(team.seed)) - 3)}"

    def __str__(self):
        # print the entire bracket
        length = self._get_longest_team_name() + len(" (xx) ")

        bracket_str = ""

        for c in self.conf_indices:
            bracket_str += f"{c}\n"
            bracket_str += str(self.conf_bracket_str).replace("...", " " * length).replace(
                "~~~", "-" * length)

            i = 0
            for r in self.rounds:
                for t in r:
                    if t.conference == c:
                        i += 1
                        s = f"x0{i}" if i < 10 else f"x{i}"
                        bracket_str = bracket_str.replace(
                            s, self._get_padded_team_name(t, length), 1)

            bracket_str = re.sub(r"x\d\d", " " * length, bracket_str)
            bracket_str += "\n\n"

        index = -1

        while len(self.rounds[index]) < 4:
            index -= 1

        if index == -1 and len(self.rounds[index]) > 4:
            return bracket_str

        else:
            bracket_str += "Final Four\n"
            bracket_str += str(self.final_bracket_str).replace(
                "...", " " * length).replace("~~~", "-" * length)

            i = 0
            while index < 0:
                for t in self.rounds[index]:
                    i += 1
                    bracket_str = bracket_str.replace(
                        f"x0{i}", self._get_padded_team_name(t, length), 1)
                index += 1

            bracket_str += "\n\n"

        return bracket_str
    # def simulate_match(self, team1, team2):
    #     """
    #     Simulates the outcome of a match between two teams based on their seeds.

    #     Args:
    #       team1 (dict): A dictionary containing information about the first team, including its seed.
    #       team2 (dict): A dictionary containing information about the second team, including its seed.

    #     Returns:
    #       dict: The dictionary of the winning team.
    #     """
    #     # Simulate match outcome based on seed
    #     seed1 = int(team1.seed)
    #     seed2 = int(team2.seed)
    #     probability = seed2 / (seed1 + seed2)


def main():
    """
    Main function
    """

    args = get_args()
    generator_type = args.generator_type
    input_file = args.input_file
    num_iterations = args.num_iterations

    options = {
        "seed_adjusted": args.seed_adjusted
    }

    teams = read_teams(input_file)

    if generator_type == 'coinflip':
        game_simulator = CoinflipGameSimulator(options=options)
    elif generator_type == 'confidence':
        game_simulator = ConfidenceGameSimulator()
    else:
        raise ValueError(f"Invalid generator type: {generator_type}")

    print("Simulating with simulator", game_simulator.name)
    print("Options: ", options)
    print("")
    brackets = [Bracket(teams) for _ in range(num_iterations)]

    for i, bracket in enumerate(brackets):
        bracket.simulate(game_simulator)

        with open(f'sim_{i+1}.txt', 'w', encoding='utf8') as f:
            f.write(str(bracket))

        print(bracket)

    # teams = read_teams('teams.csv')
    # bracket = generate_bracket(teams)
    # print_bracket(bracket)


if __name__ == "__main__":
    main()
