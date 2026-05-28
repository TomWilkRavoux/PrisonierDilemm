# Documentation — src/generate.py

## Role

Point d'entree de la phase **Extract** du pipeline ETL. Lit la configuration, instancie les strategies, lance le tournoi et ecrit les resultats en JSON dans la couche Bronze.

Commande : `make generate` → `uv run python -m src.generate`

## Flux d'execution

```
config.yaml
    │
    ▼
load_config() ──► build_players() ──► Tournament() ──► run_tournament()
                                                            │
                                                            ▼
                                          data/bronze/<run_id>/
                                          ├── turns.json
                                          ├── matches.json
                                          └── metadata.json
```

## Fonctions

### `load_config(path=None) -> dict`

Charge et parse `config.yaml` avec PyYAML. Par defaut, cherche le fichier a la racine du projet. Retourne un dictionnaire Python avec la structure du YAML.

### `build_players(config) -> list[Strategy]`

Construit la liste des joueurs a partir de la configuration :

1. **Strategies codees** : pour chaque nom dans `config["strategies"]["coded"]`, recupere la classe correspondante dans `STRATEGY_REGISTRY` et l'instancie
2. **Agents Mistral** : si la variable d'environnement `MISTRAL_API_KEY` est definie, cree un `MistralAgent` pour chaque profil dans `config["strategies"]["mistral"]`

Si `MISTRAL_API_KEY` n'est pas definie, les agents Mistral sont simplement ignores et le tournoi se joue uniquement avec les strategies codees.

### `main()`

Fonction principale :

1. Charge la configuration
2. Construit les joueurs
3. Cree un `Tournament` avec un `run_id` UUID unique
4. Affiche les informations du run (ID, joueurs, rounds, nombre de matchs)
5. Lance le tournoi via `run_tournament()`
6. Serialise les resultats en JSON via `orjson` :
   - `turns.json` : tous les tours joues (1800 enregistrements pour 9 joueurs × 50 rounds)
   - `matches.json` : resume de chaque match (36 enregistrements pour 9 joueurs)
   - `metadata.json` : parametres du run (timestamp UTC, nombre de rounds, liste des joueurs, matrice de gains)

## Fichiers de sortie (Bronze)

### turns.json

```json
[
  {
    "run_id": "f81bd148-...",
    "match_id": "a3c2d1e0-...",
    "turn_number": 1,
    "player_a": "always_cooperate",
    "player_b": "tit_for_tat",
    "strategy_a": "always_cooperate",
    "strategy_b": "tit_for_tat",
    "choice_a": "C",
    "choice_b": "C",
    "score_a": 3,
    "score_b": 3,
    "cumulative_score_a": 3,
    "cumulative_score_b": 3,
    "reasoning_a": "",
    "reasoning_b": ""
  }
]
```

### matches.json

```json
[
  {
    "run_id": "f81bd148-...",
    "match_id": "a3c2d1e0-...",
    "player_a": "always_cooperate",
    "player_b": "tit_for_tat",
    "strategy_a": "always_cooperate",
    "strategy_b": "tit_for_tat",
    "total_score_a": 150,
    "total_score_b": 150,
    "num_turns": 50
  }
]
```

### metadata.json

```json
{
  "run_id": "f81bd148-...",
  "timestamp": "2026-05-28T09:34:52.123456+00:00",
  "num_rounds": 50,
  "players": ["always_cooperate", "always_defect", "..."],
  "num_matches": 36,
  "num_turns": 1800,
  "payoff_matrix": {"CC": [3, 3], "CD": [0, 5], "DC": [5, 0], "DD": [1, 1]}
}
```

## Dependances

| Module | Usage |
|--------|-------|
| `orjson` | Serialisation JSON rapide (ecriture binaire avec indentation) |
| `yaml` | Lecture de config.yaml |
| `dotenv` | Chargement du fichier `.env` (cle API Mistral) |
| `src.engine` | Classe `Tournament` |
| `src.strategies` | `STRATEGY_REGISTRY` pour les strategies codees |
| `src.strategies.mistral_agent` | Classe `MistralAgent` |

## Chargement du .env

`load_dotenv()` est appele au demarrage du module. Il lit le fichier `.env` a la racine du projet et charge les variables dans `os.environ`. Cela permet de definir `MISTRAL_API_KEY` sans l'exporter manuellement dans le shell.
