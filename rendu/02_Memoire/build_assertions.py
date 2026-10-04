"""Génère rendu/02_Memoire/assertions.csv — couche « machine » de la mémoire NOVA.

Chaque événement de evenements.csv est décomposé en assertions atomiques : UNE clé = UNE valeur,
reliée à UNE preuve exacte (source + ancre). Le résolveur (nova_brain.resolver) décide ensuite
lesquelles sont en vigueur. Ce script n'est qu'une aide de saisie : le CSV produit fait foi
et peut être corrigé à la main (puis rechargé avec python -m nova_brain.assertions).
"""
import csv
from pathlib import Path

OUT = Path(__file__).with_name("assertions.csv")

M01 = "02_Reunions/M01_CR_Demarrage_07juillet.txt"
M02 = "02_Reunions/M02_Transcript_Architecture_23juillet.txt"
M03 = "02_Reunions/M03_CR_Comite_27aout.txt"
M04 = "02_Reunions/M04_Transcript_Comite_direction_10sept.txt"
M05 = "02_Reunions/M05_CR_Suivi_18sept.txt"
M06 = "02_Reunions/M06_Transcript_Comite_26sept.txt"
CH = "04_Documents_projet/Charte_Projet_NOVA_v1.txt"
NOTE = "04_Documents_projet/Note_transition_Elodie_16sept.txt"
PJ = "08_Archives_et_documents_connexes/Plan_NOVA_preliminaire_juin.xlsx"
P2 = "04_Documents_projet/Plan_Projet_NOVA_v2.xlsx"
P3 = "04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx"
REG = "04_Documents_projet/Registre_Risques_29sept.xlsx"
RAP = "04_Documents_projet/Rapport_Statut_21sept.pdf"
F = "05_Contrats_et_finances/"
CON, CR01, CR04 = F + "CONTRAT_Boreal_NOVA.pdf", F + "CR-01_Rapports_avances_APPROUVE.pdf", F + "CR-04_Optimisation_mobile_BROUILLON.pdf"
ADR = "06_Architecture_et_decisions/ADR-007_Localisation_donnees.md"
A1, A2 = "06_Architecture_et_decisions/Architecture_NOVA_v1.pdf", "06_Architecture_et_decisions/Architecture_NOVA_v2.pdf"
DP2 = "06_Architecture_et_decisions/Decision_Portee_Phase2.md"
T15, T16 = "07_Conversations_Teams/Teams_15sept_ProjetNOVA.txt", "07_Conversations_Teams/Teams_16sept_Transition.txt"
T19, T22 = "07_Conversations_Teams/Teams_19sept_Securite.txt", "07_Conversations_Teams/Teams_22sept_Mobile.txt"
RUNBOOK = "03_Tickets/OPS-601_runbook.png"
EML = {n.split("_")[0]: f"01_Courriels/{n}.eml" for n in [
    "E02_Question_hebergement", "E03_Confirmation_Canada_Central", "E04_Corrections_accessibilite",
    "E05_Retard_integration", "E06_Transition_charge_projet", "E07_Facture_003_question",
    "E08_Correctif_journalisation", "E09_Rappel_mise_en_production", "E10_Fonction_mobile",
    "E11_Communication_statut", "E12_Resolution_integration"]}


def TK(t):
    return f"03_Tickets/{t}.txt"


PH1 = "SSO; création et suivi de demandes; pièces jointes; workflow; tableau de suivi; rapports standards"
R = []


def a(ref, cle, val, st, act, src, anc, aut="", date="", lien="", note=""):
    R.append([ref, cle, val, st, act, aut, date, src, anc, lien, note])


