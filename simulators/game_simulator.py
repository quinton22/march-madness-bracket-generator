from team import Team


class GameSimulator:
    __slots__ = 'options'

    name: str

    def __init__(self, options={}):
        self.options = options

    def preload(self, teams) -> None:
        """
        Pre-fetch and cache any necessary data for the teams in *teams*.
        This is an optional method that can be overridden by subclasses to improve performance.
        """

    def simulate(self, *teams: Team) -> Team:
        """
        Generates a tournament bracket by simulating matches between teams.
        """
        raise NotImplementedError(
            "simulate method must be implemented")
