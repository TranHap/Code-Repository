# Projet NOVA : brief de reprise

État au 30 septembre 2026, 9 h (heure de Montréal). Version initiale, avant la nouvelle information.

La mise en production est approuvée pour le 22 octobre 2026, sous conditions. Au 30 septembre, aucune des trois conditions n'est remplie.

## 1. Responsable

Nicolas Perron est chargé de projet depuis le 16 septembre 2026 (E06, Note_transition l. 4). Il a succédé à Élodie Caron, en poste du 7 juillet au 15 septembre. Le fournisseur est Boréal Numérique (contact : Julien Moreau).

## 2. Date approuvée et conditions

La date initiale du 15 octobre a été reportée au 22 octobre. Boréal a proposé ce report le 8 septembre (E05) et le comité de direction l'a approuvé le 10 septembre (M04, 15:22 à 15:25). Nicolas Perron a précisé que le 22 n'est « pas un go automatique » (M04, 15:27). Le comité du 26 septembre a fixé trois conditions (M06, 10:09 à 10:16; rappel écrit dans E09). La cause du report, le ticket INT-101, est fermée depuis le 17 septembre.

| Condition | Situation au 30 sept. | Action | Responsable | Échéance |
|---|---|---|---|---|
| C1. Validation sécurité de SEC-210 | Correctif livré le 19 sept., pas encore validé : ticket en validation (comm. du 26 sept.) | A01. Re-test et acceptation | Sophie Lambert (confirmé) | À confirmer, avant le 22 oct. |
| C2. Fermeture d'ACC-303 | Ouvert : au clavier, le focus n'atteint pas le bouton « Enregistrer » (ACC-303_focus.png) | A02. Correctif dans la prochaine build; A03. Re-test clavier | A02 : Boréal (confirmé); A03 : Mélissa Gagnon (proposé) | À confirmer (« prochaine build », M06 10:12) |
| C3. Runbook avec rollback approuvé | OPS-601 ouvert. Étape 4 (retour arrière) à faire, étape 5 (validation après déploiement) à compléter (OPS-601_runbook.png). Version finale non reçue au 29 sept. | A04. Compléter le runbook; A05. Donner le go exploitation | A04 : équipe ops de Boréal (confirmé); A05 : Olivier Côté (confirmé) | À confirmer; « quelques jours avant » la mise en production (M04 15:12) |
| Ensemble | | A06. Tenir un go/no-go formel sur preuves (recommandation de l'équipe) | Nicolas Perron (proposé) | À confirmer |

## 3. Portée de la phase 1

La charte prévoit le SSO, la création et le suivi de demandes, les pièces jointes, le workflow, le tableau de suivi et les rapports standards (Charte, l. 12 à 18). Les rapports avancés s'y ajoutent par CR-01, approuvée le 14 août. L'optimisation mobile avancée (CR-04) est hors portée : elle a été reportée en phase 2 le 24 septembre (Decision_Portee_Phase2), la phase 1 devant seulement rester utilisable sur mobile. Les données de production sont hébergées au Canada Central (ADR-007; vérification notée au CR du 27 août, M03 l. 5).

## 4. Budget et factures

Montants en dollars canadiens, hors taxes. Le montant autorisé est de 204 000 $, soit 180 000 $ prévus au contrat (CONTRAT, p. 1) plus 24 000 $ pour CR-01. CR-04 (18 000 $) n'est qu'un brouillon et n'est pas approuvé; il ne fait donc pas partie de l'autorisé.

| Facture | Montant | Statut |
|---|---|---|
| INV-001 | 60 000 $ | Payée |
| INV-002 | 72 000 $, dont 24 000 $ pour CR-01 | Payée |
| INV-003 | 54 000 $ : 36 000 $ pour le jalon 3 et 18 000 $ pour CR-04, non approuvé | En validation; ne pas payer en l'état |

Au total, 132 000 $ ont été payés et 186 000 $ facturés. Sans la ligne CR-04, le facturé serait de 168 000 $ et il resterait 36 000 $ sur l'autorisé. La facture INV-778 concerne le projet ORION et n'est pas comptée.

## 5. Priorités

1. Lever les trois conditions de mise en production (A01 à A06).
2. INV-003 : refuser la ligne de 18 000 $, demander une note de crédit et confirmer l'acceptation du jalon 3 avant tout paiement (A07 à A09).
3. Ne pas diffuser le brouillon de communication qui présente le projet « au vert » (E11) et corriger le rapport de statut du 21 septembre, qui indique à tort que la sécurité et l'accessibilité sont au vert (A14, A15).
4. Mettre à jour le plan projet avec la date du 22 octobre et fermer le risque R-01 au registre (A12, A13).
5. Prévoir une option d'avenant : le contrat se termine le 31 octobre, soit neuf jours seulement après la mise en production (A16).

---

<small>Responsable « confirmé » : nommé dans une source. « Proposé » : déduit par l'équipe de reprise. Une recommandation de l'équipe n'est pas un engagement documenté. Informations absentes du dossier : dates du re-test SEC-210, de la prochaine build, du runbook final et du comité go/no-go; acceptation du jalon 3. Les repères détaillés figurent dans 03_Reponses_Q01-Q10.md et 02_Memoire/actions.md.</small>