# ── Rôles : faits datés, le résolveur en déduit l'autorité de chacun à chaque date
a("EV002", "role:charge_de_projet", "Élodie Caron", "DECISION", "Comité de démarrage", M01, "L9", "comite")
a("EV002", "role:charge_de_projet", "Élodie Caron", "REFLET", "Charte v1", CH, "L4", note="charte non mise à jour automatiquement (ligne 20)")
a("EV041", "role:charge_de_projet", "Nicolas Perron", "DECISION", "Élodie Caron", EML["E06"], "msg", note="« à compter d'aujourd'hui, 16 septembre »")
a("EV041", "role:charge_de_projet", "Nicolas Perron", "DECISION", "Élodie Caron", NOTE, "L4")
a("EV041", "role:charge_de_projet", "Nicolas Perron", "CONSTAT", "Élodie Caron", T16, "L4")
a("ROLE", "role:securite", "Sophie Lambert", "CONSTAT", "Atelier architecture", M02, "L3", note="rôle déduit : « Sophie Lambert (sécurité) »")
a("ROLE", "role:architecture", "Marc Gervais", "CONSTAT", "Atelier architecture", M02, "L3", note="rôle déduit : « Marc Gervais (architecture) »")
a("ROLE", "role:integration", "Marc Gervais", "CONSTAT", "Comité de démarrage", M01, "L16", note="rôle déduit : chargé du connecteur interne ; propriétaire de R-01")
a("ROLE", "role:accessibilite", "Mélissa Gagnon", "CONSTAT", "Mélissa Gagnon", TK("ACC-301"), "L14", note="rôle déduit : analyses des tickets ACC ; propriétaire de R-04")
a("ROLE", "role:exploitation", "Olivier Côté", "CONSTAT", "Olivier Côté", M04, "L12", note="rôle déduit : « Pour l'exploitation... » ; propriétaire de R-03")
a("ROLE", "role:migration", "Camille Beaulieu", "CONSTAT", "Camille Beaulieu", TK("DATA-401"), "L4", note="rôle déduit : demandeuse de DATA-401 ; propriétaire de R-05")
a("ROLE", "role:finances", "Amélie Fortin", "CONSTAT", "Amélie Fortin", EML["E07"], "msg", note="signature « Amélie / Finances »")
a("ORG", "organisation:Julien Moreau", "Boréal", "CONSTAT", "", EML["E05"], "msg", note="adresse @boreal.example")

