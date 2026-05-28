from abc import ABC, abstractmethod


class Strategy(ABC):
    name: str

    @abstractmethod
    def choose(self, history: list[tuple[str, str]]) -> str:
        """Return 'C' (cooperate) or 'D' (defect) given the match history.

        Each entry in history is (my_choice, opponent_choice).
        """

    def reset(self) -> None:
        pass
