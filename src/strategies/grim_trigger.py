from src.strategies.base import Strategy


class GrimTrigger(Strategy):
    name = "grim_trigger"

    def __init__(self) -> None:
        self._triggered = False

    def choose(self, history: list[tuple[str, str]]) -> str:
        if self._triggered:
            return "D"
        if history and history[-1][1] == "D":
            self._triggered = True
            return "D"
        return "C"

    def reset(self) -> None:
        self._triggered = False
