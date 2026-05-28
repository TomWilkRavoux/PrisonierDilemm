# Plan — Prisoner's Dilemma ETL Pipeline

## Contexte

Projet EPSI M1 Data/IA. Construire un pipeline de data engineering complet autour d'une simulation du **dilemme du prisonnier iteratif**. Le pipeline genere ses propres donnees (tournoi de strategies + agents Mistral), les charge en Parquet (Silver), et les transforme via dbt-duckdb (Gold). Le bonus (multi-run versioning) est inclus.

**Repo** : `/home/snowgou/EPSI/M1/ETL&ELT/prisoner-dilemma-etl`  
**Stack** : Python 3.12 (uv), DuckDB, dbt-duckdb, Mistral API, polars, httpx

---

## Structure du repo

```
prisoner-dilemma-etl/
├── .gitignore
├── .python-version
├── pyproject.toml                  # deps via uv
├── Makefile                        # make generate / load / transform / all
├── config.yaml                     # parametres du tournoi
├── README.md
├── ARCHITECTURE.md                 # explication Bronze/Silver/Gold + Delta Lake (bonus)
├── src/
│   ├── __init__.py
│   ├── strategies/
│   │   ├── __init__.py             # STRATEGY_REGISTRY
│   │   ├── base.py                 # classe abstraite Strategy
│   │   ├── always_cooperate.py
│   │   ├── always_defect.py
│   │   ├── tit_for_tat.py
│   │   ├── grim_trigger.py
│   │   ├── random_strategy.py
│   │   ├── pavlov.py               # win-stay lose-shift (bonus)
│   │   └── mistral_agent.py        # agent IA via API Mistral
│   ├── engine.py                   # moteur de tournoi round-robin
│   ├── generate.py                 # CLI → Bronze (JSON)
│   ├── load.py                     # Bronze → Silver (Parquet partitionne)
│   └── transform.py                # Silver → Gold (appelle dbt build)
├── dbt_dilemma/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── sources.yml             # lecture Silver Parquet via external_location
│       ├── staging/
│       │   ├── stg_turns.sql
│       │   └── stg_matches.sql
│       └── gold/
│           ├── gold_match_summary.sql      # scores, taux coop, trahisons par match
│           ├── gold_strategy_metrics.sql   # perf globale par strategie + forgiveness
│           ├── gold_turn_evolution.sql     # rolling coop rate + memoire des tours
│           ├── gold_head_to_head.sql       # matrice confrontation directe
│           └── gold_run_comparison.sql     # comparaison cross-run (bonus)
├── tests/
│   └── test_strategies.py
├── data/                           # .gitignore'd
│   ├── bronze/
│   ├── silver/
│   └── gold/
└── docs/
    └── delta_lake_design.md        # conception Delta Lake (bonus)
```

---

## Phases d'implementation

### Phase 1 — Scaffold projet (30 min)

