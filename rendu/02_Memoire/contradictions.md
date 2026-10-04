# Projet NOVA : décisions et contradictions résolues

État au 30 septembre 2026, 9 h (heure de Montréal). Chemins de source relatifs à `NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/`. Les numéros EVxxx renvoient aux lignes de `evenements.csv`.

**Règle appliquée** (`nova_brain/policy.toml`) : une contradiction se tranche d'abord par l'autorité de l'auteur (comité, chargé de projet, responsable du domaine, partie prenante, fournisseur), puis par la date du fait. Un plan, un registre ou un rapport de statut ne fait que recopier un état : il ne l'emporte jamais sur la source qu'il recopie. La date d'un fichier ne compte pas, seule la date du fait compte.

## 1. Proposition, décision, validation

| Sujet | Proposition | Décision | Validation |
|---|---|---|---|
| Report de la mise en production au 22 oct. | Julien Moreau (Boréal), 8 sept. : « il s'agit d'une proposition de notre part » (E05) | Comité de direction, 10 sept., 15:22 à 15:25 (M04); reconduite avec trois conditions le 26 sept., 10:09 à 10:16 (M06) | Aucune : les trois conditions restent à remplir (SEC-210, ACC-303, runbook) |
| Correction du connecteur INT-101, cause du report | Diagnostic de Boréal, 5 sept. : jeton de service expiré (INT-101, comm. 05 sept. 11:18) | Sans objet (correctif technique) | Correctif déployé par Boréal le 17 sept. (comm. 14:23 : 120 recherches sur 120), validé et fermé par Marc Gervais (comm. 17 sept. 16:10; E12) |
| Hébergement des données | Exigence de la sécurité (Sophie Lambert), atelier du 23 juil. (M02, 09:06) | ADR-007 acceptée le 23 juil. : Canada Central | Migration vérifiée par l'équipe architecture, CR du 27 août (M03, l. 5) |
| Correctif sécurité SEC-210 | Livraison annoncée par Boréal le 19 sept. (E08) | Sans objet | Non obtenue : re-test planifié, statut maintenu EN VALIDATION (SEC-210, comm. 26 sept. 15:40) |
| Optimisation mobile (CR-04) | Boréal, brouillon CR-04 de 18 000 $ | Reportée en phase 2 le 24 sept. (Decision_Portee_Phase2; E10); « Facturer du CR-04, non » (M06, 10:25) | Aucune approbation de CR-04 |

## 2. Contradictions résolues

| # | Sujet | Ce que dit la source écartée | Ce que dit la source retenue | Raison |
|---|---|---|---|---|
| 1 | Date de mise en production (**plan**) | Plan_Projet_NOVA_v3_12sept.xlsx, cellules E7:F7 : 15 oct. 2026. Même date dans la Charte v1 (l. 7) et dans une note personnelle non signée des archives. | 22 oct. 2026 : décision du comité du 10 sept. (M04, 15:22 à 15:25), reconduite le 26 sept. (M06) et rappelée par écrit le 27 sept. (E09). | Autorité : le comité prime sur un plan qui recopie l'état. Nicolas Perron note lui-même que « le plan projet n'a visiblement pas encore été corrigé » (Teams_15sept, 09:18). La Charte précise qu'elle n'est pas mise à jour après chaque décision (l. 20). |
| 2 | Risque R-01, retard du connecteur (**registre**) | Registre_Risques_29sept.xlsx, ligne R-01 : statut « Ouvert » (F2), commentaire « Suivi au 9 septembre 2026 » (H2). | INT-101 fermé et validé le 17 sept. par Marc Gervais (INT-101; E12; CR de suivi du 18 sept., M05 l. 6). | Date du fait : le registre porte la date du 29 sept., mais son contenu n'a pas été revu depuis le 9 sept. La validation du 17 sept. est plus récente. Le courriel d'archive du 17 sept. est un doublon de E12 et ne compte pas comme une seconde preuve. |
| 3 | Sécurité acceptée? | Rapport_Statut_21sept.pdf, p. 1 : Sécurité VERT, sur la base du correctif livré. Le brouillon d'Alex (E11) parle de sécurité « complétée ». | SEC-210 EN VALIDATION (comm. 26 sept. 15:40); « déployé != accepté » (Teams_19sept_Securite, 10:31); bloquant confirmé en comité (M06, 10:02). | Autorité et date : la responsable de la sécurité refuse de clore sans re-test, et son constat est postérieur au rapport. Le rapport admet avoir été préparé avant la vérification détaillée des tickets. |
| 4 | Accessibilité complétée? | E04 (20 août, Boréal) : « Tout devrait maintenant être conforme ». Rapport de statut du 21 sept. : Accessibilité VERT. | ACC-303 ouvert depuis le 17 sept. : le bouton « Enregistrer » de la modale n'est pas atteignable au clavier (ACC-303; capture ACC-303_focus.png); bloquant confirmé le 26 sept. (M06, 10:05). | Une déclaration du fournisseur n'est pas une validation. E04 ne couvrait que les labels et le contraste (ACC-301, ACC-302). |
| 5 | Optimisation mobile dans la portée? | Julien croit le mobile avancé inclus (Teams_22sept_Mobile, 13:03). INV-003 facture 18 000 $ pour CR-04. | Charte et contrat : portée sans mobile avancé. CR-04 est un brouillon non approuvé. Report en phase 2 le 24 sept. (Decision_Portee_Phase2). | Autorité : décision du chargé de projet et du comité contre une interprétation du fournisseur. Le contrat exige une approbation écrite avant exécution et facturation (CONTRAT, p. 1). |
| 6 | Chargé de projet | Charte v1 (l. 4) et Plan v2 (D7) : Élodie Caron. | Nicolas Perron depuis le 16 sept. (E06; Note_transition, l. 4; Teams_16sept_Transition, 08:45). | Date du fait : un rôle se transmet, le fait le plus récent l'emporte. |
| 7 | Région d'hébergement | Architecture_NOVA_v1.pdf (18 juil.), p. 1 : données en East US. | ADR-007 (23 juil.) : Canada Central, migration vérifiée le 27 août (M03, l. 5). | Date du fait : la décision ADR-007 remplace l'architecture v1 sur ce point. |

## 3. Sources écartées sans contradiction

- INV-778 (archives) : facture du projet ORION, sans lien avec NOVA.
- Courriel_archive_17sept.eml : doublon de E12 (même Message-ID).
- Les pièces jointes présentes aussi comme fichiers séparés (Architecture_NOVA_v2.pdf, INV-003.pdf, Rapport_Statut_21sept.pdf, CR-04) ne comptent qu'une fois.

## 4. Point non tranché

Le Plan v3, intitulé « 12sept », nomme déjà Nicolas Perron en D7 alors qu'il n'est en poste que depuis le 16 septembre. Le fichier a probablement été modifié après la date de son titre. Il n'est retenu comme source d'autorité ni pour la date ni pour le responsable.
