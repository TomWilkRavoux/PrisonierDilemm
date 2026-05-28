from src.strategies.always_cooperate import AlwaysCooperate
from src.strategies.always_defect import AlwaysDefect
from src.strategies.grim_trigger import GrimTrigger
from src.strategies.pavlov import Pavlov
from src.strategies.random_strategy import RandomStrategy
from src.strategies.tit_for_tat import TitForTat


def test_always_cooperate():
    s = AlwaysCooperate()
    assert s.choose([]) == "C"
    assert s.choose([("C", "D"), ("C", "D")]) == "C"


def test_always_defect():
    s = AlwaysDefect()
    assert s.choose([]) == "D"
    assert s.choose([("D", "C")]) == "D"


def test_tit_for_tat_starts_cooperating():
    s = TitForTat()
    assert s.choose([]) == "C"


def test_tit_for_tat_mirrors():
    s = TitForTat()
    assert s.choose([("C", "D")]) == "D"
    assert s.choose([("C", "D"), ("D", "C")]) == "C"


def test_grim_trigger_cooperates_initially():
    s = GrimTrigger()
    assert s.choose([]) == "C"


def test_grim_trigger_triggers_on_defect():
    s = GrimTrigger()
    assert s.choose([("C", "C")]) == "C"
    assert s.choose([("C", "C"), ("C", "D")]) == "D"
    assert s.choose([("C", "C"), ("C", "D"), ("D", "C")]) == "D"


def test_pavlov_starts_cooperating():
    s = Pavlov()
    assert s.choose([]) == "C"


def test_pavlov_win_stay():
    s = Pavlov()
    assert s.choose([("C", "C")]) == "C"
    assert s.choose([("D", "D")]) == "C"


def test_pavlov_lose_shift():
    s = Pavlov()
    assert s.choose([("C", "D")]) == "D"
    assert s.choose([("D", "C")]) == "D"


def test_random_returns_valid():
    s = RandomStrategy()
    for _ in range(20):
        assert s.choose([]) in ("C", "D")