# ── Échéancier
a("EV001", "projet:date_golive", "2026-10-15", "REFLET", "Plan préliminaire (juin)", PJ, "Plan projet!3", date="2026-06-01", note="version préliminaire ; date exacte du fichier inconnue")
a("EV004", "projet:date_golive", "2026-10-15", "DECISION", "Comité de démarrage", M01, "L11", "comite")
a("EV004", "projet:date_golive", "2026-10-15", "REFLET", "Charte v1", CH, "L7")
a("PLANV2", "projet:date_golive", "2026-10-15", "REFLET", "Plan projet v2", P2, "Plan projet!7", note="« Cible initiale » ; date du fichier inconnue")
a("EV030", "projet:date_golive", "2026-10-22", "PROPOSITION", "Julien Moreau", EML["E05"], "msg", note="« il s'agit d'une proposition de notre part »")
a("EV030", "projet:date_golive", "2026-10-22", "PROPOSITION", "Julien Moreau", M04, "L6", note="recommandation réitérée en comité")
a("EV034", "projet:date_golive", "2026-10-22", "DECISION", "Comité de direction", M04, "L23", "comite", note="formulée par Élodie à 15:22 (ligne 17), aucune opposition, « Donc approuvé » à 15:25")
a("EV036", "golive:reserve", "pas un go automatique : critères sécurité, accessibilité et exploitation maintenus", "DECISION", "Comité de direction", M04, "L24", "comite", note="rappel de Nicolas, confirmé par Sophie à 15:28")
a("EV038", "projet:date_golive", "2026-10-15", "REFLET", "Plan projet v3", P3, "Plan projet!7", date="2026-09-12", note="« Cible de planification » ; date tirée du nom de fichier")
a("EV040", "projet:date_golive", "2026-10-22", "CONSTAT", "Nicolas Perron", T15, "L5", note="« le plan projet n'a visiblement pas encore été corrigé »")
a("M05", "projet:date_golive", "2026-10-22", "CONSTAT", "Suivi livraison", M05, "L13")
a("EV055", "projet:date_golive", "2026-10-22", "DECISION", "Comité de direction", M06, "L16", "comite", note="« c'est conditionnel à ces trois éléments »")
a("EV055", "golive:condition:SEC-210", "validation sécurité de SEC-210", "DECISION", "Comité de direction", M06, "L11", "comite", lien="ticket:SEC-210:statut")
a("EV055", "golive:condition:ACC-303", "fermeture d'ACC-303", "DECISION", "Comité de direction", M06, "L11", "comite", lien="ticket:ACC-303:statut")
a("EV055", "golive:condition:runbook", "approbation du runbook incluant le rollback", "DECISION", "Comité de direction", M06, "L11", "comite", lien="ticket:OPS-601:statut")
a("EV059", "projet:date_golive", "2026-10-22", "CONSTAT", "Nicolas Perron", EML["E09"], "msg", note="rappel écrit")
a("EV059", "communication:golive", "ne pas communiquer le 22 octobre comme un go garanti", "DECISION", "Nicolas Perron", EML["E09"], "msg")
a("EV035", "action:maj_plans_date", "A_FAIRE", "ENGAGEMENT", "Élodie Caron", M04, "L23", note="« On doit mettre les plans et communications à jour »")
a("EV040", "action:maj_plans_date", "A_FAIRE", "CONSTAT", "Nicolas Perron", T15, "L5", note="plan pas encore corrigé au 15 septembre")
a("NOTE", "action:maj_plans_date", "A_FAIRE", "ENGAGEMENT", "Élodie Caron", NOTE, "L7")
a("EV030", "analyse:cause_report_golive", "instabilité du connecteur interne (INT-101)", "DECLARATION", "Julien Moreau", EML["E05"], "msg", lien="ticket:INT-101:statut")
a("EV034", "analyse:cause_report_golive", "instabilité du connecteur interne (INT-101)", "CONSTAT", "Marc Gervais", M04, "L9", lien="ticket:INT-101:statut", note="« le connecteur est le chemin critique »")

