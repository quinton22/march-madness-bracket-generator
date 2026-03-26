import inquirer
import random
from simulators.game_simulator import GameSimulator


class ConfidenceGameSimulator(GameSimulator):
    __slots__ = 'confidences_cache'

    name = 'confidence'

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
