
class Team:
    __slots__ = 'name', 'seed', 'conference'

    def __init__(self, name, seed, conference):
        self.name = name
        self.seed = int(seed)
        self.conference = conference