# ── Budget, contrat, portée
a("EV003", "projet:budget_initial", "180000", "DECISION", "Comité de démarrage", M01, "L10", "comite")
a("EV003", "projet:budget_initial", "180000", "REFLET", "Charte v1", CH, "L6")
a("EV006", "contrat:plafond", "180000", "DOCUMENT", "Contrat (Organisation Démo)", CON, "p1", "comite", "2026-07-07", note="document contractuel ; montant maximal initial en CAD")
a("EV006", "contrat:fin", "2026-10-31", "DOCUMENT", "Contrat (Organisation Démo)", CON, "p1", "comite", "2026-07-07")
a("EV006", "contrat:regle_changement", "tout travail hors portée exige une demande de changement écrite et approuvée avant exécution et facturation", "DOCUMENT", "Contrat (Organisation Démo)", CON, "p1", "comite", "2026-07-07")
a("EV005", "portee:phase1", PH1, "DECISION", "Comité de démarrage", M01, "L12", "comite")
a("EV006", "portee:phase1", PH1, "DOCUMENT", "Contrat (Organisation Démo)", CON, "p1", "comite", "2026-07-07")
a("EV015", "cr:CR-01:statut", "APPROUVE", "DECISION", "Comité de projet", CR01, "p1", "comite", note="date de décision 14 août 2026")
a("EV015", "cr:CR-01:montant", "24000", "DOCUMENT", "Comité de projet", CR01, "p1", "comite")
a("EV027", "cr:CR-04:statut", "BROUILLON", "DOCUMENT", "Boréal Numérique", CR04, "p1", note="« BROUILLON - APPROBATION REQUISE », aucune signature")
a("EV027", "cr:CR-04:montant", "18000", "PROPOSITION", "Boréal Numérique", CR04, "p1", note="montant estimé")
a("EV051", "cr:CR-04:statut", "BROUILLON", "CONSTAT", "Amélie Fortin", EML["E07"], "msg", note="« rien qui indique qu'il a été approuvé »")
a("EV037", "portee:mobile_avance:phase1", "EXCLU", "DECISION", "Comité de direction", M04, "L35", "comite", note="« Mobile : aucune décision de dépense » ; hors portée actuelle (15:33)")
a("NOTE", "portee:mobile_avance:phase1", "EXCLU", "CONSTAT", "Élodie Caron", NOTE, "L8", note="« ne pas considérer le mobile avancé comme approuvé »")
a("EV049", "portee:mobile_avance:phase1", "INCLUS", "DECLARATION", "Julien Moreau", T22, "L4", note="« je pensais que le mobile était inclus »")
a("EV049", "portee:mobile_avance:phase1", "EXCLU", "CONSTAT", "Nicolas Perron", T22, "L5", note="compatibilité de base oui, CR-04 non approuvé")
a("EV052", "portee:mobile_avance:phase1", "EXCLU", "DECISION", "Nicolas Perron", DP2, "L6")
a("EV052", "portee:mobile_avance:phase2", "REPORTE", "DECISION", "Nicolas Perron", DP2, "L4")
a("EV052", "cr:CR-04:statut", "REPORTE_PHASE2", "DECISION", "Nicolas Perron", DP2, "L4")
a("EV052", "cr:CR-04:facturable", "NON", "DECISION", "Nicolas Perron", EML["E10"], "msg", note="« aucune dépense liée à CR-04 ne doit être engagée ou facturée sans nouvelle approbation »")
a("EV056", "cr:CR-04:facturable", "NON", "DECISION", "Nicolas Perron", M06, "L23", note="« Regarder, oui. Facturer du CR-04, non. »")
a("M06", "action:ajustements_mobiles_boreal", "EN_COURS", "DECLARATION", "Julien Moreau", M06, "L22", note="Boréal a déjà commencé des ajustements mobiles")

# ── Factures
for inv, st, tot, lignes, ref in [("INV-001", "PAYEE", "60000", [("acompte", "60000")], "EV012"),
                                  ("INV-002", "PAYEE", "72000", [("jalon2", "48000"), ("CR-01", "24000")], "EV024"),
                                  ("INV-003", "EN_VALIDATION", "54000", [("jalon3", "36000"), ("CR-04", "18000")], "EV050")]:
    src = F + inv + ".pdf"
    a(ref, f"facture:{inv}:statut", st, "DOCUMENT", "Boréal Numérique", src, "p1", note="statut indiqué sur la facture")
    a(ref, f"facture:{inv}:total", tot, "DOCUMENT", "Boréal Numérique", src, "p1")
    for ligne, montant in lignes:
        a(ref, f"facture:{inv}:ligne:{ligne}", montant, "DOCUMENT", "Boréal Numérique", src, "p1")
a("EV051", "facture:INV-003:statut", "EN_VALIDATION", "CONSTAT", "Amélie Fortin", EML["E07"], "msg", note="libération en attente de l'approbation de CR-04")

# ── Hébergement
a("EV007", "hebergement:production", "East US", "DOCUMENT", "Boréal Numérique", A1, "p1", note="architecture v1, préparée avant la décision de localisation")
a("EV008", "exigence:donnees_au_canada", "données de production au Canada", "PROPOSITION", "Sophie Lambert", EML["E02"], "msg", note="« à trancher demain en atelier »")
a("EV009", "hebergement:production", "Canada Central", "DECISION", "Élodie Caron", M02, "L17", note="tranché en atelier (09:10-09:12), Marc, Sophie et Julien d'accord")
a("EV009", "hebergement:production", "Canada Central", "DECISION", "Élodie Caron", ADR, "L10", note="ADR-007, statut « Acceptée »")
a("EV020", "hebergement:production", "Canada Central", "DOCUMENT", "Boréal Numérique", A2, "p1", note="pièce jointe de E03 : pas une confirmation indépendante")
a("EV021", "hebergement:migration", "COMPLETEE", "DECLARATION", "Julien Moreau", EML["E03"], "msg", note="test de déploiement et de connectivité")
a("EV022", "hebergement:migration", "COMPLETEE", "VALIDATION", "Comité projet", M03, "L5", "comite", note="« déclarée terminée par Boréal et vérifiée par l'équipe architecture »")
a("ADR", "exigence:validation_migration", "une validation technique doit confirmer la migration avant les tests de production", "DECISION", "Élodie Caron", ADR, "L15")

