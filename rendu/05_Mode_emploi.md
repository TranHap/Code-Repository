# Projet NOVA : mode d'emploi

Ce dossier constitue la mémoire opérationnelle du projet NOVA au 30 septembre 2026, 9 h (heure de Montréal), puis après l'intégration de la nouvelle information. Tout le contenu est lisible sans installer quoi que ce soit. L'application est un complément pour chercher et naviguer plus vite.

## 1. Ouverture

**Sans installation.** Ouvrir les fichiers du dossier `rendu/` :

| Fichier | Contenu |
|---|---|
| `01_Brief_reprise.pdf` | Brief d'une page : responsable, date et conditions, portée, budget, factures, priorités |
| `02_Memoire/actions.pdf` (et `.md`) | Actions restantes A01 à A17 : responsable, preuve, échéance, nature (engagement ou recommandation) |
| `02_Memoire/contradictions.pdf` (et `.md`) | Proposition, décision et validation des sujets clés; sept contradictions résolues, avec la raison du choix |
| `02_Memoire/evenements.csv` | Chronologie : un événement par ligne (EV001, EV002…), avec date, acteur, statut et repère |
| `02_Memoire/assertions.csv` | Faits extraits du dossier, avec leur source et leur repère |
| `03_Reponses_Q01-Q10.pdf` (et `.md`) | Réponses aux dix questions, avec fichier source, repère et contradictions résolues |
| `04_Mise_a_jour/` | Après la nouvelle information : rapport des changements par rapport à la baseline, preuves et actions touchées |
| `06_Eval/` | Résultats des tests du chat sur les dix questions |

Les chemins de source sont relatifs à `NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/`.

**Avec l'application** (Python 3.11 ou plus récent), depuis la racine du projet :

```
pip install -r requirements.txt
python -m streamlit run app.py
```

L'application s'ouvre à l'adresse http://localhost:8501. Elle lit la base `nova_brain/data/memory.db`, déjà construite; aucune ingestion n'est nécessaire. Le chat et l'import de nouvelles informations demandent une clé d'API dans un fichier `.env`, à créer en copiant `.env.example` (variables `ZAI_API_KEY`, `ZAI_BASE_URL`, `TEXT_MODEL`, `VISION_MODEL`; tout service compatible avec l'API OpenAI convient, par exemple Google Gemini avec une clé gratuite). Sans clé, les onglets État du projet, Preuves, Chronologie et Baseline vs actuel fonctionnent normalement.

## 2. Navigation dans l'application

| Onglet | Usage |
|---|---|
| Chat | Poser une question en langage naturel. Chaque réponse liste ses sources; le bouton « voir » affiche le passage exact. Une information nouvelle donnée au chat n'est enregistrée qu'après un clic sur « Enregistrer ». |
| État du projet | Indicateurs clés, trois conditions de go-live, contradictions détectées et faits en vigueur. Le détail d'un fait montre qui l'a proposé, décidé et validé. |
| Preuves | Recherche plein texte dans les courriels, comptes rendus, tickets, conversations Teams, PDF, tableurs et captures. L'inventaire signale les doublons et les documents hors projet. |
| Chronologie | Tous les événements datés, filtrables par statut (proposition, décision, validation) et par sujet. La case « Écartés seulement » montre les informations remplacées ou périmées. |
| Nouvelle information | Importer un dossier ou une archive .zip, relire les propositions extraites, puis les charger. |
| Baseline vs actuel | Rapport des changements depuis l'état initial, téléchargeable en Markdown. |

**Exemple : retrouver une preuve en trois étapes.** Pour vérifier ce qui manque au runbook (Q10) : ouvrir l'onglet Preuves, chercher « rollback runbook », puis ouvrir le résultat `OPS-601_runbook.png` (parmi les premiers, avec le ticket OPS-601 et le compte rendu M06). La transcription montre l'étape 4 (procédure de retour arrière) à l'état TODO. Sans l'application, le même fichier se trouve dans `03_Tickets/`.

## 3. Outils utilisés

- Python, Streamlit (interface), SQLite (base de la mémoire), PyMuPDF et openpyxl (lecture des PDF et des tableurs).
- Modèles de langage via une API compatible OpenAI : modèles GLM de Z.ai lors de l'ingestion initiale (extraction et transcription des captures), Google Gemini 2.5 Flash pour le chat et les imports actuels.
- Assistants d'IA utilisés pendant le développement pour écrire du code et mettre en forme les documents.

Le modèle de langage ne décide de rien. Il propose des faits et rédige des réponses à partir des sources. Les règles qui départagent deux informations contradictoires sont écrites dans `nova_brain/policy.toml` : l'autorité de l'auteur passe d'abord (comité, chargé de projet, responsable du domaine, partie prenante, fournisseur), puis la date du fait. Seul le responsable du domaine ou le comité peut fermer un sujet.

## 4. Traitements manuels

- La chronologie (`evenements.csv`) et les faits de référence (`assertions.csv`) ont été construits et relus par l'équipe à partir de la lecture du dossier.
- Les réponses Q01 à Q10 ont été rédigées par l'équipe et vérifiées contre les sources citées. Ce sont elles qui font foi, pas le chat.
- Lors d'un import, chaque proposition extraite est relue avant d'être chargée (case « garder ? », cellules modifiables).
- Un import erroné peut être annulé (onglet Nouvelle information, « Annuler un lot ») : rien n'est effacé, le lot est seulement neutralisé.
- La baseline correspond aux lots 1 à 7. Elle n'est jamais modifiée et peut être recalculée à tout moment. En ligne de commande : `python -m nova_brain.nouvelle_info <dossier> --partial` pour importer, puis `python -m nova_brain.rapport_maj` pour produire le rapport des changements.

## 5. Limites et informations incertaines

**Absent du dossier, donc marqué « à confirmer » :** date du re-test SEC-210, date de la prochaine build, date de livraison du runbook final, date du comité go/no-go, acceptation du jalon 3 de INV-003, réponse de Boréal sur INV-003.

**Points incertains :**

- Hébergement au Canada Central : la seule preuve de vérification est la mention au compte rendu du 27 août (M03). Le dossier ne contient ni export de configuration ni rapport signé.
- Le Plan v3, intitulé « 12sept », nomme déjà Nicolas Perron, qui n'est en poste que depuis le 16 septembre. Le fichier a probablement été modifié après sa date; il n'est pas retenu comme source d'autorité.
- Une date de fichier récente ne garantit pas une information exacte : le registre des risques du 29 septembre n'a pas été revu depuis le 9 septembre.

**Limites de l'outil :**

- Le chat peut se tromper ou omettre une nuance. Il faut ouvrir la source citée avant de s'y fier.
- Les transcriptions des captures d'écran sont produites par un modèle de vision et conservées en cache. En cas de doute, consulter l'image d'origine.
- Les propositions extraites automatiquement peuvent être mal classées (par exemple une déclaration du fournisseur prise pour un constat). C'est la raison de la relecture obligatoire.
- La version gratuite de l'API limite le nombre de requêtes par minute; en cas d'erreur, attendre quelques secondes et relancer.
- Une pièce jointe présente aussi comme fichier séparé n'est comptée qu'une fois.
