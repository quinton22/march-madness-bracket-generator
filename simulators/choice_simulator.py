
import inquirer
from simulators.game_simulator import GameSimulator


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
