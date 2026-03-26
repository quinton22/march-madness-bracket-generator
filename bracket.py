import re
from team import Team
from simulators.game_simulator import GameSimulator


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
