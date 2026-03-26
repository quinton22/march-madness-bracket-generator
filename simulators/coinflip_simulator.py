import math
import random
from simulators.game_simulator import GameSimulator


class CoinflipGameSimulator(GameSimulator):

    name = 'coinflip'

    def generate_probability(self, *teams):
        team1, team2 = teams
        if str.lower(self.options.get("seed_adjusted", "")) == 'heavy':
            probability = team2.seed / (team1.seed + team2.seed)
        elif str.lower(self.options.get("seed_adjusted", "")) == 'light':
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
