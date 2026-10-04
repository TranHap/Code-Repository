# NOVA — Réponses aux questions initiales Q01–Q10

**Date de référence :** 30 septembre 2026, 09 h 00 (heure de Montréal, UTC−04:00)
**Racine du corpus :** `NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/` (abrégée `C/` ci-dessous)

Légende des rôles de source : **Décision** (autorité de gouvernance) · **Proposition** · **Validation** (preuve de vérification par le client) · **Déclaration** (affirmation non vérifiée, souvent fournisseur) · **Obsolète / contredit**.

> Rappel : une pièce jointe d'un courriel présente aussi comme fichier séparé n'est **pas** une confirmation indépendante (ex. `Architecture_NOVA_v2.pdf` joint à E03, `INV-003.pdf` joint à E07, `Rapport_Statut_21sept.pdf` joint à E11, `CR-04` joint à E10). `08_Archives/Courriel_archive_17sept.eml` est un **doublon** de E12 (même Message-ID).

---

## Q01. Date de mise en production actuellement approuvée, et avec quelle réserve ?

**Réponse :** **22 octobre 2026.** Ce n'est **pas un go automatique** : la date est **conditionnelle** à trois éléments précisés le 26 septembre : (1) validation sécurité de SEC-210, (2) fermeture d'ACC-303, (3) approbation du runbook incluant le rollback.

| Source | Repère | Rôle |
|---|---|---|
| [C/02_Reunions/M04_Transcript_Comite_direction_10sept.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M04_Transcript_Comite_direction_10sept.txt) | 15:22 – 15:25 (« déplacée du 15 octobre au 22 octobre 2026 » … « Donc approuvé ») ; 15:27 Nicolas : « le 22 n'est pas un go automatique » | Décision + réserve |
| [C/02_Reunions/M06_Transcript_Comite_26sept.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M06_Transcript_Comite_26sept.txt) | 10:09 (trois conditions) ; 10:16 « c'est conditionnel à ces trois éléments » | Décision (précision des conditions) |
| [C/01_Courriels/E09_Rappel_mise_en_production.eml](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/01_Courriels/E09_Rappel_mise_en_production.eml) | 27 sept, corps : « la cible approuvée demeure le 22 octobre … conditionnelle » | Confirmation écrite du chargé de projet |
| [C/04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx) | feuille « Plan projet », E7/F7 = 2026-10-15 | **Obsolète** — non mis à jour |

