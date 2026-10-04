"""Tests de l'étape 2 : vocabulaire, politique, assertions, résolveur.

A. Les 10 questions du défi, sur le vrai corpus (réponse ET nuance : qui propose / décide / valide).
B. Concordance avec les verdicts écrits à la main dans evenements.csv.
C. Situations synthétiques difficiles (autorité, conflits, rôles datés, mise à jour par chat, politique).
"""
import json
import shutil

import pytest

from nova_brain import assertions as asr
from nova_brain import config, db, ingest, policy as pol, seed_events
from nova_brain.resolver import resoudre, diff
from nova_brain.vocab import VocabError, normaliser_valeur

CSV_ASSERTIONS = config.ROOT / "rendu" / "02_Memoire" / "assertions.csv"


# ───────────────────────── Fixtures ─────────────────────────

@pytest.fixture(scope="module")
def reel(tmp_path_factory):
    """Mémoire complète du vrai corpus, dans une base temporaire."""
    if not config.CORPUS_DEFAULT.exists():
        pytest.skip("corpus absent")
    con = db.connect(tmp_path_factory.mktemp("reel") / "m.db")
    cache = json.loads(config.VISION_CACHE.read_text(encoding="utf-8")) if config.VISION_CACHE.exists() else {}
    ingest.ingest(config.CORPUS_DEFAULT, con=con, transcrire=lambda b: cache.get(ingest.sha(b), "[capture non transcrite]"))
    seed_events.seed(seed_events.DEFAULT, con=con)
    asr.charger_csv(CSV_ASSERTIONS, con=con)
    yield con
    con.close()


@pytest.fixture(scope="module")
def faits(reel):
    return resoudre(reel)


@pytest.fixture
def mem(tmp_path_factory):
    """Mémoire vide + rôles de base, pour les scénarios synthétiques."""
    con = db.connect(tmp_path_factory.mktemp("syn") / "m.db")
    b = db.new_batch(con, "test", "base")
    add(con, b, "role:charge_de_projet", "Élodie Caron", "DECISION", "Comité", "2026-07-07", autorite="comite")
    add(con, b, "role:securite", "Sophie Lambert", "CONSTAT", "Comité", "2026-07-07")
    add(con, b, "organisation:Julien Moreau", "Boréal", "CONSTAT", "", "2026-07-07")
    con.commit()
    yield con, b
    con.close()


def add(con, batch, cle, valeur, statut, acteur, date, autorite="", lien="", ref="T"):
    row = dict(ref=ref, cle=cle, valeur=valeur, statut=statut, acteur=acteur, autorite=autorite, date_fait=date,
               source="", ancre="", lien=lien, note="")
    return asr.inserer(con, asr.preparer(con, row), "test", batch)


def verdicts(f):
    return [(a.ref, a.valeur, a.verdict) for a in f.historique]


# ───────────────────────── A. Les 10 questions ─────────────────────────

def test_q01_date_approuvee_et_reserve(faits):
    f = faits["projet:date_golive"]
    assert f.valeur == "2026-10-22" and f.retenu.niveau == "comite"
    assert {c.split(":")[2] for c in faits if c.startswith("golive:condition:") and c.count(":") == 2} == {"SEC-210", "ACC-303", "runbook"}
    assert "pas un go automatique" in faits["golive:reserve"].valeur


def test_q02_cause_et_etat_actuel(faits):
    assert "INT-101" in faits["analyse:cause_report_golive"].valeur
    t = faits["ticket:INT-101:statut"]
    assert t.valeur == "FERME" and [v.acteur for v in t.validations] == ["Marc Gervais", "Marc Gervais"]
    assert t.validations[0].date.startswith("2026-09-17")


def test_q03_proposition_vs_approbation(faits):
    f = faits["projet:date_golive"]
    prop = f.proposee_par[0]
    assert prop.acteur == "Julien Moreau" and prop.date.startswith("2026-09-08") and prop.verdict == "proposition adoptée"
    premiere = f.decisions[0]
    assert premiere.ref == "EV034" and premiere.date.startswith("2026-09-10") and premiere.ev_id.endswith("#L23")


def test_q04_responsable_et_depuis_quand(faits):
    f = faits["role:charge_de_projet"]
    assert f.valeur == "Nicolas Perron"
    assert min(d.date for d in f.decisions).startswith("2026-09-16")
    assert all(d.niveau == "charge_de_projet" for d in f.decisions)   # nommé par Élodie, alors CP
    assert ("EV002", "Élodie Caron", "remplacé") in verdicts(f)


