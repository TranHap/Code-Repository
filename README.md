# Défi Loto-Québec — Projet 360 (NOVA)

Mémoire opérationnelle du projet NOVA. **Les résultats finaux sont dans [`rendu/`](rendu/) et se lisent sans exécuter de code.**

## Résultats finaux

| # | Livrable | Fichier |
|---|---|---|
| 1 | Brief de reprise (« si je reprenais le projet demain matin ») | [rendu/01_Brief_reprise.md](rendu/01_Brief_reprise.md) · [PDF](rendu/01_Brief_reprise.pdf) |
| 2 | Mémoire : prochaines actions | [rendu/02_Memoire/actions.md](rendu/02_Memoire/actions.md) · [PDF](rendu/02_Memoire/actions.pdf) |
| 2 | Mémoire : contradictions détectées | [rendu/02_Memoire/contradictions.md](rendu/02_Memoire/contradictions.md) · [PDF](rendu/02_Memoire/contradictions.pdf) |
| 2 | Mémoire : assertions et événements (données) | [assertions.csv](rendu/02_Memoire/assertions.csv) · [evenements.csv](rendu/02_Memoire/evenements.csv) |
| 3 | **Réponses aux questions Q01–Q10, avec sources** | [rendu/03_Reponses_Q01-Q10.md](rendu/03_Reponses_Q01-Q10.md) · [PDF](rendu/03_Reponses_Q01-Q10.pdf) |
| 5 | Mode d'emploi | [rendu/05_Mode_emploi.md](rendu/05_Mode_emploi.md) · [PDF](rendu/05_Mode_emploi.pdf) |
| 6 | Évaluation du chat (questions en langage naturel) | [rendu/06_Eval/](rendu/06_Eval/) |

> Les liens de sources (`../NOVA_ETUDIANTS/...`) renvoient au corpus fourni par les organisateurs, volontairement non republié ici : le placer à la racine du dépôt rend les liens fonctionnels.

## Code (facultatif)

- `app.py` — application Streamlit (interrogation en langage naturel, sources citées)
- `nova_brain/` — ingestion, extraction, résolution des contradictions, recherche ; `nova_brain/data/memory.db` est la base construite
- `tests/` — tests (`pytest`)

```bash
pip install -r requirements.txt
cp .env.example .env   # renseigner la clé d'API
streamlit run app.py
```
