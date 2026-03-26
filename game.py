class Game:
    """
    Represents a single game between two teams. Stores the teams and the winner.
    """

    __slots__ = 'team1', 'team2', 'winner'

    def __init__(self, *teams, ):
        self.team1 = teams[0]
        self.team2 = teams[1]
        self.winner = None
