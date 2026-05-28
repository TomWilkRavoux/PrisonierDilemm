from src.strategies.base import Strategy


class Pavlov(Strategy):
    name = "pavlov"

    def choose(self, history: list[tuple[str, str]]) -> str:
        if not history:
            return "C"
        my_last, opp_last = history[-1]
        if my_last == opp_last:
            return "C"
        return "D"
