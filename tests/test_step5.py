"""Tests de l'interface Streamlit (sans navigateur) : chargement, onglets, recherche, chat avec confirmation."""
import json
from types import SimpleNamespace as NS

import pytest
from streamlit.testing.v1 import AppTest

from nova_brain import config, llm

APP = str(config.ROOT / "app.py")


@pytest.fixture
def app(copie_reelle, monkeypatch):
    path = copie_reelle.execute("PRAGMA database_list").fetchone()["file"]
    monkeypatch.setattr(config, "DB_PATH", type(config.DB_PATH)(path))
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at, copie_reelle


def faux_llm(*reponses):
    it = iter(reponses)

    def chat(messages, **kw):
        nom, args, texte = next(it)
        calls = [NS(id="c1", function=NS(name=nom, arguments=json.dumps(args)))] if nom else None
        return NS(choices=[NS(message=NS(content=texte, tool_calls=calls))])
    return chat


def test_chargement_et_etat_du_projet(app):
    at, _ = app
    assert len(at.tabs) == 6
    metriques = {m.label: m.value for m in at.metric}
    assert metriques["Mise en production"] == "2026-10-22"
    assert metriques["Go-live prêt"] == "NON"
    assert metriques["Chargé de projet"] == "Nicolas Perron"
    assert any("reflet périmé" in w.value for w in at.warning)


def test_recherche_de_preuves(app):
    at, _ = app
    champ = next(t for t in at.text_input if t.label.startswith("Rechercher"))
    champ.set_value("rollback runbook").run()
    assert not at.exception
    assert any("OPS-601" in e.label for e in at.expander)


def test_chat_proposition_puis_confirmation_par_bouton(app, monkeypatch):
    at, con = app
    monkeypatch.setattr(llm, "chat", faux_llm(
        ("proposer_mise_a_jour", {"cle": "role:charge_de_projet", "valeur": "Anna Roy", "statut": "DECISION",
                                  "acteur": "Comité de direction", "date_fait": "2026-10-02",
                                  "preuve": "CR du comité du 2 octobre"}, ""),
        (None, None, "Proposition affichée : à confirmer.")))
    n = con.execute("SELECT COUNT(*) FROM assertions").fetchone()[0]
    at.chat_input[0].set_value("Le comité a nommé Anna Roy le 2 octobre (CR du 2 octobre).").run()
    assert not at.exception
    assert con.execute("SELECT COUNT(*) FROM assertions").fetchone()[0] == n          # rien d'écrit avant le clic
    assert any("Mise à jour proposée" in m.value for m in at.markdown)
    at.button(key="ok0").click().run()
    assert not at.exception
    assert con.execute("SELECT COUNT(*) FROM assertions").fetchone()[0] == n + 1
    assert {m.label: m.value for m in at.metric}["Chargé de projet"] == "Anna Roy"


def test_chat_rejet_par_bouton(app, monkeypatch):
    at, con = app
    monkeypatch.setattr(llm, "chat", faux_llm(
        ("proposer_mise_a_jour", {"cle": "role:charge_de_projet", "valeur": "Anna Roy"}, ""),
        (None, None, "En attente.")))
    n = con.execute("SELECT COUNT(*) FROM assertions").fetchone()[0]
    at.chat_input[0].set_value("Anna est CP").run()
    at.button(key="ko0").click().run()
    assert con.execute("SELECT COUNT(*) FROM assertions").fetchone()[0] == n
    assert any("Rejeté" in m.value for m in at.markdown)


def test_llm_indisponible_interface_reste_utilisable(app, monkeypatch):
    at, _ = app

    def panne(*a, **k):
        raise TimeoutError("quota")
    monkeypatch.setattr(llm, "chat", panne)
    at.chat_input[0].set_value("Date ?").run()
    assert not at.exception
    assert any("indisponible" in m.value for m in at.markdown)


@pytest.mark.parametrize("valeur, attendu", [
    ("NON REMPLIE (ticket:ACC-303:statut = OUVERT)", "bad"),
    ("REMPLIE (ticket:SEC-210:statut = FERME)", "ok"),
    ("OUVERT", "bad"),
    ("FERME", "ok"),
    ("EN_VALIDATION", "warn"),
    ("OUI", "ok"),
    ("NON", "bad"),
    ("VERT", "ok"),
    ("ROUGE", "bad"),
])
def test_tone_des_badges(valeur, attendu):
    import app
    assert app.tone(valeur) == attendu
