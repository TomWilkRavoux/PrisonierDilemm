# Fil Rouge — Pipeline ETL Dilemme du Prisonnier

## 1. Presentation du projet

Ce projet est un pipeline de data engineering complet qui simule le **dilemme du prisonnier iteratif**, un probleme classique de la theorie des jeux. Le pipeline genere ses propres donnees via un tournoi round-robin entre strategies codees et agents IA (Mistral), puis les transforme a travers trois couches de donnees (Bronze → Silver → Gold) pour produire des analyses exploitables.

### Pourquoi ce sujet ?

Le dilemme du prisonnier iteratif est un terrain d'experimentation ideal pour un projet ETL :
- Il **genere des donnees structurees** (tours, matchs, scores) avec un volume configurable
- Il produit des **metriques analytiques riches** (taux de cooperation, trahisons, pardon, evolution temporelle)
- L'ajout d'agents IA via l'API Mistral apporte une **dimension temps reel** et des comportements non-deterministes
- Le multi-run permet de tester le **versioning des donnees** et la comparaison cross-run

---

## 2. Architecture globale

```
┌─────────────────────────────────────────────────────────────────────┐
│                         config.yaml                                │
│              (parametres du tournoi, strategies, Mistral)           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 1 — GENERATE (Bronze)                     │
│                         src/generate.py                            │
│                                                                    │
│   config.yaml ──► build_players() ──► Tournament.run_tournament()  │
│                                              │                     │
│                  src/strategies/*.py    src/engine.py               │
│                  (6 codees + 3 Mistral)  (round-robin)             │
│                                              │                     │
│                                              ▼                     │
│                           data/bronze/<run_id>/                    │
│                           ├── turns.json                           │
│                           ├── matches.json                         │
│                           └── metadata.json                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PHASE 2 — LOAD (Silver)                        │
│                          src/load.py                               │
│                                                                    │
│   data/bronze/*/ ──► validation ──► deduplication ──► Parquet      │
│                      (C/D, scores,                                 │
│                       pas de nulls)                                │
│                                              │                     │
│                                              ▼                     │
│                       data/silver/turns/run_id=<uuid>/data.parquet │
│                       data/silver/matches/run_id=<uuid>/data.parquet│
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PHASE 3 — TRANSFORM (Gold)                       │
│                        src/transform.py                            │
│                     dbt_dilemma/models/                             │
│                                                                    │
│   Silver Parquet ──► dbt build ──► 7 modeles SQL ──► DuckDB        │
│                                                                    │
│   Staging :                                                        │
│   ├── stg_turns  (+ cooperated_a/b, betrayal_a/b)                 │
│   └── stg_matches (passthrough)                                    │
│                                                                    │
│   Gold :                                                           │
│   ├── gold_match_summary      (resume par match)                   │
│   ├── gold_strategy_metrics   (perf globale + forgiveness)         │
│   ├── gold_turn_evolution     (rolling coop rate + memoire)        │
│   ├── gold_head_to_head       (matrice confrontation directe)      │
│   └── gold_run_comparison     (comparaison cross-run)              │
│                                              │                     │
│                                              ▼                     │
│                              data/dilemma.duckdb                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Flux de donnees detaille

### Flux 1 — Generation (Extract)

**Point d'entree** : `make generate` → `src/generate.py`

1. `load_config()` lit `config.yaml` (nombre de rounds, matrice de gains, liste des strategies)
2. `build_players()` instancie les strategies :
   - 6 strategies codees via le `STRATEGY_REGISTRY` (dictionnaire nom → classe)
   - 3 agents Mistral si `MISTRAL_API_KEY` est defini dans l'environnement
3. `Tournament` est cree avec un `run_id` UUID unique
4. `run_tournament()` joue chaque paire en round-robin :
   - Pour N joueurs, il y a N×(N-1)/2 matchs
   - Chaque match joue `rounds` tours (defini dans config.yaml)
   - A chaque tour, chaque joueur appelle `choose(history)` pour decider C ou D
   - Les scores sont calcules selon la matrice de gains
5. Les resultats sont ecrits en JSON dans `data/bronze/<run_id>/`

**Volume de donnees** (9 joueurs, 50 rounds) :
- 36 matchs × 50 tours = **1800 turn records**
- 36 match records
- 1 fichier metadata

### Flux 2 — Chargement (Load)

**Point d'entree** : `make load` → `src/load.py`

1. Parcourt tous les sous-dossiers de `data/bronze/`
2. Pour chaque run :
   - Lit les JSON avec `orjson`
   - Charge en `polars.DataFrame`
   - **Deduplication** : `df.unique()` supprime les doublons eventuels
   - **Validation** : verifie que les choix sont C/D, les scores >= 0, aucun null
3. Ecrit en Parquet Hive-partitionne : `data/silver/turns/run_id=<uuid>/data.parquet`
4. La colonne `run_id` est droppee du Parquet car elle est encodee dans le chemin du dossier (partition Hive)

**Point cle** : chaque run cree son propre sous-dossier. Il n'y a jamais d'ecrasement des runs precedents.

### Flux 3 — Transformation (Transform)

**Point d'entree** : `make transform` → `src/transform.py` → `dbt build`

1. `transform.py` est un wrapper qui appelle `dbt build --profiles-dir .`
2. dbt lit les Parquet Silver via `external_location` dans `sources.yml`
3. DuckDB reconstruit automatiquement la colonne `run_id` depuis les noms de dossiers Hive
4. Les 7 modeles SQL sont executes dans l'ordre du DAG :

```
sources.yml (Silver Parquet)
    │
    ├── stg_turns ──────┬── gold_match_summary ──── gold_head_to_head
    │                   ├── gold_strategy_metrics ── gold_run_comparison
    │                   └── gold_turn_evolution
    │
    └── stg_matches ──── gold_match_summary