# ── Sécurité
a("EV010", "exigence:securite_sso", "SSO seulement en production, pas de comptes locaux", "DECISION", "Sophie Lambert", M02, "L19")
a("EV011", "exigence:securite_journalisation_admin", "journaliser toutes les actions administrateur, surtout consultation et export", "DECISION", "Sophie Lambert", M02, "L28", note="Boréal : « On vous montrera ça en validation » (09:38)")
a("EV039", "ticket:SEC-210:statut", "OUVERT", "CONSTAT", "Sophie Lambert", TK("SEC-210"), "L18", date="2026-09-12", note="export CSV journalisé sans objet ni résultat ; bloquant avant production")
a("EV045", "livraison:SEC-210", "LIVRE", "DECLARATION", "Julien Moreau", EML["E08"], "msg")
a("EV045", "ticket:SEC-210:statut", "FERME", "DECLARATION", "Julien Moreau", EML["E08"], "msg", note="« pour nous, le problème est corrigé »")
a("EV045", "ticket:SEC-210:statut", "FERME", "DECLARATION", "Boréal", TK("SEC-210"), "L23", note="« Pour nous c'est réglé »")
a("EV045", "ticket:SEC-210:statut", "FERME", "DECLARATION", "Julien Moreau", T19, "L4")
a("EV046", "ticket:SEC-210:statut", "EN_VALIDATION", "CONSTAT", "Sophie Lambert", TK("SEC-210"), "L24", note="« Ne pas fermer avant validation sécurité »")
a("EV046", "ticket:SEC-210:statut", "EN_VALIDATION", "CONSTAT", "Sophie Lambert", T19, "L5", note="« déployé » != « accepté »")
a("M06", "livraison:SEC-210", "LIVRE", "CONSTAT", "Sophie Lambert", M06, "L7", note="« Vous avez livré un fix »")
a("M06", "ticket:SEC-210:statut", "EN_VALIDATION", "CONSTAT", "Sophie Lambert", M06, "L7", note="« Nous n'avons pas encore donné l'acceptation sécurité »")
a("EV058", "ticket:SEC-210:statut", "EN_VALIDATION", "CONSTAT", "Sophie Lambert", TK("SEC-210"), "L25", note="« Re-test planifié »")
a("EV058", "action:retest_SEC-210", "A_FAIRE", "ENGAGEMENT", "Sophie Lambert", TK("SEC-210"), "L25", note="date du re-test non précisée")

