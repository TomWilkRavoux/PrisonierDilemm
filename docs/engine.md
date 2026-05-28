# Documentation — src/engine.py

## Role

Moteur de tournoi round-robin. Orchestre les matchs entre strategies et produit les enregistrements de donnees (turns et matches) qui forment la couche Bronze.

## Structures de donnees

### `TurnRecord` (dataclass)

Un enregistrement par tour joue. C'est l'unite atomique de donnee du pipeline.

| Champ | Type | Description |
|-------|------|-------------|
| `run_id` | str (UUID) | Identifiant unique du run (tournoi complet) |
| `match_id` | str (UUID) | Identifiant unique du match |
| `turn_number` | int | Numero du tour (1-based) |
| `player_a` / `player_b` | str | Nom du joueur |
| `strategy_a` / `strategy_b` | str | Nom de la strategie |
| `choice_a` / `choice_b` | str | `"C"` ou `"D"` |
| `score_a` / `score_b` | int | Points gagnes ce tour (0, 1, 3 ou 5) |
| `cumulative_score_a` / `cumulative_score_b` | int | Score cumule depuis le debut du match |
| `reasoning_a` / `reasoning_b` | str | Justification textuelle (agents Mistral uniquement, vide pour les strategies codees) |

### `MatchRecord` (dataclass)

Un enregistrement par match. Resume les scores finaux.

| Champ | Type | Description |
|-------|------|-------------|
| `run_id` | str | Identifiant du run |
| `match_id` | str | Identifiant du match |
| `player_a` / `player_b` | str | Noms des joueurs |
| `strategy_a` / `strategy_b` | str | Noms des strategies |
| `total_score_a` / `total_score_b` | int | Score final de chaque joueur |
| `num_turns` | int | Nombre de tours joues |

### `PayoffMatrix`

Alias de type : `dict[str, list[int]]`

Exemple :
```python
{
    "CC": [3, 3],   # cooperation mutuelle
    "CD": [0, 5],   # A coopere, B a trahi
    "DC": [5, 0],   # A a trahi, B a coopere
    "DD": [1, 1],   # trahison mutuelle
}
```

## Classe `Tournament`

### Attributs

| Attribut | Type | Description |
|----------|------|-------------|
| `players` | list[Strategy] | Liste des strategies participant au tournoi |
| `num_rounds` | int | Nombre de tours par match |
| `payoff_matrix` | PayoffMatrix | Matrice de gains |
| `run_id` | str | UUID genere automatiquement a la creation |

### `_compute_scores(choice_a, choice_b) -> (int, int)`

Concatene les deux choix (ex: `"C"+"D"` → `"CD"`) et retourne les scores correspondants depuis la matrice de gains.

### `play_match(player_a, player_b) -> (list[TurnRecord], MatchRecord)`

Joue un match complet entre deux strategies :

1. **Reset** : appelle `reset()` sur les deux joueurs pour reinitialiser leur etat interne
2. **Boucle de jeu** (pour chaque tour de 1 a `num_rounds`) :
   - Chaque joueur choisit C ou D via `choose(history)`
   - Les scores sont calcules via la matrice de gains
   - Les scores cumules sont mis a jour
   - Si un joueur est un `MistralAgent`, sa justification est recuperee via `get_reasoning()`
   - Un `TurnRecord` est cree et ajoute a la liste
   - Les historiques respectifs sont mis a jour (chaque joueur voit l'historique depuis sa perspective)
3. Un `MatchRecord` resume le match

**Point important** : chaque joueur a son propre historique. Pour le joueur A, l'historique est `(mon_choix, choix_adversaire)`. Pour le joueur B, c'est inverse : `(choix_b, choix_a)`. Cela garantit que `history[-1][1]` est toujours le dernier choix de l'adversaire, quel que soit le joueur.

### `run_tournament() -> (list[TurnRecord], list[MatchRecord])`

Organise le tournoi en round-robin : chaque paire de joueurs joue exactement un match.

```python
for i in range(len(players)):
    for j in range(i + 1, len(players)):
        # joueur i vs joueur j
```

Pour N joueurs : N × (N-1) / 2 matchs.

| N joueurs | Matchs | Tours (50 rounds) | Tours (200 rounds) |
|-----------|--------|--------------------|--------------------|
| 6 (sans Mistral) | 15 | 750 | 3000 |
| 9 (avec Mistral) | 36 | 1800 | 7200 |

## Dependances

- `uuid` : generation des identifiants de run et de match
- `src.strategies.base.Strategy` : type des joueurs
- `src.strategies.mistral_agent.MistralAgent` : detection pour recuperer le reasoning