```

### Flux 4 — Multi-run (bonus)

Le pipeline supporte l'accumulation de plusieurs runs :

1. Lancer `make generate` plusieurs fois → plusieurs dossiers dans `data/bronze/`
2. `make load` traite tous les runs Bronze et cree des partitions Silver separees
3. `make transform` reconstruit les vues Gold qui agrègent tous les runs
4. `gold_run_comparison` compare les strategies a travers les runs avec un classement global

---

## 4. Matrice de gains

La matrice de gains definit les points obtenus a chaque tour selon les choix des deux joueurs :

```
              Adversaire
              C (coopere)    D (trahit)
Joueur C      3 / 3          0 / 5
Joueur D      5 / 0          1 / 1
```

- **Cooperation mutuelle (CC)** : 3 points chacun — le meilleur resultat collectif
- **Trahison unilaterale (DC)** : 5 points pour le traitre, 0 pour le cooperant
- **Trahison mutuelle (DD)** : 1 point chacun — le pire resultat collectif
- **Tentation** : trahir rapporte toujours plus individuellement, mais la cooperation mutuelle bat la trahison mutuelle

---

## 5. Les strategies

### Strategies codees

| Strategie | Fichier | Logique |
|-----------|---------|---------|
| **always_cooperate** | `always_cooperate.py` | Retourne toujours C. Strategie la plus naive, exploitable. |
| **always_defect** | `always_defect.py` | Retourne toujours D. Exploite les cooperants, mauvais score contre les punitifs. |
| **tit_for_tat** | `tit_for_tat.py` | Coopere au 1er tour, puis copie le dernier choix de l'adversaire. Gagnante du tournoi d'Axelrod (1980). |
| **grim_trigger** | `grim_trigger.py` | Coopere jusqu'a la premiere trahison adverse, puis trahit indefiniment. Utilise un etat interne `_triggered`. |
| **random** | `random_strategy.py` | Choix aleatoire 50/50. Baseline non-strategique. |
| **pavlov** | `pavlov.py` | Win-stay, lose-shift : coopere si le tour precedent avait le meme choix pour les deux, trahit sinon. Capable d'exploiter les cooperants tout en cooperant avec les reciproques. |

### Agents Mistral (IA)

| Agent | Profil | Comportement observe |
|-------|--------|---------------------|
| **mistral_empathique** | Cooperation et confiance | Se comporte comme always_cooperate (100% coop). Se fait exploiter par les traitres. |
| **mistral_calculateur** | Maximisation froide | Trahit souvent (~41% coop). Strategie la plus imprevisible mais pas la plus performante. |
| **mistral_rancunier** | Punit les trahisons | Se comporte comme grim_trigger. Coopere puis punit definitivement. 3eme au classement. |

Les agents Mistral appellent l'API `mistral-small-latest` via httpx. Chaque appel envoie les 5 derniers tours comme contexte et un system prompt qui definit la personnalite.

---

## 6. Les modeles Gold (dbt)

### stg_turns — Staging des tours

Enrichit les donnees Silver avec des colonnes derivees :
- `cooperated_a/b` : 1 si le joueur a coopere, 0 sinon
- `betrayal_a/b` : 1 si le joueur a trahi alors que l'adversaire cooperait

### stg_matches — Staging des matchs

Passthrough des donnees Silver sans transformation.

### gold_match_summary — Resume par match

Joint `stg_turns` et `stg_matches` pour produire des metriques par match :
- Taux de cooperation de chaque joueur
- Nombre de trahisons
- Cooperation mutuelle (les deux jouent C) et trahison mutuelle (les deux jouent D)
- Taux de cooperation mutuelle

### gold_strategy_metrics — Performance par strategie

Unpivote les tours (A/B → une ligne par joueur) puis calcule par strategie :
- **avg_score** : score moyen par tour
- **total_score** : score cumule sur tous les matchs
- **coop_rate** : taux de cooperation global
- **total_betrayals** : nombre de trahisons (D quand l'adversaire joue C)
- **forgiveness_rate** : proportion de fois ou le joueur re-coopere apres avoir trahi (mesure du "pardon")
- **rank_in_run** : classement par total_score dans le run

### gold_turn_evolution — Evolution tour par tour

Permet d'observer l'evolution temporelle des strategies :
- **rolling_coop_rate_50** : moyenne glissante du taux de cooperation sur 50 tours
- **prev_choice_1/2/3** : memoire des 3 derniers choix (pattern detection)
- Score cumule tour par tour

### gold_head_to_head — Matrice confrontation directe

Unpivote les matchs pour avoir une ligne par paire directionnelle (strategy vs opponent) :
- Score, score adversaire, difference de score
- Resultat : win, draw ou loss

### gold_run_comparison — Comparaison cross-run

Reprend `gold_strategy_metrics` et ajoute un `global_rank` qui classe les strategies a travers tous les runs. Permet de voir si une strategie est consistante d'un run a l'autre.

---

## 7. Stack technique

| Composant | Technologie | Role |
|-----------|-------------|------|
| Gestion de projet | uv + pyproject.toml | Gestion des deps et du venv Python 3.12 |
| Configuration | YAML | Parametres du tournoi, strategies, prompts Mistral |
| Serialisation Bronze | orjson | Ecriture/lecture JSON rapide |
| Dataframes | Polars | Chargement, validation et ecriture Parquet |
| Format Silver | Apache Parquet (Hive) | Stockage colonnaire partitionne par run_id |
| Transformations Gold | dbt-duckdb | Modeles SQL analytiques |
| Base analytique | DuckDB | Moteur OLAP embarque, lecture native Parquet |
| API IA | httpx → Mistral API | Appels REST aux agents IA |
| Tests | pytest | Tests unitaires des strategies |
| Orchestration | Makefile | Enchainement generate → load → transform |

---

## 8. Comment reproduire

```bash
# 1. Installer les dependances
uv sync

# 2. Configurer Mistral (optionnel)
# Creer un fichier .env avec : MISTRAL_API_KEY=<votre_cle>

# 3. Lancer le pipeline complet
make all

# 4. Consulter les resultats
cd dbt_dilemma
duckdb ../data/dilemma.duckdb

# Exemples de requetes :
# SELECT * FROM gold_strategy_metrics ORDER BY rank_in_run;
# SELECT * FROM gold_head_to_head WHERE strategy = 'tit_for_tat';
# SELECT * FROM gold_run_comparison ORDER BY strategy, run_id;
```
