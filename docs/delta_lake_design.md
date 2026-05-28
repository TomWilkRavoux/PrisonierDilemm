# Conception Delta Lake — Prisoner's Dilemma ETL

## Objectif

Ce document decrit comment le pipeline pourrait evoluer vers un vrai Delta Lake
pour beneficier des proprietes ACID, du time travel et du schema enforcement.

## Etat actuel vs Delta Lake

| Propriete | Actuel (Parquet Hive) | Delta Lake |
|-----------|----------------------|------------|
| Format | Parquet partitionne | Parquet + transaction log (_delta_log/) |
| ACID | Non | Oui — transactions atomiques |
| Time travel | Via partitions run_id | Via versions (versionAsOf) |
| Schema enforcement | Validation manuelle (load.py) | Automatique a l'ecriture |
| Upsert/Merge | Non supporte | MERGE INTO natif |
| Concurrence | Pas de garantie | Optimistic concurrency control |

## Architecture Delta Lake proposee

```
data/
├── delta/
│   ├── turns/
│   │   ├── _delta_log/
│   │   │   ├── 00000000000000000000.json   # version 0 (run 1)
│   │   │   └── 00000000000000000001.json   # version 1 (run 2)
│   │   ├── part-00000-<hash>.parquet
│   │   └── part-00001-<hash>.parquet
│   └── matches/
│       ├── _delta_log/
│       └── ...
└── gold/
    └── dilemma.duckdb
```

### Transaction Log

Chaque fichier JSON dans `_delta_log/` contient :
- **add** : fichiers Parquet ajoutes
- **remove** : fichiers supprimes (soft delete)
- **metadata** : schema, description, configuration
- **commitInfo** : timestamp, operation, user

### Time Travel

```sql
-- Lire la derniere version
SELECT * FROM delta_scan('data/delta/turns/');

-- Lire une version specifique
SELECT * FROM delta_scan('data/delta/turns/', version := 0);

-- Comparer deux runs
SELECT * FROM delta_scan('data/delta/turns/', version := 1)
EXCEPT
SELECT * FROM delta_scan('data/delta/turns/', version := 0);
```

### Schema Enforcement

Le schema serait applique automatiquement a l'ecriture :

```python
from deltalake import write_deltalake

write_deltalake(
    "data/delta/turns",
    df,
    mode="append",
    schema_mode="strict",  # refuse les colonnes inattendues
)
```

Si un champ est modifie (ex: `score_a` passe de int a float), l'ecriture echoue
sauf si `schema_mode="merge"` est utilise explicitement.

## Implementation avec Python

```python
# pip install deltalake
from deltalake import DeltaTable, write_deltalake

# Ecriture (append par run)
write_deltalake("data/delta/turns", turns_df, mode="append")

# Lecture
dt = DeltaTable("data/delta/turns")
df = dt.to_pandas()

# Time travel
df_v0 = dt.load_as_version(0).to_pandas()

# Historique
for entry in dt.history():
    print(entry["timestamp"], entry["operation"])
```

## Integration avec dbt-duckdb

DuckDB supporte nativement Delta Lake via l'extension `delta` :

```sql
-- Installation (une fois)
INSTALL delta;
LOAD delta;

-- Lecture
SELECT * FROM delta_scan('data/delta/turns/');
```

Dans `sources.yml` :
```yaml
sources:
  - name: delta
    tables:
      - name: turns
        meta:
          external_location: "delta_scan('data/delta/turns/')"
```

## Avantages pour le projet

1. **Reproductibilite** : chaque run est une version, pas un dossier
2. **Rollback** : possible de revenir a un etat precedent sans perdre de donnees
3. **Audit** : le log de transactions trace chaque modification
4. **Qualite** : le schema enforcement empeche les corruptions silencieuses
5. **Performance** : Z-ordering et data skipping pour les grosses tables

## Limites

- Ajoute une dependance (`deltalake` ou `delta-rs`)
- Overhead pour de petits volumes de donnees (< 100k lignes)
- L'extension Delta de DuckDB est encore experimentale
