# Documentation — src/load.py

## Role

Point d'entree de la phase **Load** du pipeline ETL. Lit les donnees Bronze (JSON), les valide, les deduplique, et les ecrit en Parquet Hive-partitionne dans la couche Silver.

Commande : `make load` → `uv run python -m src.load`

## Flux d'execution

```
data/bronze/
├── <run_id_1>/turns.json, matches.json
├── <run_id_2>/turns.json, matches.json
│
▼  pour chaque run :
orjson.loads() ──► pl.DataFrame() ──► unique() ──► validate_turns() ──► write_parquet()
                                                                            │
                                                                            ▼
                                                       data/silver/turns/run_id=<uuid>/data.parquet
                                                       data/silver/matches/run_id=<uuid>/data.parquet
```

## Fonctions

### `validate_turns(df) -> pl.DataFrame`

Applique 5 controles de qualite sur le DataFrame des tours :

| Controle | Assertion | Erreur si |
|----------|-----------|-----------|
| Choix valides (A) | `choice_a` dans {"C", "D"} | Valeur autre que C ou D |
| Choix valides (B) | `choice_b` dans {"C", "D"} | Valeur autre que C ou D |
| Scores positifs (A) | `score_a >= 0` | Score negatif |
| Scores positifs (B) | `score_b >= 0` | Score negatif |
| Pas de nulls | Aucune valeur nulle dans tout le DataFrame | Donnee manquante |

Si un controle echoue, une `AssertionError` est levee et le pipeline s'arrete. Cette validation est critique car les couches Silver et Gold supposent des donnees propres.

### `load_run(run_dir) -> None`

Traite un seul run Bronze :

1. **Lecture** : charge `turns.json` et `matches.json` avec `orjson`
2. **Chargement** : cree des DataFrames Polars
3. **Deduplication** : `df.unique()` supprime les eventuels doublons
4. **Validation** : appelle `validate_turns()` sur les tours
5. **Ecriture** :
   - Supprime la colonne `run_id` du DataFrame (elle sera encodee dans le chemin du dossier)
   - Cree le dossier `data/silver/turns/run_id=<uuid>/`
   - Ecrit `data.parquet`

### `main()`

Parcourt tous les sous-dossiers de `data/bronze/` et appelle `load_run()` pour chacun. Si aucune donnee Bronze n'est trouvee, affiche un message d'erreur.

## Partitionnement Hive

Le format de sortie utilise le partitionnement Hive :

```
data/silver/turns/
├── run_id=f81bd148-ff85-4529-9bed-4f0638f96a30/
│   └── data.parquet
├── run_id=0897d142-4cf4-451e-8067-00b88e930ac8/
│   └── data.parquet
```

**Avantages** :
- DuckDB et dbt-duckdb reconnaissent nativement ce format
- La colonne `run_id` est reconstruite automatiquement depuis les noms de dossiers
- Chaque run est isole : pas d'ecrasement, ajout incremental
- Lecture selective possible (pruning par partition)

## Idempotence

Le script retraite **tous** les runs Bronze a chaque execution. Les fichiers Parquet sont ecrases si le run existe deja dans Silver. Cela garantit que Silver est toujours synchronise avec Bronze.

## Dependances

| Module | Usage |
|--------|-------|
| `orjson` | Lecture JSON rapide |
| `polars` | DataFrames, deduplication, validation, ecriture Parquet |
