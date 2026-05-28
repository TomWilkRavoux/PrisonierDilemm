# Documentation — src/transform.py

## Role

Point d'entree de la phase **Transform** du pipeline ETL. Wrapper Python qui appelle `dbt build` pour transformer les donnees Silver (Parquet) en modeles Gold (DuckDB).

Commande : `make transform` → `uv run python -m src.transform`

## Flux d'execution

```
src/transform.py
    │
    ▼  subprocess.run()
dbt build --profiles-dir .
    │
    ▼  dans dbt_dilemma/
sources.yml (lit Silver Parquet)
    │
    ├── stg_turns ──┬── gold_match_summary ──── gold_head_to_head
    │               ├── gold_strategy_metrics ── gold_run_comparison
    │               └── gold_turn_evolution
    └── stg_matches ── gold_match_summary
    │
    ▼
data/dilemma.duckdb (7 vues SQL)
```

## Implementation

Le script est volontairement minimal :

1. Determine le chemin du dossier `dbt_dilemma/` (relatif au fichier source)
2. Execute `dbt build --profiles-dir .` en subprocess
3. Retourne le code de sortie de dbt (0 = succes, 1 = erreur)

Le flag `--profiles-dir .` indique a dbt de chercher `profiles.yml` dans le dossier courant (`dbt_dilemma/`) plutot que dans `~/.dbt/`.

## Configuration dbt

### dbt_project.yml

```yaml
name: dbt_dilemma
profile: dbt_dilemma
model-paths: ["models"]
```

### profiles.yml

```yaml
dbt_dilemma:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "../data/dilemma.duckdb"
```

Le chemin `../data/dilemma.duckdb` est relatif au dossier `dbt_dilemma/`. Le fichier DuckDB est cree automatiquement s'il n'existe pas.

### sources.yml

```yaml
sources:
  - name: silver
    tables:
      - name: turns
        meta:
          external_location: "../data/silver/turns/*/*.parquet"
      - name: matches
        meta:
          external_location: "../data/silver/matches/*/*.parquet"
```

`external_location` permet a dbt-duckdb de lire directement les fichiers Parquet sans les importer dans la base DuckDB. Le glob `*/*.parquet` capture toutes les partitions run_id.

## Modeles dbt — DAG et description

### Couche Staging

| Modele | Source | Transformations |
|--------|--------|-----------------|
| `stg_turns` | `silver.turns` | Ajoute `cooperated_a/b` (0/1) et `betrayal_a/b` (trahison unilaterale) |
| `stg_matches` | `silver.matches` | Passthrough sans transformation |

### Couche Gold

| Modele | Depends de | Description |
|--------|-----------|-------------|
| `gold_match_summary` | stg_turns, stg_matches | Resume par match : scores, taux coop, trahisons, cooperation mutuelle |
| `gold_strategy_metrics` | stg_turns | Performance par strategie : avg_score, coop_rate, forgiveness_rate, classement |
| `gold_turn_evolution` | stg_turns | Evolution temporelle : rolling coop rate (50 tours), memoire 3 tours |
| `gold_head_to_head` | gold_match_summary | Matrice confrontation : score_diff, resultat (win/draw/loss) |
| `gold_run_comparison` | gold_strategy_metrics | Comparaison cross-run avec classement global |

### Techniques SQL utilisees

| Technique | Utilise dans | But |
|-----------|-------------|-----|
| `UNION ALL` (unpivot) | strategy_metrics, turn_evolution, head_to_head | Transformer les colonnes A/B en lignes par joueur |
| `LAG()` | strategy_metrics, turn_evolution | Acceder au choix du tour precedent (forgiveness, memoire) |
| `AVG() OVER (ROWS BETWEEN)` | turn_evolution | Moyenne glissante sur 50 tours |
| `RANK() OVER (PARTITION BY)` | strategy_metrics | Classement par run |
| `RANK() OVER (ORDER BY)` | run_comparison | Classement global cross-run |
| `JOIN` | match_summary | Combiner turns et matches |

## Dependances

| Module | Usage |
|--------|-------|
| `subprocess` | Execution de la commande dbt |
| `dbt-duckdb` | Adaptateur dbt pour DuckDB (installe dans le venv) |
