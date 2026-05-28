# Prisoner's Dilemma ETL Pipeline

Pipeline de data engineering autour d'une simulation du **dilemme du prisonnier iteratif**.
Le pipeline genere ses propres donnees (tournoi round-robin de strategies + agents Mistral IA), les charge en Parquet partitionne (Silver), et les transforme via dbt-duckdb (Gold).

## Stack

- Python 3.12 (uv)
- DuckDB + dbt-duckdb
- Polars / PyArrow
- Mistral API (httpx)

## Setup

```bash
uv sync
```

## Usage

```bash
# Pipeline complet (sans Mistral)
make all

# Etape par etape
make generate    # → data/bronze/<run_id>/
make load        # → data/silver/turns/run_id=<uuid>/
make transform   # → dbt build, data/dilemma.duckdb

# Avec Mistral
export MISTRAL_API_KEY=<votre_cle>
make all

# Tests
make test

# Nettoyage
make clean
```

## Verification

```bash
# Classement des strategies
duckdb data/dilemma.duckdb -c \
  "SELECT * FROM gold_strategy_metrics ORDER BY rank_in_run"

# Matrice head-to-head
duckdb data/dilemma.duckdb -c \
  "SELECT strategy, opponent, score_diff, result FROM gold_head_to_head ORDER BY strategy"

# Comparaison multi-run
duckdb data/dilemma.duckdb -c \
  "SELECT run_id, strategy, avg_score, rank_in_run FROM gold_run_comparison ORDER BY strategy, run_id"
```

## Strategies implementees

| Strategie | Description |
|-----------|-------------|
| always_cooperate | Coopere systematiquement |
| always_defect | Trahit systematiquement |
| tit_for_tat | Coopere au 1er tour, puis copie le dernier choix adverse |
| grim_trigger | Coopere jusqu'a la 1ere trahison, puis trahit indefiniment |
| random | Choix aleatoire 50/50 |
| pavlov | Win-stay, lose-shift |
| mistral_empathique | Agent IA empathique (API Mistral) |
| mistral_calculateur | Agent IA calculateur (API Mistral) |
| mistral_rancunier | Agent IA rancunier (API Mistral) |

## Modeles Gold (dbt)

- **gold_match_summary** : scores, taux cooperation, trahisons, cooperation mutuelle par match
- **gold_strategy_metrics** : performance globale par strategie, forgiveness rate, classement
- **gold_turn_evolution** : rolling cooperation rate (50 tours), memoire des 3 derniers tours
- **gold_head_to_head** : matrice de confrontation directe entre strategies
- **gold_run_comparison** : comparaison cross-run avec classement global (bonus)
