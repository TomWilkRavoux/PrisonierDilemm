from src.strategies.base import Strategy


class TitForTat(Strategy):
    name = "tit_for_tat"

    def choose(self, history: list[tuple[str, str]]) -> str:
        if not history:
            return "C"
        return history[-1][1]
