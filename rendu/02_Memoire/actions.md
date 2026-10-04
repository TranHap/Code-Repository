# NOVA — Actions restantes

**État au :** 30 septembre 2026, 09 h 00 (baseline, avant la nouvelle information)
**Chemins de source :** relatifs à `NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/` · **EVxxx** = ligne de [evenements.csv](evenements.csv)

### Légende

| Colonne | Valeurs |
|---|---|
| **Nature** | **ENG** = engagement déjà documenté dans le corpus · **REC** = recommandation de notre équipe (aucun engagement trouvé) |
| **Responsable** | **confirmé** = nommé dans une source · **proposé** = déduit par notre équipe du rôle de la personne |
| **Échéance** | date documentée, sinon **à confirmer** (aucune n'est inventée) |
| **État** | Ouvert · En cours · En retard · Complété |

---

## 1. Conditions de go-live du 22 octobre (priorité 1)

Source de la décision : [M06](../../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/02_Reunions/M06_Transcript_Comite_26sept.txt) 10:09–10:16 (EV055), confirmée par [E09](../../NOVA_ETUDIANTS/Projet360_NOVA_ETUDIANTS/01_Courriels/E09_Rappel_mise_en_production.eml) (EV059).

| ID | Condition | Action | Responsable | Nature | Preuve | Échéance | État |
|---|---|---|---|---|---|---|---|
| **A01** | C1 Sécurité | Exécuter le re-test du scénario SEC-210 (export CSV : objet + résultat journalisés) et prononcer l'acceptation ou le refus | **Sophie Lambert** (confirmé) | ENG | `03_Tickets/SEC-210.txt` comm. 26 sept 15:40 « Re-test planifié » (EV058) ; M06 10:02 | Date du re-test **à confirmer** ; doit précéder le 22 oct. | En cours |
| **A02** | C2 Accessibilité | Livrer le correctif ACC-303 (piège de focus de la modale, bouton « Enregistrer ») dans la prochaine build | **Boréal / Julien Moreau** (confirmé) | ENG | M06 10:12 « On vise le correctif ACC-303 dans la prochaine build » (EV054) ; ACC-303 comm. 26 sept 11:03 | « Prochaine build » : **date à confirmer** | Ouvert |
| **A03** | C2 Accessibilité | Re-tester ACC-303 au clavier (Chrome, Edge) et fermer le ticket | **Mélissa Gagnon** (proposé : auteure du ticket et responsable R-04) | REC | `03_Tickets/ACC-303.txt` ; Registre R-04 « Fermer ACC-303 » (EV062) | **À confirmer**, après A02 | Bloqué par A02 |
| **A04** | C3 Exploitation | Compléter le runbook : **étape 4 Procédure de retour arrière (TODO)** et **étape 5 Validation fonctionnelle post-déploiement (À compléter)**, exécutable par une personne hors de l'équipe projet | **Boréal, équipe ops** (confirmé : Julien « je relance notre équipe ops ») | ENG | `03_Tickets/OPS-601_runbook.png` lignes 4–5 (EV053) ; OPS-601 comm. 25 sept ; M06 10:15 | **À confirmer**. Contrainte : « au moins quelques jours avant » la MEP (M04 15:12, EV033) | **En retard** : non reçu au 29 sept (EV060) |
| **A05** | C3 Exploitation | Approuver le runbook final et donner le go exploitation | **Olivier Côté** (confirmé) | ENG | M06 10:07 « Je ne donnerai pas mon go exploitation tant que… » ; OPS-601 | **À confirmer**, après A04 | Bloqué par A04 |
| **A06** | Toutes | Tenir un point go/no-go formel qui vérifie C1, C2 et C3 avec preuves (ticket fermé, runbook approuvé) avant le 22 oct. | **Nicolas Perron** (proposé : chargé de projet, préside le comité) | REC | M04 15:27 « pas un go automatique » (EV036) ; M06 10:16 (EV055) | **À confirmer**. Recommandé : au plus tard quelques jours avant le 22 oct. | Ouvert |

> **Ce qui n'est PAS une condition remplie :** « fix SEC-210 livré » (E08, EV045), « build stable » (M06 10:01), « tout devrait être conforme » (E04, EV018). Ce sont des déclarations du fournisseur, pas des validations.

---

## 2. Finances et portée

| ID | Action | Responsable | Nature | Preuve | Échéance | État |
|---|---|---|---|---|---|---|
| **A07** | Ne pas libérer INV-003 tel quel ; ne pas payer la ligne de 18 000 $ « CR-04 » | **Amélie Fortin** (Finances, confirmé) / **Nicolas Perron** | ENG | E10 (24 sept) « Aucune dépense liée à CR-04 ne doit être engagée ou facturée sans nouvelle approbation » (EV052) ; M06 10:25 (EV056) ; CONTRAT p.1 « Gestion des changements » | Immédiat (facture en validation depuis le 22 sept) | Ouvert |
| **A08** | Demander à Boréal une facture corrigée ou une note de crédit de 18 000 $ | **Nicolas Perron** ou **Amélie Fortin** (proposé) | REC | `05_.../INV-003.pdf` p.1 ; `CR-04_..._BROUILLON.pdf` p.1 (EV027, EV050) | **À confirmer** | Ouvert |
| **A09** | Confirmer l'acceptation du **jalon 3 (36 000 $)** avant paiement : aucune preuve d'acceptation dans le corpus | **Nicolas Perron** (proposé) | REC | INV-003 p.1 ; absence de preuve | **À confirmer** | Ouvert |
| **A10** | Clarifier avec Boréal les « ajustements » mobiles déjà commencés : non facturables, et à cesser s'ils dépassent la compatibilité mobile de base | **Nicolas Perron** (proposé) | REC | M06 10:24–10:27 (EV056) ; Teams 22 sept (EV049) ; Decision_Portee_Phase2.md (EV052) | **À confirmer** | Ouvert |
| **A11** | Si le mobile avancé est voulu : soumettre CR-04 à approbation formelle pour la **phase 2** | Boréal (demandeur CR-04) / comité | REC | Decision_Portee_Phase2.md ; CR-04 « APPROBATION REQUISE » | Phase 2, **à confirmer** | Non démarré |

**Situation budgétaire (référence pour A07–A09) :** autorisé 204 000 $ · payé 132 000 $ · INV-003 en validation 54 000 $, dont 36 000 $ potentiellement légitimes · après correction, facturé 168 000 $, solde 36 000 $. Voir Q05 dans [../03_Reponses_Q01-Q10.md](../03_Reponses_Q01-Q10.md).

---

## 3. Documentation et communication (corriger les sources obsolètes)

| ID | Action | Responsable | Nature | Preuve | Échéance | État |
|---|---|---|---|---|---|---|
| **A12** | Mettre à jour le plan projet : P-06 au 22 oct. ; revoir P-04 (tests intégrés, fin 5 oct.) et P-05 (préparation exploitation, fin 10 oct.), calés sur l'ancienne date | **Nicolas Perron** (confirmé : engagement repris dans la note de transition) | ENG | M04 15:25 « On doit mettre les plans … à jour » (EV035) ; Note_transition ligne 7 ; Plan v3 D7:G7 (EV038) ; Teams 15 sept (EV040) | Aucune date fixée. Engagement du 10 sept toujours non réalisé | **En retard** |
| **A13** | Mettre à jour le registre des risques : **fermer R-01** (INT-101 fermé le 17 sept) ; ajouter les dates cibles de R-02, R-03 et R-04 | **Marc Gervais** pour R-01 (propriétaire, confirmé) ; Nicolas Perron pour le registre (proposé) | REC | Registre F2/H2 « Suivi au 9 septembre » (EV061) vs INT-101 (EV043) | **À confirmer** | Ouvert |
| **A14** | Bloquer ou corriger le brouillon d'Alex (« au vert, sécurité et accessibilité complétées ») : aucune réponse documentée à E11 | **Nicolas Perron** (destinataire de E11, proposé) | REC (aligné sur l'engagement E09 « ne pas communiquer le 22 comme un go garanti ») | E11 (EV047) ; E09 (EV059) | Avant toute diffusion | Ouvert |
| **A15** | Émettre un rapport de statut corrigé : Sécurité et Accessibilité JAUNE/ROUGE tant que C1 et C2 ne sont pas validées | **Nicolas Perron** (proposé) | REC | Rapport_Statut_21sept p.1 (EV048) contredit par EV042, EV046, EV058 | **À confirmer** (prochain cycle de rapport) | Ouvert |

