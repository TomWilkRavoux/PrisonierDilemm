# Documentation — src/strategies/base.py

## Role

Classe abstraite qui definit le contrat que chaque strategie du dilemme du prisonnier doit respecter. C'est le socle commun a toutes les strategies, qu'elles soient codees ou basees sur l'IA.

## Classe `Strategy` (ABC)

### Attributs

| Attribut | Type | Description |
|----------|------|-------------|
| `name` | `str` | Identifiant unique de la strategie (ex: `"tit_for_tat"`, `"mistral_empathique"`). Utilise comme cle dans les enregistrements de donnees. |

### Methodes

#### `choose(history) -> str` (abstraite)

Methode principale que chaque strategie doit implementer.

- **Parametre** : `history` — liste de tuples `(mon_choix, choix_adversaire)` representant tous les tours precedents du match en cours
- **Retour** : `"C"` (cooperer) ou `"D"` (trahir)
- Au premier tour d'un match, `history` est une liste vide `[]`

**Exemple d'historique** :
```python
# Apres 3 tours ou j'ai coopere, l'adversaire a coopere, puis trahi, puis coopere
history = [("C", "C"), ("C", "D"), ("C", "C")]
# history[-1][1] = "C" → dernier choix de l'adversaire
```

#### `reset() -> None`

Reinitialise l'etat interne de la strategie entre deux matchs. Par defaut, ne fait rien. Surchargee par les strategies qui gardent un etat (comme `GrimTrigger` qui a un flag `_triggered`).

## Design pattern

Ce fichier utilise le **Template Method pattern** : la classe abstraite definit l'interface, chaque strategie concrete implemente `choose()` avec sa propre logique. Le `Tournament` manipule uniquement des objets `Strategy` sans connaitre les implementations concretes.

## Dependances

- Aucune dependance externe (uniquement `abc` de la stdlib)
- Importe par : toutes les strategies concretes, `engine.py`
