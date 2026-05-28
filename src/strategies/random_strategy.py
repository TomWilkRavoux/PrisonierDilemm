import random

from src.strategies.base import Strategy


class RandomStrategy(Strategy):
    name = "random"

    def choose(self, history: list[tuple[str, str]]) -> str:
        return random.choice(["C", "D"])
