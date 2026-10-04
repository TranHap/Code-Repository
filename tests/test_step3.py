"""Tests de l'étape 3 : agent conversationnel et mises à jour par chat.

Le LLM est remplacé par un script déterministe : on teste l'orchestration et les garde-fous du CODE
(citations, confirmation humaine, rétrogradation en DECLARATION, impacts), pas la qualité du modèle.
La qualité réelle sur les 10 questions est mesurée à part (python -m nova_brain.eval_chat).
"""
import json
import re
from types import SimpleNamespace as NS

from nova_brain import mise_a_jour, recherche
from nova_brain.chat import Session
from nova_brain.resolver import resoudre


def reponse(content=None, appels=()):
    calls = [NS(id=f"c{i}", function=NS(name=n, arguments=json.dumps(a))) for i, (n, a) in enumerate(appels)]
    return NS(choices=[NS(message=NS(content=content, tool_calls=calls or None))])


class ScriptLLM:
    """Chaque étape : fonction(messages) -> réponse. Enregistre les messages reçus."""

    def __init__(self, *etapes):
        self.etapes, self.recus = list(etapes), []

    def __call__(self, msgs):
        self.recus.append([dict(m) for m in msgs])
        return self.etapes.pop(0)(msgs)


def dernier_outil(msgs):
    return next(m["content"] for m in reversed(msgs) if m["role"] == "tool")


def premier_handle(texte):
    return re.search(r"\[(S\d+)\]", texte).group(1)


def nb_assertions(con):
    return con.execute("SELECT COUNT(*) FROM assertions").fetchone()[0]


# ───────────────────────── Questions et citations ─────────────────────────

def test_citations_numerotees_et_reference_inventee_signalee(copie_reelle):
    llm = ScriptLLM(
        lambda m: reponse(appels=[("detail_fait", {"cle": "projet:date_golive"})]),
        lambda m: reponse(f"Le 22 octobre [{premier_handle(dernier_outil(m))}], voir aussi [S999]."))
    r = Session(con=copie_reelle, appel_llm=llm).repondre("Date de mise en production ?")
    assert r.texte.startswith("Le 22 octobre [1]") and "[réf. inconnue]" in r.texte
    assert len(r.sources) == 1 and r.sources[0][1].startswith(("01_Courriels/", "02_Reunions/"))
    assert any("S999" in a for a in r.avertissements)


def test_liste_de_citations_et_identifiant_sans_crochets(copie_reelle):
    def fin(m):
        hs = re.findall(r"\[(S\d+)\]", dernier_outil(m))
        return reponse(f"A [{hs[0]}, {hs[1]}] ; B ({hs[2]}) ; S12345 n'est pas une source.")
    llm = ScriptLLM(lambda m: reponse(appels=[("detail_fait", {"cle": "ticket:SEC-210:statut"})]), fin)
    r = Session(con=copie_reelle, appel_llm=llm).repondre("SEC-210 ?")
    assert "A [1][2]" in r.texte and "B ([3])" in r.texte and "S12345" in r.texte
    assert len(r.sources) == 3


def test_relance_si_le_modele_repond_sans_consulter(copie_reelle):
    llm = ScriptLLM(
        lambda m: reponse("Le 15 octobre, de mémoire."),
        lambda m: reponse(appels=[("detail_fait", {"cle": "projet:date_golive"})]),
        lambda m: reponse(f"Le 22 octobre [{premier_handle(dernier_outil(m))}]."))
    r = Session(con=copie_reelle, appel_llm=llm).repondre("Date ?")
    assert "22 octobre" in r.texte and r.outils
    assert any("Vérifie d'abord" in x["content"] for x in llm.recus[1] if x["role"] == "user")


def test_reponse_sans_source_signalee(copie_reelle):
    llm = ScriptLLM(lambda m: reponse(appels=[("chercher_preuves", {"texte": "café froid"})]),
                    lambda m: reponse("Personne ne sait."))
    r = Session(con=copie_reelle, appel_llm=llm).repondre("Café ?")
    assert "réponse sans source citée" in r.avertissements


def test_limite_d_appels(copie_reelle):
    boucle = lambda m: reponse(appels=[("chercher_preuves", {"texte": "runbook"})])
    r = Session(con=copie_reelle, appel_llm=ScriptLLM(*[boucle] * 20)).repondre("Runbook ?")
    assert "limite" in " ".join(r.avertissements)


