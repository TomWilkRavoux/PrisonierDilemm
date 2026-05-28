# Documentation — src/strategies/mistral_agent.py

## Role

Implemente une strategie du dilemme du prisonnier pilotee par un LLM via l'API Mistral. Chaque instance represente un "profil" (empathique, calculateur, rancunier) defini par son system prompt.

## Classe `MistralAgent(Strategy)`

### Constructeur

```python
MistralAgent(name: str, system_prompt: str)
```

| Parametre | Description |
|-----------|-------------|
| `name` | Identifiant de l'agent (ex: `"mistral_empathique"`) |
| `system_prompt` | Prompt systeme qui definit la personnalite de l'agent. Defini dans `config.yaml`. |

La cle API est lue depuis la variable d'environnement `MISTRAL_API_KEY`.

### Methode `choose(history) -> str`

Appelle l'API Mistral pour decider C ou D. Delegue a `_call_api()`.

### Methode `_format_history(history) -> str`

Formate les **5 derniers tours** en texte lisible pour le LLM :

```
Tour 46: toi=C, adversaire=D
Tour 47: toi=D, adversaire=D
Tour 48: toi=D, adversaire=C
Tour 49: toi=C, adversaire=C
Tour 50: toi=C, adversaire=C
```

Seuls les 5 derniers tours sont envoyes pour limiter la taille du prompt et les couts API.

### Methode `_call_api(history) -> str`

Envoie une requete POST a `https://api.mistral.ai/v1/chat/completions` :

| Parametre API | Valeur | Raison |
|---------------|--------|--------|
| `model` | `mistral-small-latest` | Modele rapide et peu couteux, suffisant pour un choix binaire |
| `max_tokens` | 100 | La reponse attendue est courte (C/D + justification) |
| `temperature` | 0.3 | Basse pour des reponses plus deterministes et coherentes |

**Format de la requete** :
- Message systeme : le system prompt du profil
- Message utilisateur : historique des derniers tours + demande de decision

**Parsing de la reponse** :
- Si la reponse commence par "C" (insensible a la casse) → retourne `"C"`
- Sinon → retourne `"D"`
- La justification complete est stockee dans `_last_reasoning`

**Gestion des erreurs** :
- Si pas de cle API → retourne `"C"` (mode degrade)
- Si erreur reseau/API → retourne `"C"` avec reasoning "API error"
- `time.sleep(0.5)` apres chaque appel reussi pour respecter le rate limiting

### Methode `get_reasoning() -> str`

Retourne la derniere justification textuelle du LLM. Appelee par `engine.py` pour remplir les champs `reasoning_a/b` des turn records. Les strategies codees n'ont pas cette methode (le champ reste vide).

## Les 3 profils (config.yaml)

### mistral_empathique

> Tu es un joueur empathique [...] Tu privilegies la cooperation et la confiance. Tu pardonnes facilement les trahisons.

**Comportement observe** : coopere a 100%, identique a always_cooperate. Le LLM suit le prompt systeme a la lettre et choisit toujours C.

### mistral_calculateur

> Tu es un joueur calculateur [...] Tu analyses froidement les probabilites et cherches a maximiser ton score.

**Comportement observe** : trahit souvent (~41% de cooperation). Strategie la plus imprevisible. Le LLM tente de maximiser son score mais n'a pas assez de contexte (5 tours) pour developper une strategie optimale.

### mistral_rancunier

> Tu es un joueur rancunier [...] si l'adversaire te trahit une seule fois, tu le punis severement.

**Comportement observe** : se comporte comme grim_trigger. Coopere au debut, puis punit definitivement apres la premiere trahison. Le LLM interprete "punir severement" comme une trahison permanente.

## Cout et performance

Avec 9 joueurs et 50 rounds :
- ~1200 appels API (24 matchs impliquant un agent × 50 tours + 3 matchs Mistral vs Mistral × 50 tours × 2)
- ~0.5s de sleep par appel → ~10-15 min de temps d'execution pour les appels API
- Modele `mistral-small-latest` : cout negligeable (~0.01€ pour 1200 appels)