**Contradiction résolue :** le Plan v3 (12 sept) et la Charte v1 indiquent encore le 15 octobre. La décision du comité du 10 sept prime (autorité supérieure) ; Nicolas le confirme dans [Teams_15sept](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/07_Conversations_Teams/Teams_15sept_ProjetNOVA.txt) 09:18 (« Le plan projet n'a visiblement pas encore été corrigé »). La Charte précise elle-même qu'elle n'est pas mise à jour automatiquement (ligne 20).

---

## Q02. Pourquoi la date a-t-elle changé, et quel est l'état actuel de la cause initiale ?

**Réponse :** Le report est dû à l'**instabilité du connecteur interne (INT-101)** : en INT, les recherches par numéro retournaient vide (erreurs 401, jeton de service expiré après changement de secret, puis erreurs intermittentes). Boréal a demandé une semaine pour stabiliser le connecteur, reprendre les tests intégrés et garder une marge pour les anomalies bloquantes. Sécurité et accessibilité ont aussi refusé de compresser leurs tests.

**État actuel de la cause :** **résolue.** INT-101 a été corrigé (rotation du secret + logique de renouvellement du jeton), validé par Marc Gervais (120/120 recherches) et **fermé le 17 septembre**. La date reste néanmoins le 22 octobre : aucune décision ne la ramène au 15.

| Source | Repère | Rôle |
|---|---|---|
| [C/01_Courriels/E05_Retard_integration.eml](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/01_Courriels/E05_Retard_integration.eml) | 8 sept, corps | Proposition (cause) |
| [C/02_Reunions/M04_…10sept.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M04_Transcript_Comite_direction_10sept.txt) | 15:02 – 15:10 | Justification en comité |
| [C/03_Tickets/INT-101.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/03_Tickets/INT-101.txt) | commentaires 05 sept 11:18, 08 sept 16:02, 17 sept 14:23 et 16:10 ; ligne « Résolution » | Validation (fermeture) |
| [C/03_Tickets/INT-101_extrait_logs.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/03_Tickets/INT-101_extrait_logs.txt) | lignes 1–3 (401 le 05/09 → 200 OK le 17/09) | Preuve technique |
| [C/01_Courriels/E12_Resolution_integration.eml](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/01_Courriels/E12_Resolution_integration.eml) | 17 sept 16:22 | Validation (confirmation écrite) |
| [C/02_Reunions/M05_CR_Suivi_18sept.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M05_CR_Suivi_18sept.txt) | ligne 6 | Confirmation en suivi |
| [C/04_Documents_projet/Registre_Risques_29sept.xlsx](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/04_Documents_projet/Registre_Risques_29sept.xlsx) | ligne R-01 : F2 « Ouvert », H2 « Suivi au 9 septembre 2026 » | **Obsolète** |

**Contradiction résolue (registre de risques) :** le registre daté du 29 sept garde R-01 « Retard du connecteur » **Ouvert**, mais son commentaire (H2) montre qu'il n'a pas été revu depuis le 9 sept. Le ticket fermé et validé le 17 sept fait autorité → R-01 devrait être fermé. *Le doublon `08_Archives/Courriel_archive_17sept.eml` ne compte pas comme une seconde preuve.*

---

## Q03. Qui a approuvé le changement et quand ? Proposition vs approbation

| Étape | Qui | Quand | Source / repère |
|---|---|---|---|
| **Proposition** | Julien Moreau (Boréal, fournisseur) | 8 sept 2026, 11:16 | [E05](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/01_Courriels/E05_Retard_integration.eml) : « il s'agit d'une proposition de notre part. À vous de confirmer la décision de gouvernance » |
| Recommandation réitérée | Julien Moreau | 10 sept, 15:02 | [M04](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M04_Transcript_Comite_direction_10sept.txt) 15:02 |
| **Approbation** | **Comité de direction NOVA**, décision formulée par **Élodie Caron** (chargée de projet à cette date), sans opposition (Sophie Lambert, Marc Gervais, Olivier Côté, Nicolas Perron « D'accord ») | **10 sept 2026, 15:22 – 15:25** | [M04](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M04_Transcript_Comite_direction_10sept.txt) 15:22 – 15:25 |
| Reconduction avec conditions | Comité, présidé par Nicolas Perron | 26 sept, 10:09 – 10:16 | [M06](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M06_Transcript_Comite_26sept.txt) |

Recoupements : [Teams_15sept](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/07_Conversations_Teams/Teams_15sept_ProjetNOVA.txt) 09:18 et [Note_transition_Elodie_16sept](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/04_Documents_projet/Note_transition_Elodie_16sept.txt) ligne 7 (« le comité a approuvé le 22 octobre »).
Pas d'impact contractuel identifié : le contrat court jusqu'au 31 octobre (M04 15:18 ; CONTRAT p.1, « Période »).

---

## Q04. Qui est responsable du projet et depuis quand ?

**Réponse :** **Nicolas Perron**, chargé de projet **depuis le 16 septembre 2026**. Avant : Élodie Caron (du 7 juillet au 15 septembre 2026), qui reste disponible quelques jours pour la transition.

| Source | Repère | Rôle |
|---|---|---|
| [C/01_Courriels/E06_Transition_charge_projet.eml](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/01_Courriels/E06_Transition_charge_projet.eml) | 16 sept 08:35, corps | Annonce officielle |
| [C/04_Documents_projet/Note_transition_Elodie_16sept.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/04_Documents_projet/Note_transition_Elodie_16sept.txt) | ligne 4 | Note de transition |
| [C/07_Conversations_Teams/Teams_16sept_Transition.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/07_Conversations_Teams/Teams_16sept_Transition.txt) | 08:45 et 08:47 | Recoupement |
| [C/02_Reunions/M01_CR_Demarrage_07juillet.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M01_CR_Demarrage_07juillet.txt) | ligne 9 | Historique (Élodie) |

**Obsolète :** Charte v1 (ligne 4) et Plan v2 (D7 « Élodie Caron »).
**Incertitude :** le Plan v3, intitulé « 12sept », indique déjà « Nicolas Perron » en D7 (responsable de la mise en production), soit avant la transition du 16 sept. Il s'agit probablement d'une modification ultérieure du fichier sans mise à jour de la date. Le fichier n'est pas une source d'autorité sur ce point.

---

## Q05. Montant contractuel autorisé et calcul

**Réponse :** **204 000 $ CAD** (hors taxes) = **180 000 $** (montant maximal initial du contrat) **+ 24 000 $** (CR-01 « Rapports avancés », **approuvée** le 14 août 2026 par le comité de projet).
**CR-04 (18 000 $) n'est pas inclus** : c'est un brouillon non approuvé.

| Élément | Montant | Statut | Source / repère |
|---|---|---|---|
| Contrat initial | 180 000 $ | Autorisé | [CONTRAT_Boreal_NOVA.pdf](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/05_Contrats_et_finances/CONTRAT_Boreal_NOVA.pdf) p.1, tableau « Valeur contractuelle » |
| CR-01 | +24 000 $ | **Approuvée** 14 août 2026 | [CR-01_…_APPROUVE.pdf](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/05_Contrats_et_finances/CR-01_Rapports_avances_APPROUVE.pdf) p.1 « Décision / Date / Autorité » |
| CR-04 | (18 000 $) | **Brouillon, non approuvé** | [CR-04_…_BROUILLON.pdf](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/05_Contrats_et_finances/CR-04_Optimisation_mobile_BROUILLON.pdf) p.1 « Statut » + Note |
| **Total autorisé** | **204 000 $** | | |

**Autorisé vs facturé vs payé :**

| Facture | Date | Montant | Statut | Repère |
|---|---|---|---|---|
| INV-001 | 2026-07-31 | 60 000 $ (acompte phase 1) | **Payée** | [INV-001.pdf](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/05_Contrats_et_finances/INV-001.pdf) p.1 |
| INV-002 | 2026-08-31 | 72 000 $ (48 000 jalon 2 + 24 000 CR-01) | **Payée** | [INV-002.pdf](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/05_Contrats_et_finances/INV-002.pdf) p.1 |
| INV-003 | 2026-09-22 | 54 000 $ (36 000 jalon 3 + 18 000 CR-04) | **En validation** | [INV-003.pdf](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/05_Contrats_et_finances/INV-003.pdf) p.1 |
| ~~INV-778~~ | — | 41 000 $ | **Autre projet (ORION), à exclure** | [08_Archives/INV-778_Projet_ORION.pdf](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/08_Archives_et_documents_connexes/INV-778_Projet_ORION.pdf), Note |

- **Payé :** 132 000 $
- **Facturé :** 186 000 $ (en comptant INV-003 tel quel)
- **Facturable légitime si la ligne CR-04 est retirée :** 168 000 $, soit un solde autorisé restant de 36 000 $

---

## Q06. Quel problème présente INV-003 ? Montant et traitement

**Problème :** INV-003 (22 sept, 54 000 $) contient une ligne de **18 000 $ « Optimisation interface mobile – CR-04 »**. Or CR-04 est un **brouillon non approuvé** (aucune signature ni numéro d'approbation), et le contrat exige qu'un travail hors portée fasse l'objet d'une demande **écrite et approuvée avant exécution et facturation**. La portée phase 1 exclut explicitement l'optimisation mobile avancée, reportée en phase 2 le 24 sept.

**Montant concerné :** **18 000 $**. La ligne « jalon 3 » de 36 000 $ n'est pas contestée dans le corpus.

**Traitement à prévoir :**
1. Ne pas libérer INV-003 tel quel.
2. Demander à Boréal une **facture corrigée ou une note de crédit** retirant les 18 000 $.
3. Traiter le jalon 3 (36 000 $) selon le processus normal. *Acceptation du jalon 3 : à confirmer, aucune preuve d'acceptation dans le corpus.*
4. Toute dépense mobile future exige une **nouvelle approbation** de CR-04 (phase 2).

| Source | Repère | Rôle |
|---|---|---|
| [C/05_Contrats_et_finances/INV-003.pdf](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/05_Contrats_et_finances/INV-003.pdf) | p.1, ligne « Optimisation interface mobile – CR-04 » 18 000 $ ; Note | Facture |
| [C/01_Courriels/E07_Facture_003_question.eml](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/01_Courriels/E07_Facture_003_question.eml) | 23 sept 10:18, Amélie Fortin (Finances) | Question de validation |
| [C/05_…/CR-04_Optimisation_mobile_BROUILLON.pdf](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/05_Contrats_et_finances/CR-04_Optimisation_mobile_BROUILLON.pdf) | p.1 « Statut : BROUILLON – APPROBATION REQUISE » ; Note | Preuve de non-approbation |
| [C/05_…/CONTRAT_Boreal_NOVA.pdf](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/05_Contrats_et_finances/CONTRAT_Boreal_NOVA.pdf) | p.1 « Gestion des changements » | Règle contractuelle |
| [C/06_…/Decision_Portee_Phase2.md](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/06_Architecture_et_decisions/Decision_Portee_Phase2.md) | 24 sept, « Décision » + § 2 | Décision de portée |
| [C/01_Courriels/E10_Fonction_mobile.eml](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/01_Courriels/E10_Fonction_mobile.eml) | 24 sept 13:42, Nicolas → Julien + Amélie | Décision communiquée (réponse de fait à E07) |
| [C/02_Reunions/M06_…26sept.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M06_Transcript_Comite_26sept.txt) | 10:24 – 10:25 « Facturer du CR-04, non. Il n'est pas approuvé. » | Confirmation en comité |
| [C/02_Reunions/M04_…10sept.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M04_Transcript_Comite_direction_10sept.txt) | 15:33 – 15:40 « aucune approbation aujourd'hui » | Historique |

**Contradiction :** [Teams_22sept_Mobile](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/07_Conversations_Teams/Teams_22sept_Mobile.txt) 13:03, Julien croyait le mobile avancé inclus dans le périmètre. Démenti par Nicolas (13:06), par la Charte/le Contrat (portée incluse, sans mobile avancé) et par M01 ligne 20. Risque : Boréal a « déjà commencé à regarder quelques ajustements » (M06 10:24).

---

## Q07. Où les données de production doivent-elles être hébergées ? Preuve de mise en œuvre

**Réponse :** au **Canada, région Canada Central**. Décision ADR-007, **acceptée le 23 juillet 2026**, à la demande de la sécurité (Sophie Lambert). L'architecture v1 (East US) est remplacée sur ce point.

**Preuve de mise en œuvre :**
- **Déclaration fournisseur :** E03 (26 août), Julien annonce la migration complétée, avec test de déploiement et de connectivité ; schéma v2 joint (Canada Central).
- **Vérification client :** CR du comité du 27 août, « déclarée terminée par Boréal **et vérifiée par l'équipe architecture** ». C'est la preuve qui fait autorité.
- *Le PDF `Architecture_NOVA_v2.pdf` est la pièce jointe de E03 : ce n'est pas une confirmation indépendante.*

| Source | Repère | Rôle |
|---|---|---|
| [C/06_…/ADR-007_Localisation_donnees.md](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/06_Architecture_et_decisions/ADR-007_Localisation_donnees.md) | lignes 3–4 (date, statut) ; § Décision ligne 10 | Décision |
| [C/02_Reunions/M02_Transcript_Architecture_23juillet.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M02_Transcript_Architecture_23juillet.txt) | 09:06 – 09:17 | Décision en atelier |
| [C/01_Courriels/E03_Confirmation_Canada_Central.eml](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/01_Courriels/E03_Confirmation_Canada_Central.eml) | 26 août 09:05 + PJ v2 | Déclaration |
| [C/02_Reunions/M03_CR_Comite_27aout.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M03_CR_Comite_27aout.txt) | ligne 5 | **Validation** |
| [C/06_…/Architecture_NOVA_v1.pdf](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/06_Architecture_et_decisions/Architecture_NOVA_v1.pdf) | p.1 « Données East US » (18 juillet) | **Obsolète** |

**Limite :** le corpus ne contient pas de preuve technique brute (export de configuration cloud, rapport de validation signé). La vérification repose sur la mention au CR du 27 août.

---

## Q08. La sécurité est-elle acceptée ? Livraison vs validation

**Réponse : Non.** Le correctif de **SEC-210** (journal d'audit incomplet lors d'un export CSV admin : l'objet, c.-à-d. l'ID du dossier, et le résultat sont absents) a été **livré / déployé** en validation le **19 septembre** par Boréal. L'**acceptation sécurité n'est pas donnée** : le ticket est **EN VALIDATION**, et le re-test de Sophie Lambert a été **planifié** le 26 sept, sans résultat connu au 30 sept. SEC-210 est classé « Bloquante avant production » et constitue l'une des trois conditions de go-live.

| Étape | Date | Source / repère |
|---|---|---|
| Défaut constaté | 12 sept | [SEC-210.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/03_Tickets/SEC-210.txt) « Observé » ; capture [SEC-210_audit.png](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/03_Tickets/SEC-210_audit.png), ligne 14:04:08 EXPORT_CSV, Objet « --- », Résultat « --- » |
| **Livraison** (fournisseur) | 19 sept 10:20–10:24 | [E08](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/01_Courriels/E08_Correctif_journalisation.eml) ; SEC-210 comm. 19 sept 10:22 ; [Teams_19sept_Securite](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/07_Conversations_Teams/Teams_19sept_Securite.txt) 10:24 |
| Refus de clore sans re-test | 19 sept | SEC-210 comm. 19 sept 14:05 ; Teams 19 sept 10:31 « "déployé" != "accepté" » |
| **Validation : non obtenue** | 26 sept | SEC-210 comm. 26 sept 15:40 « Re-test planifié. Statut maintenu EN VALIDATION » ; [M06](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M06_Transcript_Comite_26sept.txt) 10:02 |

**Contradiction résolue :** le [Rapport_Statut_21sept.pdf](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/04_Documents_projet/Rapport_Statut_21sept.pdf) (p.1, ligne Sécurité) affiche **VERT** sur la base du seul « correctif livré ». Le rapport reconnaît lui-même avoir été « préparé avant la dernière vérification détaillée de certains tickets ». Le ticket et le comité du 26 sept, plus récents et émanant de l'autorité sécurité, priment. Le brouillon d'Alex « sécurité … complétée » ([E11](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/01_Courriels/E11_Communication_statut.eml)) est donc **inexact** et ne doit pas être publié. Le registre de risques confirme : R-02 « Validation sécurité incomplète » est Ouvert.

---

## Q09. L'accessibilité est-elle complétée ? Ce qui reste à corriger

**Réponse : Non.**
- **Corrigés et validés :** ACC-301 (labels, validé NVDA/VoiceOver le 15 août) et ACC-302 (contraste 2,1:1 → 5,3:1, validé le 20 août).
- **Reste ouvert : ACC-303** (priorité haute, **bloquant d'accessibilité avant production** selon Mélissa Gagnon). Dans la modale « Modifier le dossier », le piège de focus ne parcourt qu'une liste incomplète d'éléments : Tab circule entre « Nom » et « Commentaire », et **le bouton « Enregistrer » n'est jamais atteint au clavier**. Reproduit sur Chrome et Edge, build 2026.09.17. Un correctif est **annoncé** pour la prochaine build, mais **non livré ni validé** au 26 sept.

| Source | Repère | Rôle |
|---|---|---|
| [C/03_Tickets/ACC-303.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/03_Tickets/ACC-303.txt) | Statut OUVERT ; comm. 17 sept 13:14, 18 sept 09:50, 26 sept 11:03 | Statut courant |
| [C/03_Tickets/ACC-303_focus.png](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/03_Tickets/ACC-303_focus.png) | capture build 2026.09.17, bouton Enregistrer encadré, « Le focus clavier ne rejoint pas ce bouton » | Preuve visuelle |
| [C/02_Reunions/M06_…26sept.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M06_Transcript_Comite_26sept.txt) | 10:05 | Bloquant confirmé en comité |
| [C/03_Tickets/ACC-301.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/03_Tickets/ACC-301.txt), [ACC-302.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/03_Tickets/ACC-302.txt) | comm. 15 août / 20 août « Fermé » | Validés |
| [C/02_Reunions/M05_CR_Suivi_18sept.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M05_CR_Suivi_18sept.txt) | ligne 10 | Recoupement |

**Contradictions :** [E04](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/01_Courriels/E04_Corrections_accessibilite.eml) (20 août, Boréal : « Tout devrait maintenant être conforme ») est une **déclaration fournisseur** qui ne couvre que labels et contraste ; Mélissa demandait déjà de repasser les modales au clavier (citation du 12 août, même courriel, et M03 ligne 11). Le Rapport de statut du 21 sept (ligne Accessibilité **VERT**, « Correctifs appliqués ») est **contredit** par ACC-303, ouvert depuis le 17 sept.

---

## Q10. Trois conditions de go-live et travaux manquants du runbook

**Les trois conditions** (comité du 26 sept, Nicolas Perron ; confirmées par Sophie, Mélissa et Olivier) :
1. **Validation sécurité de SEC-210** (acceptation par Sophie Lambert après re-test).
2. **Fermeture d'ACC-303** (correctif dans la prochaine build, puis validation par Mélissa Gagnon).
3. **Approbation du runbook incluant le rollback** (go exploitation d'Olivier Côté).

**Runbook, d'après la capture [OPS-601_runbook.png](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/03_Tickets/OPS-601_runbook.png) (version du 25 septembre) :**

| Étape | État |
|---|---|
| 1. Vérifier la santé des services | OK |
| 2. Activer le mode maintenance | OK |
| 3. Déployer la version approuvée | OK |
| **4. Procédure de retour arrière** | **TODO** |
| **5. Validation fonctionnelle post-déploiement** | **À compléter** |

→ Travaux manquants : **étape 4 (rollback)** et **étape 5 (validation fonctionnelle post-déploiement)**. Olivier exige une procédure « qu'une autre personne peut exécuter sans appeler l'équipe projet ». Au **29 sept**, la version finale n'est toujours pas reçue.

| Source | Repère | Rôle |
|---|---|---|
| [C/02_Reunions/M06_Transcript_Comite_26sept.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M06_Transcript_Comite_26sept.txt) | 10:09 – 10:16 | Décision (conditions) |
| [C/01_Courriels/E09_Rappel_mise_en_production.eml](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/01_Courriels/E09_Rappel_mise_en_production.eml) | 27 sept | Recoupement écrit |
| [C/03_Tickets/OPS-601.txt](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/03_Tickets/OPS-601.txt) | comm. 25 sept, 26 sept, 29 sept | Statut OUVERT |
| [C/03_Tickets/OPS-601_runbook.png](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/03_Tickets/OPS-601_runbook.png) | lignes 4 et 5 de la capture | Preuve visuelle |
| [C/04_Documents_projet/Registre_Risques_29sept.xlsx](../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/04_Documents_projet/Registre_Risques_29sept.xlsx) | R-02, R-03, R-04 (G3:G5) | Mitigations alignées |

**Échéances :** aucune date de fermeture n'est documentée pour les trois conditions → **à confirmer**. Contrainte connue : Olivier veut le runbook final « au moins quelques jours avant » le go-live (M04 15:12).

---

## Annexe — Sources écartées ou à faible autorité

| Fichier | Raison |
|---|---|
| `08_Archives/INV-778_Projet_ORION.pdf` | Autre projet (ORION) |
| `08_Archives/Courriel_archive_17sept.eml` | Doublon de E12 (même Message-ID) |
| `08_Archives/Notes_personnelles_quelquun.txt` | Auteur inconnu, non officiel (« 15 oct probablement » : faux) |
| `08_Archives/Plan_NOVA_preliminaire_juin.xlsx` | Plan préliminaire antérieur au démarrage |
| `08_Archives/Newsletter_…`, `Invitation_Formation_Excel.txt` | Hors sujet |
| `01_Courriels/E11_Communication_statut.eml` | Brouillon de communication erroné, à corriger avant diffusion |
