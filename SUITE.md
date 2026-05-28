# Ce qu'il reste a faire

## 1. Commit initial Git

Aucun commit n'a encore ete fait. C'est la premiere chose a faire.

```bash
cd prisoner-dilemma-etl
git add -A
git commit -m "feat: pipeline ETL complet — dilemme du prisonnier iteratif"
```

---

## 2. Run avec Mistral (le vrai run du projet)

Les 2 runs actuels n'utilisent que les 6 strategies codees (pas d'agent Mistral car pas de cle API).
Pour le rendu il faut au moins un run avec les 3 agents Mistral.

```bash
# 1. Obtenir une cle API Mistral sur https://console.mistral.ai/
# 2. Exporter la cle
export MISTRAL_API_KEY=<ta_cle>

# 3. Optionnel : nettoyer les anciens runs de test
make clean

# 4. Lancer le pipeline complet (~15 min avec 9 joueurs × 200 rounds)
make all
```

**Attention** : avec Mistral active, il y a 9 joueurs → 36 matchs × 200 rounds = 7200 tours.
Les 3 agents Mistral generent des appels API (avec 0.5s de sleep entre chaque),
donc ~24 matchs impliquent un agent × 200 tours × 0.5s ≈ **40 min**.
Pour aller plus vite, tu peux baisser les rounds dans `config.yaml` :

```yaml
tournament:
  rounds: 50   # rapide pour tester (~10 min)
```

---

## 3. Multi-run (bonus)

Apres le premier run Mistral, relancer un 2eme run pour montrer le multi-run :

```bash
# Modifier les rounds ou la matrice de gains dans config.yaml si tu veux varier
make generate
make load
make transform

# Verifier que les 2 runs apparaissent
duckdb data/dilemma.duckdb -c \
  "SELECT run_id, strategy, avg_score, rank_in_run FROM gold_run_comparison ORDER BY strategy, run_id"
```

---

## 4. Verification des resultats Gold

Avant le rendu, verifier que tous les modeles Gold retournent des donnees coherentes :

```bash
cd dbt_dilemma

# Classement des strategies
duckdb ../data/dilemma.duckdb -c \
  "SELECT strategy, avg_score, coop_rate, forgiveness_rate, rank_in_run
   FROM gold_strategy_metrics ORDER BY rank_in_run"

# Matrice head-to-head
duckdb ../data/dilemma.duckdb -c \
  "SELECT strategy, opponent, score_diff, result
   FROM gold_head_to_head ORDER BY strategy, opponent"

# Evolution cooperation (extrait)
duckdb ../data/dilemma.duckdb -c \
  "SELECT strategy, turn_number, rolling_coop_rate_50
   FROM gold_turn_evolution
   WHERE turn_number IN (1, 50, 100, 150, 200)
   ORDER BY strategy, turn_number
   LIMIT 30"

# Resume par match
duckdb ../data/dilemma.duckdb -c \
  "SELECT strategy_a, strategy_b, total_score_a, total_score_b, mutual_coop_rate
   FROM gold_match_summary ORDER BY strategy_a, strategy_b"
```

---

## 5. Tests dbt

```bash
cd dbt_dilemma
dbt test --profiles-dir .
```

Si tu veux ajouter des tests dbt personnalises, cree un fichier
`dbt_dilemma/models/gold/schema.yml` :

```yaml
version: 2

models:
  - name: gold_strategy_metrics
    columns:
      - name: strategy
        tests:
          - not_null
      - name: avg_score
        tests:
          - not_null
      - name: rank_in_run
        tests:
          - not_null

  - name: gold_match_summary
    columns:
      - name: match_id
        tests:
          - not_null
          - unique
```

---

## 6. Commit final + push

```bash
git add -A
git commit -m "feat: ajout run Mistral + multi-run + tests dbt"
git remote add origin <url_de_ton_repo>
git push -u origin master
```

---

## Checklist de rendu

- [ ] Au moins un run avec les agents Mistral (3 profils)
- [ ] Au moins 2 runs pour montrer le multi-run dans `gold_run_comparison`
- [ ] `make all` fonctionne de bout en bout
- [ ] `make test` passe (10 tests pytest)
- [ ] `dbt test` passe (si schema.yml ajoute)
- [ ] `dbt build` passe (7 modeles sans erreur)
- [ ] README.md, ARCHITECTURE.md, docs/delta_lake_design.md presents
- [ ] Git propre avec historique de commits