---

## 4. Risques à surveiller

| ID | Action | Responsable | Nature | Preuve | Échéance |
|---|---|---|---|---|---|
| **A16** | Anticiper la fin du contrat le **31 oct.** : avec une MEP au 22 oct., il ne reste que 9 jours de marge. Préparer une option d'avenant si un glissement est probable | **Nicolas Perron** (proposé) | REC | CONTRAT p.1 « Période » (EV006) ; M04 15:18 | **À confirmer**, avant le go/no-go (A06) |
| **A17** | Faire vérifier la stabilité de la build annoncée par Boréal (« la build est stable ») : aucune preuve de validation client | Marc Gervais (proposé) | REC | M03 ligne 13 (EV023) ; M06 10:01 | **À confirmer** |

---

## 5. Actions complétées (pour traçabilité, à ne pas rouvrir)

| Action | Validé par | Date | Preuve |
|---|---|---|---|
| Migration de l'hébergement en Canada Central (ADR-007) | Équipe architecture | 27 août | M03 ligne 5 (EV022) |
| ACC-301 labels | Mélissa Gagnon | 15 août | ACC-301 (EV017) |
| ACC-302 contraste | Mélissa Gagnon | 20 août | ACC-302 (EV019) |
| PERF-501 performance de recherche | Support | 7 sept | PERF-501 (EV029) |
| DATA-401 doublons de migration | Camille Beaulieu | 9 sept | DATA-401 (EV032) |
| INT-101 connecteur (cause du report) | Marc Gervais | 17 sept | INT-101, E12 (EV043) |
| Transition chargé de projet → Nicolas Perron | Élodie Caron | 16 sept | E06 (EV041) |
| Clarification de portée CR-04 envoyée à Boréal et aux Finances | Nicolas Perron | 24 sept | E10 (EV052) |

---

## Information manquante (à ne pas inventer)

- Aucune date de prochaine build, de re-test SEC-210 ou de livraison du runbook.
- Aucune date de comité go/no-go fixée.
- Aucune preuve d'acceptation du jalon 3.
- Aucune réponse documentée à Alex (E11) ni réponse formelle de Boréal sur INV-003.
- Aucune preuve technique brute de l'hébergement Canada Central : seule la mention au CR du 27 août.
