# Architecture — Bronze / Silver / Gold

## Vue d'ensemble

```
config.yaml
    │
    ▼
┌──────────┐     ┌──────────┐     ┌──────────┐
│  BRONZE  │ ──► │  SILVER  │ ──► │   GOLD   │
│  (JSON)  │     │(Parquet) │     │ (DuckDB) │
└──────────┘     └──────────┘     └──────────┘
 generate.py      load.py         dbt build
```

## Bronze — Donnees brutes (JSON)

```
data/bronze/<run_id>/
├── turns.json       # 1 enregistrement par tour joue
├── matches.json     # 1 enregistrement par match
└── metadata.json    # parametres du run
```

Le moteur de tournoi (`engine.py`) joue chaque paire de strategies en round-robin.
Les donnees sont ecrites en JSON via `orjson`.

### Schema d'un turn record

| Champ | Type | Description |
|-------|------|-------------|
| run_id | UUID | Identifiant unique du run |
| match_id | UUID | Identifiant unique du match |
| turn_number | int | Numero du tour (1-based) |
| player_a / player_b | string | Nom du joueur |
| strategy_a / strategy_b | string | Nom de la strategie |
| choice_a / choice_b | C/D | Cooperer ou Trahir |
| score_a / score_b | int | Points gagnes ce tour |
| cumulative_score_a / cumulative_score_b | int | Score cumule |
| reasoning_a / reasoning_b | string | Justification (agents Mistral) |

## Silver — Donnees validees (Parquet Hive-partitionne)

```
data/silver/
├── turns/
│   ├── run_id=<uuid_1>/data.parquet
│   └── run_id=<uuid_2>/data.parquet
└── matches/
    ├── run_id=<uuid_1>/data.parquet
    └── run_id=<uuid_2>/data.parquet
```

Le script `load.py` :
1. Lit les JSON Bronze
2. Valide les types (C/D uniquement, scores >= 0, pas de nulls)
3. Deduplique les enregistrements
4. Ecrit en Parquet partitionne par `run_id`

Le partitionnement Hive permet a DuckDB de lire `run_id` comme colonne native sans schema explicite.
Chaque run est un sous-dossier independant : pas d'ecrasement des runs precedents.

## Gold — Modeles analytiques (dbt-duckdb)

DAG dbt :

```
sources.yml
    │
    ├── stg_turns (+ cooperated_a/b, betrayal_a/b)
    │   ├── gold_match_summary
    │   ├── gold_strategy_metrics ──► gold_run_comparison
    │   ├── gold_turn_evolution
    │   └── gold_head_to_head (via gold_match_summary)
    │
    └── stg_matches
        └── gold_match_summary
```

### Modeles

| Modele | Description | Metriques cles |
|--------|-------------|----------------|
| stg_turns | Staging + colonnes derivees | cooperated_a/b, betrayal_a/b |
| stg_matches | Staging matches | passthrough |
| gold_match_summary | Resume par match | taux coop, trahisons, cooperation mutuelle |
| gold_strategy_metrics | Performance par strategie | avg_score, coop_rate, forgiveness_rate, rank |
| gold_turn_evolution | Evolution tour par tour | rolling coop rate (50t), memoire 3 tours |
| gold_head_to_head | Matrice confrontation | score_diff, resultat (win/draw/loss) |
| gold_run_comparison | Comparaison cross-run | rank global, avg_score par run |

## Matrice de gains

| | Adversaire C | Adversaire D |
|---|---|---|
| **Joueur C** | 3 / 3 | 0 / 5 |
| **Joueur D** | 5 / 0 | 1 / 1 |