- `mkdir -p` structure de dossiers
- `uv init` + `pyproject.toml` avec deps : duckdb, dbt-duckdb, polars, pyarrow, httpx, pyyaml, orjson, pytest
- `.gitignore` (data/, *.duckdb, __pycache__/, .venv/, dbt_dilemma/target/, dbt_dilemma/logs/)
- `config.yaml` avec parametres par defaut :
  - rounds: 200 (pas 2000, sinon ~7h d'appels Mistral)
  - matrice: CC=3/3, CD=0/5, DC=5/0, DD=1/1
  - strategies codees + 3 profils Mistral (empathique, calculateur, rancunier)
- `git init` + commit initial

### Phase 2 — Strategies codees (1h)

- `base.py` : classe abstraite `Strategy` avec `choose(history) -> "C"|"D"`
- 6 strategies : always_cooperate, always_defect, tit_for_tat, grim_trigger, random, pavlov
- `__init__.py` : registre `STRATEGY_REGISTRY` qui mappe noms → classes
- `test_strategies.py` : tests unitaires (tit_for_tat repond bien a l'historique, grim_trigger se declenche, etc.)

### Phase 3 — Agent Mistral (1h)

- `mistral_agent.py` : appels `httpx` vers `https://api.mistral.ai/v1/chat/completions`
- 3 profils via system prompt : empathique, calculateur, rancunier
- Parse la reponse pour extraire C/D + justification
- Gestion erreurs API + rate limiting (`time.sleep(0.5)`)
- Cle API via `MISTRAL_API_KEY` env var

### Phase 4 — Engine + Generate (Bronze) (1-2h)

- `engine.py` : classe `Tournament`
  - `play_match(player_a, player_b, num_rounds)` → liste de turn records
  - `run_tournament()` → round-robin, retourne `(turns, matches)`
- Schema d'un turn record :
  ```
  run_id, match_id, turn_number, player_a, player_b, strategy_a, strategy_b,
  choice_a, choice_b, score_a, score_b, cumulative_score_a, cumulative_score_b,
  reasoning_a, reasoning_b
  ```
- `generate.py` : lit config.yaml, cree run_id (UUID4), lance le tournoi, ecrit dans `data/bronze/<run_id>/turns.json`, `matches.json`, `metadata.json`

### Phase 5 — Load (Silver) (1h)

- `load.py` : lit `data/bronze/*/`, valide types (C/D, scores >= 0, pas de nulls), deduplique
- Ecrit en Parquet Hive-partitionne : `data/silver/turns/run_id=<uuid>/data.parquet`
- Chaque run = un sous-dossier partition → pas d'ecrasement des runs precedents (bonus)

### Phase 6 — dbt Gold (2h)

- `sources.yml` avec `external_location` pour lire les Parquet Silver (evite les problemes de chemins absolus du projet Spotify)
- Staging : `stg_turns` (ajoute colonnes `cooperated_a/b`, `betrayal_a/b`), `stg_matches`
- Gold :
  - `gold_match_summary` : JOIN turns+matches, taux coop, trahisons, cooperation mutuelle par match
  - `gold_strategy_metrics` : unpivot A/B, score moyen, win rate, taux coop, **forgiveness rate** (self-join LAG), rank
  - `gold_turn_evolution` : rolling AVG sur 50 tours, LAG 3 tours (memoire), score cumule
  - `gold_head_to_head` : matrice confrontation directe entre strategies
  - `gold_run_comparison` : comparaison cross-run avec rank global (bonus)

### Phase 7 — Makefile + transform.py (30 min)

- `transform.py` : wrapper subprocess qui appelle `dbt build --profiles-dir .`
- `Makefile` : targets `generate`, `load`, `transform`, `all`, `clean`

### Phase 8 — Multi-run test (bonus) (30 min)

- Lancer `make generate` 2-3 fois avec des parametres differents
- Verifier que les partitions Silver s'accumulent
- Verifier `gold_run_comparison` avec DuckDB

### Phase 9 — Documentation (1-2h)

- `README.md` : setup, architecture, usage, reproduction
- `ARCHITECTURE.md` : explication Bronze/Silver/Gold, schema des donnees, DAG dbt
- `docs/delta_lake_design.md` : conception Delta Lake (ACID, time travel, schema enforcement) — conceptuel, pas implemente

---

## Decisions techniques cles

| Decision | Raison |
|----------|--------|
| 200 rounds par defaut (pas 2000) | 3 profils Mistral × ~8 adversaires × 2000 tours = 48 000 appels API = ~7h. A 200 tours c'est ~40 min. Configurable dans `config.yaml`. |
| Hive partitioning par `run_id` | Chaque run est un sous-dossier. Pas d'ecrasement. DuckDB lit le `run_id` comme colonne partition nativement. |
| `external_location` dans dbt sources | Evite les problemes de chemins absolus rencontres dans le projet Spotify. dbt-duckdb resout les chemins automatiquement. |
| `httpx` direct (pas SDK Mistral) | Moins de deps, plus de controle, le student apprend l'API REST. |
| `pyproject.toml` + uv | Standard moderne, coherent avec l'ecosysteme uv deja utilise. |
| Pavlov comme strategie bonus | Produit des patterns analytiques interessants (win-stay/lose-shift). |

---

## Verification end-to-end

```bash
# 1. Test rapide (sans Mistral, 20 rounds)
make generate    # → data/bronze/<run_id>/
make load        # → data/silver/turns/run_id=<uuid>/
make transform   # → dbt build OK, data/dilemma.duckdb

# 2. Verification Gold
duckdb data/dilemma.duckdb -c "SELECT * FROM gold_strategy_metrics ORDER BY rank_in_run"

# 3. Multi-run (bonus)
make generate    # 2eme run
make load && make transform
duckdb data/dilemma.duckdb -c "SELECT run_id, strategy, avg_score, rank_in_run FROM gold_run_comparison ORDER BY strategy, run_id"

# 4. Run complet avec Mistral
export MISTRAL_API_KEY=<cle>
# config.yaml : activer profils Mistral, 200 rounds
make all

# 5. Tests qualite
cd dbt_dilemma && dbt test --profiles-dir .
```