def test_cle_approximative_suggere_les_bonnes(copie_reelle):
    s = Session(con=copie_reelle)
    out = s._detail("projet:date_mise_en_production")
    assert "clé inconnue" in out and "projet:date_golive" in out


def test_detail_contient_la_synthese_calculee(copie_reelle):
    out = Session(con=copie_reelle)._detail("projet:date_golive")
    assert "PROPOSÉ PAR : Julien Moreau le 2026-09-08" in out
    assert "PREMIÈRE DÉCISION : Comité de direction le 2026-09-10T15:25" in out
    assert "REFLET PÉRIMÉ" in out


def test_recherche_preuves(copie_reelle):
    res = recherche.chercher(copie_reelle, "rollback runbook retour arrière")
    assert any("OPS-601" in r["path"] for r in res[:3])
    dup = recherche.chercher(copie_reelle, "INT-101 fermé connecteur validé 120/120")
    officiel = [i for i, r in enumerate(dup) if r["path"].endswith("E12_Resolution_integration.eml")]
    archive = [i for i, r in enumerate(dup) if "Courriel_archive" in r["path"]]
    assert officiel and (not archive or officiel[0] < archive[0])   # le doublon d'archive passe après


# ───────────────────────── Mises à jour par chat ─────────────────────────

def maj(args):
    return lambda m: reponse(appels=[("proposer_mise_a_jour", args)])


def fin_maj(m):
    return reponse(dernier_outil(m))


def test_maj_refusee_rien_n_est_ecrit(copie_reelle):
    n = nb_assertions(copie_reelle)
    llm = ScriptLLM(maj({"cle": "role:charge_de_projet", "valeur": "Anna Roy"}), fin_maj)
    r = Session(con=copie_reelle, appel_llm=llm, confirmer=lambda p: False).repondre("Anna est CP.")
    assert nb_assertions(copie_reelle) == n and r.texte.startswith("NON ENREGISTRÉ")


def test_session_par_defaut_n_ecrit_jamais(copie_reelle):
    n = nb_assertions(copie_reelle)
    llm = ScriptLLM(maj({"cle": "role:charge_de_projet", "valeur": "Anna Roy", "statut": "DECISION",
                         "acteur": "Comité de direction", "date_fait": "2026-10-02", "preuve": "CR"}), fin_maj)
    Session(con=copie_reelle, appel_llm=llm).repondre("Anna est CP.")      # aucun confirmer fourni
    assert nb_assertions(copie_reelle) == n


def test_maj_sans_preuve_reste_une_declaration(copie_reelle):
    vu = []
    llm = ScriptLLM(maj({"cle": "role:charge_de_projet", "valeur": "Anna Roy", "statut": "DECISION",
                         "acteur": "Comité de direction"}), fin_maj)
    msg = "Le comité a nommé Anna Roy cheffe de projet."
    r = Session(con=copie_reelle, appel_llm=llm, confirmer=lambda p: vu.append(p) or True, utilisateur="Tran").repondre(msg)
    p = vu[0]
    assert p.statut == "DECLARATION" and p.acteur == "Tran (chat)" and "selon l'utilisateur : Comité de direction" in p.note
    assert any("manquant" in a for a in p.avertissements) and r.mises_a_jour
    f = resoudre(copie_reelle)["role:charge_de_projet"]
    assert f.valeur == "Nicolas Perron"
    chat = [a for a in f.historique if a.origine.startswith("chat:")][0]
    assert chat.verdict == "déclaration non confirmée"
    ev = copie_reelle.execute("SELECT texte, auteur FROM evidence WHERE ev_id = ?", (chat.ev_id,)).fetchone()
    assert ev["texte"] == msg and ev["auteur"] == "Tran"                    # le message est une preuve citable


def test_maj_documentee_change_le_fait_et_garde_l_historique(copie_reelle):
    vu = []
    llm = ScriptLLM(maj({"cle": "role:charge_de_projet", "valeur": "Anna Roy", "statut": "DECISION",
                         "acteur": "Comité de direction", "date_fait": "2026-10-02",
                         "preuve": "compte rendu du comité du 2 octobre"}), fin_maj)
    Session(con=copie_reelle, appel_llm=llm, confirmer=lambda p: vu.append(p) or True).repondre("...")
    assert any("role:charge_de_projet" in i and "Anna Roy" in i for i in vu[0].impacts)
    assert any("non versée" in a for a in vu[0].avertissements)
    f = resoudre(copie_reelle)["role:charge_de_projet"]
    assert f.valeur == "Anna Roy" and f.retenu.niveau == "comite"
    assert {"Élodie Caron", "Nicolas Perron"} <= {a.valeur for a in f.historique}   # rien n'est effacé
    assert resoudre(copie_reelle, as_of="2026-09-30")["role:charge_de_projet"].valeur == "Nicolas Perron"


