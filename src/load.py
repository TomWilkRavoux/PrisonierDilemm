from pathlib import Path

import orjson
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"

VALID_CHOICES = {"C", "D"}


def validate_turns(df: pl.DataFrame) -> pl.DataFrame:
    assert df.filter(~pl.col("choice_a").is_in(VALID_CHOICES)).height == 0, "Invalid choice_a values"
    assert df.filter(~pl.col("choice_b").is_in(VALID_CHOICES)).height == 0, "Invalid choice_b values"
    assert df.filter(pl.col("score_a") < 0).height == 0, "Negative score_a"
    assert df.filter(pl.col("score_b") < 0).height == 0, "Negative score_b"
    assert df.null_count().sum_horizontal().item() == 0, "Null values found"
    return df


def load_run(run_dir: Path) -> None:
    run_id = run_dir.name
    print(f"Loading run {run_id}...")

    with open(run_dir / "turns.json", "rb") as f:
        turns_raw = orjson.loads(f.read())
    with open(run_dir / "matches.json", "rb") as f:
        matches_raw = orjson.loads(f.read())

    turns_df = pl.DataFrame(turns_raw)
    matches_df = pl.DataFrame(matches_raw)

    turns_df = turns_df.unique()
    matches_df = matches_df.unique()

    validate_turns(turns_df)

    turns_out = SILVER_DIR / "turns" / f"run_id={run_id}"
    turns_out.mkdir(parents=True, exist_ok=True)
    turns_df.drop("run_id").write_parquet(turns_out / "data.parquet")

    matches_out = SILVER_DIR / "matches" / f"run_id={run_id}"
    matches_out.mkdir(parents=True, exist_ok=True)
    matches_df.drop("run_id").write_parquet(matches_out / "data.parquet")

    print(f"  Turns:   {turns_df.height} rows → {turns_out}")
    print(f"  Matches: {matches_df.height} rows → {matches_out}")


def main() -> None:
    run_dirs = sorted(BRONZE_DIR.iterdir()) if BRONZE_DIR.exists() else []
    if not run_dirs:
        print("No bronze data found. Run 'make generate' first.")
        return

    for run_dir in run_dirs:
        if run_dir.is_dir() and (run_dir / "turns.json").exists():
            load_run(run_dir)

    print("Silver layer ready.")


if __name__ == "__main__":
    main()
