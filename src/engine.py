import uuid
from dataclasses import dataclass, field

from src.strategies.base import Strategy
from src.strategies.mistral_agent import MistralAgent


@dataclass
class TurnRecord:
    run_id: str
    match_id: str
    turn_number: int
    player_a: str
    player_b: str
    strategy_a: str
    strategy_b: str
    choice_a: str
    choice_b: str
    score_a: int
    score_b: int
    cumulative_score_a: int
    cumulative_score_b: int
    reasoning_a: str
    reasoning_b: str


@dataclass
class MatchRecord:
    run_id: str
    match_id: str
    player_a: str
    player_b: str
    strategy_a: str
    strategy_b: str
    total_score_a: int
    total_score_b: int
    num_turns: int


PayoffMatrix = dict[str, list[int]]


@dataclass
class Tournament:
    players: list[Strategy]
    num_rounds: int
    payoff_matrix: PayoffMatrix
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def _compute_scores(self, choice_a: str, choice_b: str) -> tuple[int, int]:
        key = choice_a + choice_b
        pair = self.payoff_matrix[key]
        return pair[0], pair[1]

    def play_match(self, player_a: Strategy, player_b: Strategy) -> tuple[list[TurnRecord], MatchRecord]:
        match_id = str(uuid.uuid4())
        turns: list[TurnRecord] = []
        history_a: list[tuple[str, str]] = []
        history_b: list[tuple[str, str]] = []
        cum_a = 0
        cum_b = 0

        player_a.reset()
        player_b.reset()

        for t in range(1, self.num_rounds + 1):
            choice_a = player_a.choose(history_a)
            choice_b = player_b.choose(history_b)
            sa, sb = self._compute_scores(choice_a, choice_b)
            cum_a += sa
            cum_b += sb

            reasoning_a = player_a.get_reasoning() if isinstance(player_a, MistralAgent) else ""
            reasoning_b = player_b.get_reasoning() if isinstance(player_b, MistralAgent) else ""

            turns.append(TurnRecord(
                run_id=self.run_id,
                match_id=match_id,
                turn_number=t,
                player_a=player_a.name,
                player_b=player_b.name,
                strategy_a=player_a.name,
                strategy_b=player_b.name,
                choice_a=choice_a,
                choice_b=choice_b,
                score_a=sa,
                score_b=sb,
                cumulative_score_a=cum_a,
                cumulative_score_b=cum_b,
                reasoning_a=reasoning_a,
                reasoning_b=reasoning_b,
            ))

            history_a.append((choice_a, choice_b))
            history_b.append((choice_b, choice_a))

        match_rec = MatchRecord(
            run_id=self.run_id,
            match_id=match_id,
            player_a=player_a.name,
            player_b=player_b.name,
            strategy_a=player_a.name,
            strategy_b=player_b.name,
            total_score_a=cum_a,
            total_score_b=cum_b,
            num_turns=self.num_rounds,
        )

        return turns, match_rec

    def run_tournament(self) -> tuple[list[TurnRecord], list[MatchRecord]]:
        all_turns: list[TurnRecord] = []
        all_matches: list[MatchRecord] = []

        for i in range(len(self.players)):
            for j in range(i + 1, len(self.players)):
                turns, match = self.play_match(self.players[i], self.players[j])
                all_turns.extend(turns)
                all_matches.append(match)

        return all_turns, all_matches