def test_maj_ne_ferme_pas_une_condition_sans_le_bon_role(copie_reelle):
    """« SEC-210 est validé » dit par l'utilisateur, avec preuve mais par un acteur sans le rôle sécurité."""
    vu = []
    llm = ScriptLLM(maj({"cle": "ticket:SEC-210:statut", "valeur": "FERME", "statut": "VALIDATION",
                         "acteur": "Nicolas Perron", "date_fait": "2026-10-01", "preuve": "courriel"}), fin_maj)
    Session(con=copie_reelle, appel_llm=llm, confirmer=lambda p: vu.append(p) or True).repondre("SEC-210 validé")
    faits = resoudre(copie_reelle)
    assert faits["ticket:SEC-210:statut"].valeur == "EN_VALIDATION"
    assert faits["golive:pret"].valeur == "NON"
    assert vu[0].impacts == [] and any("aucun fait ne change" in a for a in vu[0].avertissements)


def test_maj_validee_par_la_bonne_personne_met_a_jour_les_conditions(copie_reelle):
    vu = []
    llm = ScriptLLM(maj({"cle": "ticket:SEC-210:statut", "valeur": "fermé", "statut": "VALIDATION",
                         "acteur": "Sophie Lambert", "date_fait": "2026-10-01", "preuve": "courriel de Sophie du 1er octobre"}), fin_maj)
    Session(con=copie_reelle, appel_llm=llm, confirmer=lambda p: vu.append(p) or True).repondre("Sophie a validé SEC-210")
    imp = " ".join(vu[0].impacts)
    assert "ticket:SEC-210:statut" in imp and "golive:condition:SEC-210:etat" in imp and "rapport:securite" in imp
    faits = resoudre(copie_reelle)
    assert faits["golive:condition:SEC-210:etat"].valeur.startswith("REMPLIE")
    assert faits["golive:pret"].valeur == "NON"                     # ACC-303 et runbook restent ouverts


def test_maj_cle_invalide_aide_le_modele(copie_reelle):
    n = nb_assertions(copie_reelle)
    llm = ScriptLLM(maj({"cle": "projet:responsable", "valeur": "Anna"}), fin_maj)
    r = Session(con=copie_reelle, appel_llm=llm, confirmer=lambda p: True).repondre("Anna responsable")
    assert "proposition invalide" in r.texte and "role:{role}" in r.texte
    assert nb_assertions(copie_reelle) == n


def test_apercu_d_impact_n_ecrit_rien(copie_reelle):
    n = nb_assertions(copie_reelle)
    p = mise_a_jour.preparer(copie_reelle, "projet:date_golive", "2026-10-29", "DECISION", "Comité de direction",
                             "2026-10-01", "CR du 1er octobre")
    assert any(i.startswith("projet:date_golive") for i in p.impacts)
    assert nb_assertions(copie_reelle) == n
    assert resoudre(copie_reelle)["projet:date_golive"].valeur == "2026-10-22"


def test_historique_garde_les_identifiants_bruts(copie_reelle):
    """Le 2e tour ne doit pas voir « [1] » (sinon le modèle imite un format non vérifiable)."""
    llm = ScriptLLM(
        lambda m: reponse(appels=[("detail_fait", {"cle": "projet:date_golive"})]),
        lambda m: reponse(f"Le 22 octobre [{premier_handle(dernier_outil(m))}]."),
        lambda m: reponse(appels=[("detail_fait", {"cle": "role:charge_de_projet"})]),
        lambda m: reponse(f"Nicolas [{premier_handle(dernier_outil(m))}]."))
    s = Session(con=copie_reelle, appel_llm=llm)
    s.repondre("Date ?")
    r2 = s.repondre("Responsable ?")
    precedent = [x["content"] for x in llm.recus[2] if x["role"] == "assistant"][0]
    assert re.search(r"\[S\d+\]", precedent) and "[1]" not in precedent
    assert r2.texte == "Nicolas [1]." and r2.sources                     # numérotation propre à chaque réponse


def test_synthese_en_vigueur_depuis(copie_reelle):
    out = Session(con=copie_reelle)._detail("role:charge_de_projet")
    assert "EN VIGUEUR DEPUIS : Élodie Caron le 2026-09-16" in out