def test_q05_montant_autorise_et_calcul(faits):
    f = faits["budget:autorise"]
    assert f.valeur == "204000"
    assert "180 000" in f.explication and "CR-01" in f.explication and "CR-04" in f.explication


def test_q06_inv003_montant_conteste(faits):
    assert faits["facture:INV-003:montant_conteste"].valeur == "18000"
    assert faits["facture:INV-003:statut"].valeur == "EN_VALIDATION"
    assert any("CR-04" in a for a in faits["facture:INV-003:statut"].alertes)
    assert faits["cr:CR-04:facturable"].valeur == "NON"


def test_q07_hebergement_et_preuve(faits):
    f = faits["hebergement:production"]
    assert f.valeur == "Canada Central"
    assert ("EV007", "East US", "remplacé") in verdicts(f)
    m = faits["hebergement:migration"]
    assert m.valeur == "COMPLETEE" and m.validations[0].ev_id.endswith("M03_CR_Comite_27aout.txt#L5")
    assert any(a.verdict == "déclaration confirmée" for a in m.historique)   # Boréal l'avait déclarée


def test_q08_securite_livree_pas_validee(faits):
    assert faits["livraison:SEC-210"].valeur == "LIVRE"
    t = faits["ticket:SEC-210:statut"]
    assert t.valeur == "EN_VALIDATION" and t.retenu.acteur == "Sophie Lambert"
    boreal = [a for a in t.historique if a.statut == "DECLARATION"]
    assert len(boreal) == 3 and all(a.verdict == "déclaration non confirmée" for a in boreal)
    assert any("SEC-210" in a for a in faits["rapport:securite"].alertes)   # le rapport « VERT » est périmé


def test_q09_accessibilite(faits):
    assert faits["ticket:ACC-301:statut"].valeur == "FERME"
    assert faits["ticket:ACC-302:statut"].valeur == "FERME"
    assert faits["ticket:ACC-303:statut"].valeur == "OUVERT"
    assert any("ACC-303" in a for a in faits["rapport:accessibilite"].alertes)


def test_q10_conditions_et_runbook(faits):
    assert faits["golive:pret"].valeur == "NON"
    for c in ("SEC-210", "ACC-303", "runbook"):
        assert faits[f"golive:condition:{c}:etat"].valeur.startswith("NON REMPLIE")
    for etape in ("runbook_etape4_retour_arriere", "runbook_etape5_validation_post_deploiement"):
        f = faits[f"action:{etape}"]
        assert f.valeur == "A_FAIRE" and f.retenu.ev_id.endswith("OPS-601_runbook.png#capture")


def test_contradictions_plan_et_registre(faits):
    plan_v3 = [a for a in faits["projet:date_golive"].historique if a.ref == "EV038"][0]
    assert plan_v3.verdict == "reflet périmé"
    assert any("INT-101" in a for a in faits["risque:R-01:statut"].alertes)
    assert not faits["risque:R-05:statut"].alertes        # R-05 fermé et DATA-401 fermé : cohérent


def test_chaque_assertion_a_une_preuve(faits):
    sans = [a.ref for f in faits.values() for a in f.historique if not a.ev_id]
    assert sans == []


def test_etat_a_une_date_passee(reel):
    f = resoudre(reel, as_of="2026-09-09")
    assert f["projet:date_golive"].valeur == "2026-10-15"           # la proposition du 8 n'est pas une décision
    assert f["role:charge_de_projet"].valeur == "Élodie Caron"
    assert f["ticket:INT-101:statut"].valeur == "OUVERT"


# ───────────────────────── B. Concordance avec evenements.csv ─────────────────────────

def test_concordance_avec_verdicts_manuels(reel, faits):
    """Ce que l'équipe a jugé à la main doit être retrouvé par le résolveur, sans lire la colonne de verdict."""
    manuels = {r["ref"]: (r["type"], r["note"] or "") for r in reel.execute("SELECT ref, type, note FROM events")}
    par_ref = {}
    for f in faits.values():
        for a in f.historique:
            par_ref.setdefault(a.ref, []).append((a, f))
    ecarts = []
    for ref, (typ, note) in manuels.items():
        if ref not in par_ref:
            continue
        lst = par_ref[ref]
        if note.startswith(("historique (remplacé)", "remplacé", "contredit")):
            signale = any(a.verdict not in ("retenu", "concordant") or any(ref in x for x in f.alertes) for a, f in lst)
            if not signale:
                ecarts.append(f"{ref} jugé « {note} » mais rien n'est signalé")
        if typ == "DECISION" and note.startswith("actuel"):
            ok = ("retenu", "concordant", "reflet cohérent", "déclaration confirmée", "proposition adoptée")
            bad = [(a.cle, a.verdict) for a, _ in lst if a.verdict not in ok]
            if bad:
                ecarts.append(f"{ref} décision actuelle mais {bad}")
    assert ecarts == []