# ── Accessibilité
a("EV013", "ticket:ACC-301:statut", "OUVERT", "CONSTAT", "Mélissa Gagnon", TK("ACC-301"), "L14", note="aucun label associé")
a("ACC301", "livraison:ACC-301", "LIVRE", "DECLARATION", "Boréal", TK("ACC-301"), "L15")
a("EV017", "ticket:ACC-301:statut", "FERME", "VALIDATION", "Mélissa Gagnon", TK("ACC-301"), "L16", note="validé NVDA et VoiceOver")
a("EV014", "ticket:ACC-302:statut", "OUVERT", "CONSTAT", "Mélissa Gagnon", TK("ACC-302"), "L14", note="contraste 2,1:1")
a("ACC302", "livraison:ACC-302", "LIVRE", "DECLARATION", "Boréal", TK("ACC-302"), "L15")
a("EV019", "ticket:ACC-302:statut", "FERME", "VALIDATION", "Mélissa Gagnon", TK("ACC-302"), "L16", note="re-test 5,3:1")
a("EV018", "ticket:ACC-301:statut", "FERME", "DECLARATION", "Julien Moreau", EML["E04"], "msg", note="« tout devrait maintenant être conforme »")
a("EV018", "ticket:ACC-302:statut", "FERME", "DECLARATION", "Julien Moreau", EML["E04"], "msg", note="« tout devrait maintenant être conforme »")
a("EV014", "action:test_clavier_modales", "A_FAIRE", "ENGAGEMENT", "Mélissa Gagnon", EML["E04"], "msg", date="2026-08-12", note="citation du 12 août : « repasser les modales au clavier »")
a("M03", "ticket:ACC-301:statut", "FERME", "CONSTAT", "Comité projet", M03, "L11", "comite")
a("M03", "ticket:ACC-302:statut", "FERME", "CONSTAT", "Comité projet", M03, "L11", "comite")
a("M03", "action:test_clavier_modales", "A_FAIRE", "ENGAGEMENT", "Mélissa Gagnon", M03, "L11", note="deuxième passage clavier sur les modales")
a("EV042", "ticket:ACC-303:statut", "OUVERT", "CONSTAT", "Mélissa Gagnon", TK("ACC-303"), "L14", note="Tab n'atteint jamais « Enregistrer » (Chrome, Edge, build 2026.09.17)")
a("EV042", "action:test_clavier_modales", "FAIT", "CONSTAT", "Mélissa Gagnon", TK("ACC-303"), "L14", note="le passage clavier sur les modales a produit ACC-303")
a("M06", "ticket:ACC-303:statut", "OUVERT", "CONSTAT", "Mélissa Gagnon", M06, "L9", note="« Pour moi c'est un bloquant »")
a("EV057", "ticket:ACC-303:statut", "OUVERT", "CONSTAT", "Mélissa Gagnon", TK("ACC-303"), "L16", note="« Correctif annoncé pour la prochaine build »")
a("EV054", "action:correctif_ACC-303", "EN_COURS", "ENGAGEMENT", "Julien Moreau", M06, "L15", note="« dans la prochaine build » : date non précisée")

# ── Intégration, migration, performance
a("EV028", "ticket:INT-101:statut", "OUVERT", "CONSTAT", "Marc Gervais", TK("INT-101"), "L14", note="recherches vides en INT")
a("EV031", "ticket:INT-101:statut", "OUVERT", "CONSTAT", "Marc Gervais", TK("INT-101"), "L16", note="erreurs intermittentes ; risque sur le 15 octobre")
a("INT101", "livraison:INT-101", "LIVRE", "DECLARATION", "Boréal", TK("INT-101"), "L17", note="120 recherches rejouées")
a("EV043", "ticket:INT-101:statut", "FERME", "VALIDATION", "Marc Gervais", TK("INT-101"), "L18", note="« Validé côté intégration. Je ferme. »")
a("EV043", "ticket:INT-101:statut", "FERME", "VALIDATION", "Marc Gervais", EML["E12"], "msg", note="120/120 ; « considéré résolu »")
a("M05", "ticket:INT-101:statut", "FERME", "CONSTAT", "Suivi livraison", M05, "L6")
a("EV025", "ticket:DATA-401:statut", "OUVERT", "CONSTAT", "Camille Beaulieu", TK("DATA-401"), "L14", date="2026-09-02", note="doublons 8401/8402")
a("EV032", "ticket:DATA-401:statut", "FERME", "VALIDATION", "Camille Beaulieu", TK("DATA-401"), "L19", note="rejeu de 15 000 événements sans doublon")
a("EV032", "ticket:DATA-401:statut", "FERME", "CONSTAT", "Camille Beaulieu", M04, "L13")
a("EV026", "ticket:PERF-501:statut", "OUVERT", "CONSTAT", "Support", TK("PERF-501"), "L13")
a("EV029", "ticket:PERF-501:statut", "FERME", "VALIDATION", "Support", TK("PERF-501"), "L16", note="620 ms sur 50 essais")

