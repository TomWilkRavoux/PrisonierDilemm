import datetime
import os
from dataclasses import asdict
from pathlib import Path

import orjson
import yaml
from dotenv import load_dotenv

load_dotenv()

from src.engine import Tournament
from src.strategies import STRATEGY_REGISTRY
from src.strategies.mistral_agent import MistralAgent

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config(path: Path | None = None) -> dict:
    if path is None:
        path = PROJECT_ROOT / "config.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def build_players(config: dict) -> list:
    players = []
    for name in config["strategies"]["coded"]:
        cls = STRATEGY_REGISTRY[name]
        players.append(cls())

    if os.environ.get("MISTRAL_API_KEY"):
        for agent_cfg in config["strategies"].get("mistral", []):
            players.append(MistralAgent(
                name=agent_cfg["name"],
                system_prompt=agent_cfg["system_prompt"],
            ))

    return players


def main() -> None:
    config = load_config()
    players = build_players(config)

    tournament = Tournament(
        players=players,
        num_rounds=config["tournament"]["rounds"],
        payoff_matrix=config["payoff_matrix"],
    )

    print(f"Run ID: {tournament.run_id}")
    print(f"Players: {[p.name for p in players]}")
    print(f"Rounds per match: {tournament.num_rounds}")
    print(f"Total matches: {len(players) * (len(players) - 1) // 2}")

    turns, matches = tournament.run_tournament()

    out_dir = PROJECT_ROOT / "data" / "bronze" / tournament.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "turns.json", "wb") as f:
        f.write(orjson.dumps([asdict(t) for t in turns], option=orjson.OPT_INDENT_2))

    with open(out_dir / "matches.json", "wb") as f:
        f.write(orjson.dumps([asdict(m) for m in matches], option=orjson.OPT_INDENT_2))

    metadata = {
        "run_id": tournament.run_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "num_rounds": tournament.num_rounds,
        "players": [p.name for p in players],
        "num_matches": len(matches),
        "num_turns": len(turns),
        "payoff_matrix": config["payoff_matrix"],
    }
    with open(out_dir / "metadata.json", "wb") as f:
        f.write(orjson.dumps(metadata, option=orjson.OPT_INDENT_2))

    print(f"Bronze data written to {out_dir}")


if __name__ == "__main__":
    main()