# ───────────────────────── C. Scénarios synthétiques ─────────────────────────

def test_autorite_avant_date(mem):
    con, b = mem
    add(con, b, "projet:date_golive", "2026-10-22", "DECISION", "Comité de direction", "2026-09-10", autorite="comite", ref="COM")
    add(con, b, "projet:date_golive", "2026-10-29", "DECISION", "Élodie Caron", "2026-09-20", ref="CP")
    f = resoudre(con)["projet:date_golive"]
    assert f.valeur == "2026-10-22"
    assert ("CP", "2026-10-29", "écarté") in verdicts(f)


def test_meme_autorite_plus_recent_gagne(mem):
    con, b = mem
    add(con, b, "projet:date_golive", "2026-10-15", "DECISION", "Comité", "2026-07-07", autorite="comite")
    add(con, b, "projet:date_golive", "2026-10-22", "DECISION", "Comité", "2026-09-10", autorite="comite")
    assert resoudre(con)["projet:date_golive"].valeur == "2026-10-22"


def test_conflit_jamais_tranche_au_hasard(mem):
    con, b = mem
    add(con, b, "projet:date_golive", "2026-10-22", "DECISION", "Comité", "2026-09-10T15:25", autorite="comite")
    add(con, b, "projet:date_golive", "2026-10-29", "DECISION", "Comité", "2026-09-10T15:25", autorite="comite")
    f = resoudre(con)["projet:date_golive"]
    assert f.etat == "conflit" and f.valeur is None and f.alertes


def test_proposition_seule_ne_decide_rien(mem):
    con, b = mem
    add(con, b, "projet:date_golive", "2026-10-22", "PROPOSITION", "Julien Moreau", "2026-09-08")
    f = resoudre(con)["projet:date_golive"]
    assert f.etat == "non_decide" and f.valeur is None


def test_fournisseur_ne_peut_pas_valider_la_securite(mem):
    con, b = mem
    add(con, b, "ticket:SEC-210:statut", "OUVERT", "CONSTAT", "Sophie Lambert", "2026-09-12")
    add(con, b, "ticket:SEC-210:statut", "FERME", "VALIDATION", "Julien Moreau", "2026-09-19", ref="FAUX")
    f = resoudre(con)["ticket:SEC-210:statut"]
    assert f.valeur == "OUVERT"
    assert ("FAUX", "FERME", "non recevable") in verdicts(f)


def test_meme_le_charge_de_projet_ne_ferme_pas_un_ticket_securite(mem):
    con, b = mem
    add(con, b, "ticket:SEC-210:statut", "OUVERT", "CONSTAT", "Sophie Lambert", "2026-09-12")
    add(con, b, "ticket:SEC-210:statut", "FERME", "VALIDATION", "Élodie Caron", "2026-09-20", ref="CP")
    assert resoudre(con)["ticket:SEC-210:statut"].valeur == "OUVERT"


def test_ticket_sans_domaine_fermable_sauf_par_fournisseur(mem):
    con, b = mem
    add(con, b, "ticket:PERF-501:statut", "OUVERT", "CONSTAT", "Support", "2026-09-03")
    add(con, b, "ticket:PERF-501:statut", "FERME", "VALIDATION", "Boréal", "2026-09-05", ref="BOREAL")
    assert resoudre(con)["ticket:PERF-501:statut"].valeur == "OUVERT"
    add(con, b, "ticket:PERF-501:statut", "FERME", "VALIDATION", "Support", "2026-09-07")
    assert resoudre(con)["ticket:PERF-501:statut"].valeur == "FERME"


def test_ticket_rouvert_apres_validation(mem):
    con, b = mem
    add(con, b, "ticket:SEC-210:statut", "FERME", "VALIDATION", "Sophie Lambert", "2026-10-01")
    add(con, b, "ticket:SEC-210:statut", "OUVERT", "CONSTAT", "Sophie Lambert", "2026-10-05", ref="REOUV")
    assert resoudre(con)["ticket:SEC-210:statut"].valeur == "OUVERT"


