# Documentation — Strategies codees

## Vue d'ensemble

Six strategies codees implementent la classe abstraite `Strategy`. Chacune represente une approche classique de la theorie des jeux. Elles sont toutes enregistrees dans le `STRATEGY_REGISTRY` (`src/strategies/__init__.py`), un dictionnaire qui mappe le nom de la strategie vers sa classe.

---

## always_cooperate.py — AlwaysCooperate

**Logique** : retourne toujours `"C"`, quoi que fasse l'adversaire.

**Comportement en tournoi** :
- Score maximal contre les autres cooperants (3 pts/tour en mutual cooperation)
- Score minimal contre les traitres (0 pts/tour, exploitee sans defense)
- Pas de forgiveness_rate (elle ne trahit jamais, donc ne peut pas "pardonner")
- Sert de baseline cooperative

**Theorie des jeux** : strategie dite "gentille" mais exploitable. Elle ne survit pas dans un environnement competitif car elle n'a aucun mecanisme de punition.

---

## always_defect.py — AlwaysDefect

**Logique** : retourne toujours `"D"`, quoi que fasse l'adversaire.

**Comportement en tournoi** :
- Exploite les cooperants (5 pts/tour quand l'adversaire coopere)
- Mauvais score contre les strategies punitives (1 pt/tour en mutual defection)
- Souvent 1er au classement car elle gagne ou egalise contre presque tout le monde
- Forgiveness_rate = 0 (ne coopere jamais)

**Theorie des jeux** : correspond a l'equilibre de Nash du dilemme du prisonnier. Individuellement rationnelle mais collectivement sous-optimale.

---

## tit_for_tat.py — TitForTat

**Logique** :
1. Premier tour : coopere (`"C"`)
2. Tours suivants : copie le dernier choix de l'adversaire (`history[-1][1]`)

**Comportement en tournoi** :
- Coopere avec les cooperants → mutual cooperation (3 pts/tour)
- Punit immediatement les trahisons → dissuasion
- Pardonne des que l'adversaire re-coopere → forgiveness_rate > 0
- Gagnante du tournoi d'Axelrod en 1980

**Theorie des jeux** : combine les 4 proprietes identifiees par Axelrod comme gagnantes :
1. Gentille (ne trahit jamais en premier)
2. Reactive (repond a la trahison)
3. Clemence (pardonne quand l'adversaire revient a la cooperation)
4. Simple (facile a comprendre pour l'adversaire)

---

## grim_trigger.py — GrimTrigger

**Logique** :
1. Coopere tant que l'adversaire n'a jamais trahi
2. Des la premiere trahison adverse, trahit indefiniment (flag `_triggered = True`)
3. Le flag est reinitialise entre les matchs via `reset()`

**Comportement en tournoi** :
- Coopere parfaitement avec les cooperants et tit_for_tat
- Un seul "faux pas" de l'adversaire declenche une punition permanente
- Forgiveness_rate = 0 (ne pardonne jamais)
- Tres performante dans les environnements ou la trahison est rare

**Difference avec TitForTat** : TitForTat pardonne apres une cooperation, GrimTrigger ne pardonne jamais. C'est la strategie "rancuniere" par excellence.

**Etat interne** : seule strategie codee (avec Pavlov) qui necessite `reset()` entre les matchs.

---

## random_strategy.py — RandomStrategy

**Logique** : choisit `"C"` ou `"D"` aleatoirement avec une probabilite 50/50 (`random.choice`).

**Comportement en tournoi** :
- Coop_rate ≈ 0.5 (converge vers 50% sur un grand nombre de tours)
- Sert de baseline non-strategique
- Resultat imprevisible, mauvais score en general
- Generalement derniere ou avant-derniere au classement

**Theorie des jeux** : equivalent d'un joueur qui ne reflechit pas. Utile comme reference pour mesurer l'efficacite des autres strategies.

---

## pavlov.py — Pavlov (Win-Stay, Lose-Shift)

**Logique** :
1. Premier tour : coopere (`"C"`)
2. Tours suivants :
   - Si le tour precedent avait le meme choix pour les deux joueurs (`my_last == opp_last`) → coopere
   - Sinon → trahit

**Interpretation** :
- Apres CC (3 pts, "victoire") → reste sur C (win-stay)
- Apres DD (1 pt, "victoire" relative car personne n'est exploite) → passe a C (win-stay)
- Apres CD (0 pts, "defaite") → passe a D (lose-shift)
- Apres DC (5 pts, "victoire") → reste sur D? Non : `D != C` → passe a C... En fait : `my_last=D, opp_last=C` → differents → trahit D

**Comportement en tournoi** :
- Forgiveness_rate eleve (~0.7) car revient souvent a la cooperation
- Capable d'exploiter always_cooperate (contrairement a tit_for_tat)
- Coopere durablement avec les strategies reciproques

**Theorie des jeux** : decouverte par Nowak & Sigmund (1993) comme alternative superieure a tit_for_tat dans certains environnements bruites.

---

## __init__.py — STRATEGY_REGISTRY

```python
STRATEGY_REGISTRY: dict[str, type] = {
    "always_cooperate": AlwaysCooperate,
    "always_defect": AlwaysDefect,
    "tit_for_tat": TitForTat,
    "grim_trigger": GrimTrigger,
    "random": RandomStrategy,
    "pavlov": Pavlov,
}
```

Ce dictionnaire permet a `generate.py` d'instancier les strategies par leur nom (lu depuis `config.yaml`). Les agents Mistral ne sont pas dans le registry car ils necessitent des parametres specifiques (nom, system_prompt).
