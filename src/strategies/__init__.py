from src.strategies.always_cooperate import AlwaysCooperate
from src.strategies.always_defect import AlwaysDefect
from src.strategies.grim_trigger import GrimTrigger
from src.strategies.pavlov import Pavlov
from src.strategies.random_strategy import RandomStrategy
from src.strategies.tit_for_tat import TitForTat

STRATEGY_REGISTRY: dict[str, type] = {
    "always_cooperate": AlwaysCooperate,
    "always_defect": AlwaysDefect,
    "tit_for_tat": TitForTat,
    "grim_trigger": GrimTrigger,
    "random": RandomStrategy,
    "pavlov": Pavlov,
}