def test_changement_de_responsable_par_chat(mem):
    """« Anna est maintenant responsable » : déclaration non confirmée tant qu'aucune décision n'existe."""
    con, b = mem
    add(con, b, "role:charge_de_projet", "Anna Roy", "DECLARATION", "Utilisateur (chat)", "2026-10-03", ref="CHAT")
    f = resoudre(con)["role:charge_de_projet"]
    assert f.valeur == "Élodie Caron" and ("CHAT", "Anna Roy", "déclaration non confirmée") in verdicts(f)

    add(con, b, "role:charge_de_projet", "Anna Roy", "DECISION", "Comité de direction", "2026-10-02", autorite="comite", ref="COM")
    add(con, b, "projet:date_golive", "2026-10-29", "DECISION", "Anna Roy", "2026-10-03", ref="ANNA_APRES")
    add(con, b, "exigence:securite_x", "y", "DECISION", "Anna Roy", "2026-10-01", ref="ANNA_AVANT")
    faits = resoudre(con)
    assert faits["role:charge_de_projet"].valeur == "Anna Roy"
    assert faits["projet:date_golive"].retenu.niveau == "charge_de_projet"          # CP depuis le 2 octobre
    assert faits["exigence:securite_x"].retenu.niveau == "partie_prenante"          # pas encore CP le 1er
    elodie = [a for a in faits["role:charge_de_projet"].historique if a.valeur == "Élodie Caron"][0]
    assert elodie.verdict == "remplacé"                                              # historique conservé


def test_decision_ancienne_reste_valide_apres_depart(mem):
    con, b = mem
    add(con, b, "hebergement:production", "Canada Central", "DECISION", "Élodie Caron", "2026-07-23", ref="ELODIE")
    add(con, b, "role:charge_de_projet", "Nicolas Perron", "DECISION", "Élodie Caron", "2026-09-16")
    f = resoudre(con)["hebergement:production"]
    assert f.valeur == "Canada Central" and f.retenu.niveau == "charge_de_projet"


def test_budget_plusieurs_cr(mem):
    con, b = mem
    add(con, b, "contrat:plafond", "180 000 $", "DOCUMENT", "Contrat", "2026-07-07", autorite="comite")
    for cr, st, m in [("CR-01", "APPROUVE", "24000"), ("CR-02", "APPROUVE", "6 000"), ("CR-03", "REFUSE", "9000")]:
        add(con, b, f"cr:{cr}:statut", st, "DECISION", "Comité", "2026-08-14", autorite="comite")
        add(con, b, f"cr:{cr}:montant", m, "DOCUMENT", "Comité", "2026-08-14", autorite="comite")
    f = resoudre(con)["budget:autorise"]
    assert f.valeur == "210000" and "CR-03" in f.explication


def test_facture_avec_cr_approuve_non_contestee(mem):
    con, b = mem
    add(con, b, "cr:CR-01:statut", "APPROUVE", "DECISION", "Comité", "2026-08-14", autorite="comite")
    add(con, b, "facture:INV-002:ligne:CR-01", "24000", "DOCUMENT", "Boréal", "2026-08-31")
    assert "facture:INV-002:montant_conteste" not in resoudre(con)


def test_lot_de_curation_remplace_et_snapshot(tmp_path, mem):
    con, _ = mem
    hdr = "ref,cle,valeur,statut,acteur,autorite,date_fait,source,ancre,lien,note\n"
    p = tmp_path / "a.csv"
    p.write_text(hdr + "X,projet:date_golive,2026-10-15,DECISION,Comité,comite,2026-07-07,,,,\n", encoding="utf-8")
    b1 = asr.charger_csv(p, con=con)["batch_id"]
    p.write_text(hdr + "X,projet:date_golive,2026-10-22,DECISION,Comité,comite,2026-09-10,,,,\n", encoding="utf-8")
    r2 = asr.charger_csv(p, con=con)
    assert r2["supersedes"] == b1
    assert resoudre(con)["projet:date_golive"].valeur == "2026-10-22"
    assert len(resoudre(con)["projet:date_golive"].historique) == 1                # l'ancien lot n'est plus actif
    assert resoudre(con, batch_max=b1)["projet:date_golive"].valeur == "2026-10-15"  # mais le snapshot le retrouve


def test_csv_invalide_rien_n_est_charge(tmp_path, mem):
    con, _ = mem
    n = con.execute("SELECT COUNT(*) FROM assertions").fetchone()[0]
    p = tmp_path / "bad.csv"
    p.write_text("ref,cle,valeur,statut,acteur,autorite,date_fait,source,ancre,lien,note\n"
                 "A,projet:date_golive,2026-10-22,DECISION,Comité,comite,,,,,\n"
                 "B,ticket:SEC-210:statut,PRESQUE,CONSTAT,Sophie,,2026-09-01,,,,\n"
                 "C,cle:inventee,x,CONSTAT,Sophie,,2026-09-01,,,,\n"
                 "D,projet:date_golive,2026-10-22,DECIDE,Comité,,2026-09-01,,,,\n"
                 "E,projet:date_golive,2026-10-22,DECISION,Comité,,,02/M04.txt,L17,,\n", encoding="utf-8")
    with pytest.raises(asr.AssertionInvalide) as e:
        asr.charger_csv(p, con=con)
    msg = str(e.value)
    assert "4 assertion(s) invalide(s)" in msg and "PRESQUE" in msg and "cle:inventee" in msg and "DECIDE" in msg
    assert con.execute("SELECT COUNT(*) FROM assertions").fetchone()[0] == n


