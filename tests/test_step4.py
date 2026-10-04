"""Tests de l'étape 4 : nouvelle information (ingestion → extraction → relecture → rapport), baseline, annulation.

Le LLM d'extraction est simulé : on vérifie les garde-fous du code (ancres, contenu déjà connu,
clés calculées, statuts autorisés), la conservation de la baseline et le contenu du rapport.
"""
import csv
import json
from pathlib import Path

import pytest

from nova_brain import assertions as asr
from nova_brain import db, extraction, nouvelle_info, rapport_maj
from nova_brain.resolver import diff, resoudre

FIXTURE = Path(__file__).parent / "fixtures" / "nouvelle_info_A"


def llm_fixe(par_fichier: dict):
    """Réponse JSON selon le document présent dans le prompt."""
    def appel(prompt):
        for nom, props in par_fichier.items():
            if f"DOCUMENT : {nom}" in prompt:
                return "```json\n" + json.dumps({"assertions": props}, ensure_ascii=False) + "\n```"
        return '{"assertions": []}'
    return appel


PROPS_A = {
    "01_Courriels/E13_Proposition_report.eml": [
        {"ancre": "msg", "cle": "projet:date_golive", "valeur": "29 octobre 2026", "statut": "PROPOSITION",
         "acteur": "Julien Moreau", "note": "nous proposons de déplacer au 29 octobre"},
        {"ancre": "msg", "cle": "livraison:ACC-303", "valeur": "LIVRE", "statut": "DECLARATION", "acteur": "Julien Moreau"},
        {"ancre": "msg", "cle": "ticket:ACC-303:statut", "valeur": "FERME", "statut": "VALIDATION",
         "acteur": "Julien Moreau", "note": "pour nous la modale est conforme"},          # fournisseur : non recevable
        {"ancre": "msg", "cle": "golive:pret", "valeur": "OUI", "statut": "DECISION", "acteur": "Julien Moreau"},  # calculée
        {"ancre": "msg", "cle": "golive:condition:runbook", "valeur": "pas finalisé", "statut": "CONSTAT",
         "acteur": "Julien Moreau"},                                                       # DECISION seulement
        {"ancre": "L99", "cle": "projet:date_golive", "valeur": "2026-10-29", "statut": "PROPOSITION"},  # ancre inexistante
    ],
    "03_Tickets/ACC-303.txt": [
        {"ancre": "L14", "cle": "ticket:ACC-303:statut", "valeur": "OUVERT", "statut": "CONSTAT",
         "acteur": "Mélissa Gagnon"},                                                      # contenu déjà en mémoire
        {"ancre": "ligne 18", "cle": "ticket:ACC-303:statut", "valeur": "OUVERT", "statut": "CONSTAT",
         "acteur": "Mélissa Gagnon", "note": "Re-test clavier planifié le 2 octobre"},
        {"ancre": "L18", "cle": "action:retest_ACC-303", "valeur": "A_FAIRE", "statut": "ENGAGEMENT",
         "acteur": "Mélissa Gagnon"},
    ],
}


@pytest.fixture
def apres_info(copie_reelle, tmp_path):
    con = copie_reelle
    b0 = nouvelle_info.assurer_baseline(con)
    avant = resoudre(con)
    res = nouvelle_info.integrer(con, FIXTURE, partial=True, auto=True, appel_llm=llm_fixe(PROPS_A), out_dir=tmp_path)
    return con, b0, avant, res


def test_ingestion_partielle_de_la_nouvelle_information(apres_info):
    _, _, _, res = apres_info
    ing = res["ingestion"]
    assert ing["nouveau"] == ["01_Courriels/E13_Proposition_report.eml"]
    assert ing["modifie"] == ["03_Tickets/ACC-303.txt"] and ing["absent"] == []


def test_garde_fous_de_l_extraction(apres_info):
    _, _, _, res = apres_info
    rejets = {(r["cle"], r["ancre"]): r["erreur"] for r in res["propositions"] if r["garder"] == "non"}
    assert "calculée" in rejets[("golive:pret", "msg")]
    assert "DECISION" in rejets[("golive:condition:runbook", "msg")]
    assert "introuvable" in rejets[("projet:date_golive", "L99")]
    assert "déjà en mémoire" in rejets[("ticket:ACC-303:statut", "L14")]
    gardes = {(r["cle"], r["ancre"]) for r in res["propositions"] if r["garder"] == "oui"}
    assert ("ticket:ACC-303:statut", "L18") in gardes                      # « ligne 18 » normalisée en L18
    assert res["charge"]["count"] == len(gardes)


def test_nouvelle_proposition_ne_remplace_pas_la_decision(apres_info):
    con, _, _, _ = apres_info
    f = resoudre(con)["projet:date_golive"]
    assert f.valeur == "2026-10-22"
    nouvelle = [a for a in f.historique if a.valeur == "2026-10-29"][0]
    assert nouvelle.statut == "PROPOSITION" and nouvelle.verdict == "proposition non retenue"


