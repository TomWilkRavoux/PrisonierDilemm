from src.strategies.base import Strategy


class AlwaysDefect(Strategy):
    name = "always_defect"

    def choose(self, history: list[tuple[str, str]]) -> str:
        return "D"