def test_date_relue_sur_la_preuve_courante(tmp_path, mem):
    """Une assertion sans date explicite suit la nouvelle version de sa preuve."""
    con, b = mem
    d = tmp_path / "corpus"
    (d / "02").mkdir(parents=True)
    (d / "02" / "CR.txt").write_text("CR NOVA\nDate : 7 juillet 2026\nDécision : 15 octobre", encoding="utf-8")
    ingest.ingest(d, con=con)
    asr.inserer(con, asr.preparer(con, dict(ref="R", cle="projet:date_golive", valeur="2026-10-15", statut="DECISION",
                                            acteur="Comité", autorite="comite", date_fait="", source="02/CR.txt",
                                            ancre="L3", lien="", note="")), "test", b)
    assert resoudre(con)["projet:date_golive"].retenu.date == "2026-07-07"
    (d / "02" / "CR.txt").write_text("CR NOVA\nDate : 8 juillet 2026\nDécision : 15 octobre", encoding="utf-8")
    ingest.ingest(d, kind="upload", con=con)
    assert resoudre(con)["projet:date_golive"].retenu.date == "2026-07-08"


# ───────────────────────── Politique et vocabulaire ─────────────────────────

def _policy_variant(tmp_path, old, new):
    p = tmp_path / "p.toml"
    p.write_text(pol.DEFAULT.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8")
    return p


def test_changer_la_politique_change_le_resultat_et_le_diff(tmp_path, reel, faits):
    p = _policy_variant(tmp_path, "fournisseur = 5", "fournisseur = 0")   # le fournisseur devient l'autorité suprême
    autre = resoudre(reel, pol.load(p))
    assert faits["cr:CR-04:statut"].valeur == "REPORTE_PHASE2"
    assert autre["cr:CR-04:statut"].valeur == "BROUILLON"               # le document Boréal l'emporte sur la décision du CP
    assert autre["hebergement:production"].valeur == "Canada Central"   # l'architecture v2 de Boréal, plus récente
    changes = diff(faits, autre)
    assert any(c.startswith("cr:CR-04:statut") for c in changes)
    assert not any(c.startswith("ticket:SEC-210") for c in changes)     # famille ticket : date d'abord, inchangé


@pytest.mark.parametrize("old, new, msg", [
    ('motif = "*"', 'motif = "projet:*"', "famille par défaut"),
    ('gagnant = ["DECISION", "VALIDATION", "DOCUMENT"]', 'gagnant = ["DECISION", "APPROUVE"]', "statuts gagnants invalides"),
    ('"conditions_golive"]', '"conditions_golive", "regle_inexistante"]', "règles inconnues"),
    ("non_officiel = 7", "", "autorite"),
    ('ordre = ["autorite", "date_fait"]          # une', 'ordre = ["popularite"]          # une', "ordre doit"),
])
def test_politique_invalide_refusee(tmp_path, old, new, msg):
    with pytest.raises(pol.PolicyError, match=msg):
        pol.load(_policy_variant(tmp_path, old, new))


@pytest.mark.parametrize("cle, val, attendu", [
    ("contrat:plafond", "180 000 $ CAD", "180000"),
    ("projet:date_golive", "22 octobre 2026", "2026-10-22"),
    ("ticket:SEC-210:statut", "Fermé", "FERME"),
    ("facture:INV-003:statut", "Payée", "PAYEE"),
    ("hebergement:migration", "complétée", "COMPLETEE"),
])
def test_normalisation_valeurs(cle, val, attendu):
    assert normaliser_valeur(cle, val) == attendu


@pytest.mark.parametrize("cle, val", [
    ("projet:date_go_live", "2026-10-22"),     # clé mal orthographiée
    ("projet:date_golive", "bientôt"),
    ("ticket:SEC-210:statut", "presque fermé"),
    ("contrat:plafond", "beaucoup"),
    ("ticket:SEC-210:statut", ""),
])
def test_valeurs_refusees(cle, val):
    with pytest.raises(VocabError):
        normaliser_valeur(cle, val)