def test_aucune_condition_fermee_par_declaration_fournisseur(apres_info):
    con, _, _, _ = apres_info
    faits = resoudre(con)
    t = faits["ticket:ACC-303:statut"]
    assert t.valeur == "OUVERT"
    assert any(a.verdict == "non recevable" and a.valeur == "FERME" for a in t.historique)
    assert faits["livraison:ACC-303"].valeur == "LIVRE"                    # livré ≠ validé
    assert faits["golive:pret"].valeur == "NON"
    for c in ("SEC-210", "ACC-303", "runbook"):
        assert faits[f"golive:condition:{c}:etat"].valeur.startswith("NON REMPLIE")


def test_baseline_conservee(apres_info):
    con, b0, avant, _ = apres_info
    assert diff(avant, resoudre(con, batch_max=b0)) == []
    assert diff(avant, resoudre(con)) != []


def test_rapport_distingue_probleme_decision_proposition(apres_info):
    con, b0, _, _ = apres_info
    md, f0, f1 = rapport_maj.rapport(con, "baseline")
    assert "décision antérieure maintenue : **2026-10-22**" in md
    assert "Nouvelles propositions" in md and "2026-10-29" in md
    assert "Affirmations non recevables" in md
    assert "`livraison:ACC-303` | — | LIVRE" in md
    assert "`action:retest_ACC-303` : — → A_FAIRE" in md
    assert "| ACC-303 | NON REMPLIE" in md and "E13_Proposition_report.eml` — courriel" in md
    assert "NOUVELLE ·" not in md and "RÉSOLUE ·" not in md               # même contradiction, preuve différente
    assert f0["projet:date_golive"]["valeur"] == f1["projet:date_golive"]["valeur"] == "2026-10-22"


def test_annuler_le_lot_d_extraction_revient_a_la_baseline(apres_info):
    con, b0, avant, res = apres_info
    lot = res["charge"]["batch_id"]
    db.annuler_lot(con, lot, "extraction erronée")
    apres = resoudre(con)
    assert not any(c.startswith("livraison:ACC-303") for c in apres)
    assert con.execute("SELECT COUNT(*) FROM assertions WHERE batch_id=?", (lot,)).fetchone()[0] > 0   # rien d'effacé
    with pytest.raises(ValueError, match="déjà"):
        db.annuler_lot(con, lot, "deux fois")
    with pytest.raises(ValueError, match="fichiers"):
        db.annuler_lot(con, 1, "corpus")


def test_relecture_garder_non(copie_reelle, tmp_path):
    con = copie_reelle
    nouvelle_info.assurer_baseline(con)
    res = nouvelle_info.integrer(con, FIXTURE, partial=True, auto=False, appel_llm=llm_fixe(PROPS_A), out_dir=tmp_path)
    assert res["charge"] is None                                           # sans --auto : rien n'est chargé
    rows = list(csv.DictReader(res["csv"].open(encoding="utf-8")))
    for r in rows:
        if r["cle"] == "projet:date_golive":
            r["garder"] = "non"                                            # la personne qui relit rejette
    relu = tmp_path / "relu.csv"
    with relu.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    asr.charger_csv(relu, con=con, kind="extraction")
    f = resoudre(con)["projet:date_golive"]
    assert all(a.valeur != "2026-10-29" for a in f.historique)


def test_snapshot_jamais_ecrase(copie_reelle):
    db.creer_snapshot(copie_reelle, "baseline")
    with pytest.raises(ValueError, match="existe déjà"):
        db.creer_snapshot(copie_reelle, "baseline")


def test_extraction_robuste_aux_pannes_du_llm(copie_reelle):
    con = copie_reelle
    from nova_brain import ingest
    r = ingest.ingest(FIXTURE, kind="upload", partial=True, con=con)

    def panne(prompt):
        raise TimeoutError("quota")
    rows = extraction.extraire(con, r["batch_id"], appel_llm=panne)
    assert rows and all(x["garder"] == "non" and "LLM" in x["erreur"] for x in rows)
    rows = extraction.extraire(con, r["batch_id"], appel_llm=lambda p: "désolé, je ne peux pas")
    assert rows == []


@pytest.mark.parametrize("cle, statut", [
    ("budget:autorise", "DECISION"),
    ("golive:pret", "CONSTAT"),
    ("golive:condition:SEC-210:etat", "DECISION"),
    ("facture:INV-003:montant_conteste", "DOCUMENT"),
    ("golive:condition:X", "PROPOSITION"),
    ("golive:reserve", "DECLARATION"),
])
def test_cles_calculees_ou_reservees(copie_reelle, cle, statut):
    with pytest.raises(asr.AssertionInvalide):
        asr.preparer(copie_reelle, dict(ref="t", cle=cle, valeur="OUI" if "pret" in cle else "1", statut=statut,
                                        acteur="x", autorite="", date_fait="2026-10-01", source="", ancre="",
                                        lien="", note=""))