# ── Exploitation, build
a("EV033", "exigence:exploitation_runbook_final", "runbook final au moins quelques jours avant la mise en production", "DECISION", "Olivier Côté", M04, "L12")
a("M05", "action:runbook_final", "A_FAIRE", "CONSTAT", "Suivi livraison", M05, "L11", note="runbook non final")
a("EV053", "ticket:OPS-601:statut", "OUVERT", "CONSTAT", "Olivier Côté", TK("OPS-601"), "L14", note="il manque au minimum la procédure de rollback")
a("EV053", "action:runbook_etape4_retour_arriere", "A_FAIRE", "DOCUMENT", "Runbook (version du 25 septembre)", RUNBOOK, "capture", date="2026-09-25", note="étape 4 « Procédure de retour arrière » : TODO")
a("EV053", "action:runbook_etape5_validation_post_deploiement", "A_FAIRE", "DOCUMENT", "Runbook (version du 25 septembre)", RUNBOOK, "capture", date="2026-09-25", note="étape 5 « Validation fonctionnelle post-déploiement » : À compléter")
a("M06", "ticket:OPS-601:statut", "OUVERT", "CONSTAT", "Olivier Côté", M06, "L10", note="« Je ne donnerai pas mon go exploitation tant que... »")
a("EV054", "action:runbook_final", "EN_COURS", "ENGAGEMENT", "Julien Moreau", M06, "L15", note="« je relance notre équipe ops »")
a("EV060", "ticket:OPS-601:statut", "OUVERT", "CONSTAT", "Olivier Côté", TK("OPS-601"), "L16", note="« Toujours pas reçu la version finale »")
a("EV060", "action:runbook_final", "A_FAIRE", "CONSTAT", "Olivier Côté", TK("OPS-601"), "L16")
a("EV023", "action:build_stabilisation", "A_FAIRE", "ENGAGEMENT", "Comité projet", M03, "L13", "comite", note="début septembre")
a("M06", "action:build_stabilisation", "FAIT", "DECLARATION", "Julien Moreau", M06, "L6", note="« la build est stable » : non vérifié")

# ── Rapport de statut, registre, communication
for dim, coul, lien, n in [("securite", "VERT", "ticket:SEC-210:statut", "« Correctif SEC-210 livré »"),
                           ("accessibilite", "VERT", "ticket:ACC-303:statut", "« Correctifs appliqués »"),
                           ("exploitation", "JAUNE", "ticket:OPS-601:statut", "« Runbook à finaliser »"),
                           ("echeancier", "VERT", "", "« Cible 22 octobre »")]:
    a("EV048", f"rapport:{dim}", coul, "REFLET", "Rapport de statut du 21 septembre", RAP, "p1", lien=lien,
      note=n + " ; préparé avant la vérification détaillée des tickets")
a("EV047", "communication:statut_projet", "NOVA au vert, sécurité et accessibilité complétées", "PROPOSITION", "Alex Deschamps", EML["E11"], "msg", note="brouillon ; aucune réponse documentée")
a("EV061", "risque:R-01:statut", "OUVERT", "REFLET", "Registre des risques", REG, "Risques!2", date="2026-09-09", lien="ticket:INT-101:statut", note="commentaire H2 « Suivi au 9 septembre 2026 »")
for rid, st, lien, row in [("R-02", "OUVERT", "ticket:SEC-210:statut", 3), ("R-03", "OUVERT", "ticket:OPS-601:statut", 4),
                           ("R-04", "OUVERT", "ticket:ACC-303:statut", 5), ("R-05", "FERME", "ticket:DATA-401:statut", 6)]:
    a("EV062", f"risque:{rid}:statut", st, "REFLET", "Registre des risques", REG, f"Risques!{row}", date="2026-09-29", lien=lien, note="date tirée du nom de fichier")

if __name__ == "__main__":
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ref", "cle", "valeur", "statut", "acteur", "autorite", "date_fait", "source", "ancre", "lien", "note"])
        w.writerows(R)
    print(f"{len(R)} assertions -> {OUT.name}")
