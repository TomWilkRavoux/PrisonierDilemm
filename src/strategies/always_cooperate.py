from src.strategies.base import Strategy


class AlwaysCooperate(Strategy):
    name = "always_cooperate"

    def choose(self, history: list[tuple[str, str]]) -> str:
        return "C"
