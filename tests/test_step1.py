"""Tests de robustesse de l'étape 1 (ingestion → mémoire).

Chaque test simule une situation réaliste d'utilisation, pas seulement le corpus fourni.
"""
import datetime as dt
import io
import unicodedata
import zipfile

import fitz
import openpyxl
import pytest
from openpyxl.comments import Comment

from conftest import evidence, files, make_email, write
from nova_brain import config, ingest as ing, seed_events
from nova_brain.dates import find_date
from nova_brain.parsers import parse, parse_lines


# ───────────────────────── A. Dates écrites en français ─────────────────────────

@pytest.mark.parametrize("txt, attendu", [
    ("Date : 7 juillet 2026", "2026-07-07"),
    ("le 1er octobre 2026", "2026-10-01"),
    ("COMITÉ PROJET NOVA - 27 AOÛT 2026", "2026-08-27"),
    ("Rencontre du 22/10/2026", "2026-10-22"),          # format numérique québécois jj/mm/aaaa
    ("créée le 2026-09-22", "2026-09-22"),
    ("Suivi au 9 septembre 2026", "2026-09-09"),
    ("17 sept. 2026", "2026-09-17"),
])
def test_dates_valides(txt, attendu):
    assert find_date(txt) == attendu


@pytest.mark.parametrize("txt", [
    "5 décisions importantes",            # "déc" ≠ décembre
    "3 maisons à visiter",                # "mai" ≠ mai
    "Transfert de 15 octets",             # "oct" ≠ octobre
    "le 31 septembre 2026",               # date impossible
    "14:02:10 np.admin LOGIN",            # heure, pas une date
    "Facture de 1450 $ émise",
    "12 avril-like 2026".replace("avril-like", "avrilles"),
])
def test_pas_de_fausse_date(txt):
    # année par défaut fournie, comme dans parse_lines : le piège est le mois, pas l'année
    assert find_date(txt, default_year=2026) is None


def test_commentaire_ticket_passage_annee():
    txt = "TICKET X\nCréé : 20 décembre 2026\n\nCommentaires :\n05 janv 09:41 - Marc : Toujours en panne."
    _, unites = parse_lines(txt)
    comm = [u for u in unites if u["unit"] == "commentaire"][0]
    assert comm["date_fait"] == "2027-01-05T09:41"


# ───────────────────────── B. Fichiers texte ─────────────────────────

def test_fichier_texte_windows_1252(tmp_path, con):
    write(tmp_path, "02_Reunions/CR.txt", "COMPTE RENDU NOVA\nDate : 7 juillet 2026\nDécision : approuvée".encode("cp1252"))
    ing.ingest(tmp_path, con=con)
    textes = " ".join(e["texte"] for e in evidence(con, "%CR.txt"))
    assert "Décision" in textes and "�" not in textes


def test_ligne_de_log_pas_un_tour_de_parole():
    _, unites = parse_lines("Journal NOVA\n10 septembre 2026\n14:02:10 np.admin LOGIN Portail SUCCÈS")
    assert all(u["unit"] != "tour" for u in unites)


def test_variantes_tours_de_parole():
    _, u = parse_lines("Canal NOVA\n19 septembre 2026\n10:24 - Julien (Boréal) : fix déployé\n15:23 [silence]\n09:12 Alex : ok")
    tours = [x for x in u if x["unit"] == "tour"]
    assert [t["auteur"] for t in tours] == ["Julien (Boréal)", None, "Alex"]
    assert tours[0]["date_fait"] == "2026-09-19T10:24"


def test_fichier_vide_enregistre_sans_planter(tmp_path, con):
    write(tmp_path, "vide.txt", b"")
    r = ing.ingest(tmp_path, con=con)
    assert "vide.txt" in files(con) and r["nouveau"] == ["vide.txt"]


# ───────────────────────── C. Courriels ─────────────────────────

def test_courriel_html_seulement(tmp_path, con):
    write(tmp_path, "E.eml", make_email(body=None, html="<html><body><p>Le comit&eacute; a <b>approuv&eacute;</b> le 22 octobre.</p></body></html>"))
    ing.ingest(tmp_path, con=con)
    t = evidence(con, "E.eml")[0]["texte"]
    assert "approuvé le 22 octobre" in t and "<b>" not in t


def test_courriel_sans_objet(tmp_path, con):
    write(tmp_path, "E.eml", make_email(subject=None))
    ing.ingest(tmp_path, con=con)
    assert files(con)["E.eml"]["title"] in ("", None)


def test_piece_jointe_sans_nom(tmp_path, con):
    write(tmp_path, "E.eml", make_email(attachments=[(None, b"%PDF-fake", "application", "octet-stream")]))
    r = ing.ingest(tmp_path, con=con)
    assert not any(p.endswith("::None") for p in files(con))
    assert not r["erreurs"]


def test_courriel_transfere_en_piece_jointe(tmp_path, con):
    from email import message_from_bytes, policy
    inner = message_from_bytes(make_email(subject="Décision originale", body="Le comité approuve.", msgid="<in@x>"),
                               policy=policy.default)
    write(tmp_path, "FW.eml", make_email(subject="TR: décision", msgid="<fw@x>", attachments=[(None, inner, "message", "rfc822")]))
    r = ing.ingest(tmp_path, con=con)
    assert not r["erreurs"]
    assert any("Le comité approuve." in e["texte"] for e in evidence(con, "FW.eml::%"))


def test_deux_pieces_jointes_meme_nom(tmp_path, con):
    write(tmp_path, "E.eml", make_email(attachments=[("note.txt", b"version A NOVA", "text", "plain"),
                                                     ("note.txt", b"version B NOVA", "text", "plain")]))
    r = ing.ingest(tmp_path, con=con)
    assert not r["erreurs"]
    assert len([p for p in files(con) if p.startswith("E.eml::")]) == 2


def test_piece_jointe_identique_sous_autre_nom(tmp_path, con):
    pdf = _pdf("FACTURE INV-003 NOVA")   # mêmes octets : le même fichier, renommé dans le courriel
    write(tmp_path, "05/INV-003.pdf", pdf)
    write(tmp_path, "E.eml", make_email(attachments=[("facture_scan.pdf", pdf, "application", "pdf")]))
    r = ing.ingest(tmp_path, con=con)
    assert any("05/INV-003.pdf" in x for x in r["pj_liee"])
    assert not any(p.startswith("E.eml::") for p in files(con))   # pas une seconde source


def test_piece_jointe_differente_du_fichier_separe(tmp_path, con):
    write(tmp_path, "05/INV-003.pdf", _pdf("TOTAL 54 000 $ NOVA"))
    write(tmp_path, "E.eml", make_email(attachments=[("INV-003.pdf", _pdf("TOTAL 36 000 $ NOVA"), "application", "pdf")]))
    r = ing.ingest(tmp_path, con=con)
    assert r["pj_differente"]
    assert "E.eml::INV-003.pdf" in files(con)


def test_meme_piece_jointe_dans_deux_courriels(tmp_path, con):
    pdf = _pdf("FACTURE INV-003 NOVA")
    write(tmp_path, "INV-003.pdf", pdf)
    write(tmp_path, "E07.eml", make_email(msgid="<a@x>", attachments=[("INV-003.pdf", pdf, "application", "pdf")]))
    write(tmp_path, "E13.eml", make_email(msgid="<b@x>", attachments=[("INV-003.pdf", pdf, "application", "pdf")]))
    ing.ingest(tmp_path, con=con)
    liens = con.execute("SELECT email_path FROM attachments WHERE file_path='INV-003.pdf'").fetchall()
    assert {l[0] for l in liens} == {"E07.eml", "E13.eml"}


def test_message_id_normalise(tmp_path, con):
    write(tmp_path, "01/E12.eml", make_email(msgid="<e12@nova.local>", body="Résolution NOVA"))
    write(tmp_path, "08_Archives/copie.eml", make_email(msgid="  <E12@nova.local> ", body="Résolution NOVA\n\n-- \nenvoyé depuis mobile"))
    r = ing.ingest(tmp_path, con=con)
    assert files(con)["08_Archives/copie.eml"]["duplicate_of"] == "01/E12.eml"


# ───────────────────────── D. Dossiers, téléversements, versions ─────────────────────────

def test_televersement_partiel(tmp_path, con):
    base = tmp_path / "v1"
    write(base, "01/E01.eml", make_email(msgid="<e01@x>"))
    write(base, "03/INT-101.txt", "TICKET INT-101 NOVA\nCréé : 5 septembre 2026")
    ing.ingest(base, con=con)
    up = tmp_path / "up"
    write(up, "01/E13.eml", make_email(msgid="<e13@x>", body="Nouvelle info NOVA"))
    write(up, "99/copie_ticket.txt", "TICKET INT-101 NOVA\nCréé : 5 septembre 2026")
    r = ing.ingest(up, kind="upload", partial=True, con=con)
    assert r["absent"] == []                                        # partiel : rien n'est « disparu »
    assert files(con)["99/copie_ticket.txt"]["duplicate_of"] == "03/INT-101.txt"   # doublon d'un ancien lot


def test_dossier_parent_enveloppant(tmp_path, con):
    write(tmp_path / "a", "01/E01.eml", make_email())
    ing.ingest(tmp_path / "a", con=con)
    write(tmp_path / "b" / "NOVA_ETUDIANTS" / "Projet360", "01/E01.eml", make_email())
    r = ing.ingest(tmp_path / "b", kind="upload", con=con)
    assert r["inchange"] == ["01/E01.eml"] and r["nouveau"] == []


def test_televersement_zip_mac(tmp_path, con):
    write(tmp_path / "a", "02_Réunions/M01.txt", "CR NOVA\nDate : 7 juillet 2026")
    ing.ingest(tmp_path / "a", con=con)
    z = tmp_path / "upload.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("Projet360/02_Réunions/M01.txt", "CR NOVA\nDate : 7 juillet 2026")
        zf.writestr("__MACOSX/Projet360/02_Réunions/._M01.txt", b"\x00\x05\x16\x07junk")
        zf.writestr("Projet360/.DS_Store", b"\x00\x00\x00\x01Bud1")
    r = ing.ingest(z, kind="upload", con=con)
    assert r["inchange"] == ["02_Réunions/M01.txt"] and r["nouveau"] == []


def test_noms_unicode_nfd(tmp_path, con):
    write(tmp_path / "a", "02_Réunions/M01.txt", "CR NOVA")
    ing.ingest(tmp_path / "a", con=con)
    write(tmp_path / "b", unicodedata.normalize("NFD", "02_Réunions/M01.txt"), "CR NOVA")
    r = ing.ingest(tmp_path / "b", kind="upload", con=con)
    assert r["inchange"] == ["02_Réunions/M01.txt"]


def test_fichiers_systeme_ignores(tmp_path, con):
    write(tmp_path, "04/Plan.xlsx", _xlsx([["ID", "Activité"], ["P-01", "Cadrage"]]))
    write(tmp_path, "04/~$Plan.xlsx", b"\x00lock")
    write(tmp_path, "04/Thumbs.db", b"\x00")
    write(tmp_path, "04/desktop.ini", "[.ShellClassInfo]")
    write(tmp_path, "04/.~lock.Plan.xlsx#", "lock")
    ing.ingest(tmp_path, con=con)
    assert set(files(con)) == {"04/Plan.xlsx"}


def test_fichiers_corrompus_ne_bloquent_pas(tmp_path, con):
    write(tmp_path, "a.pdf", b"%PDF-1.4 tronque")
    write(tmp_path, "b.xlsx", b"PK\x03\x04 pas un vrai classeur")
    write(tmp_path, "c.txt", "ligne NOVA valide")
    r = ing.ingest(tmp_path, con=con)
    assert len(r["erreurs"]) == 2
    assert files(con)["a.pdf"]["status"] == "erreur"
    assert evidence(con, "c.txt")


def test_format_non_supporte_pas_de_charabia(tmp_path, con):
    write(tmp_path, "x.msg", bytes(range(256)) * 4)
    write(tmp_path, "y.pptx", b"PK\x03\x04" + bytes(range(200)))
    r = ing.ingest(tmp_path, con=con)
    assert files(con)["x.msg"]["status"] == "non_supporte"
    assert evidence(con, "x.msg") == [] and evidence(con, "y.pptx") == []


def test_docx(tmp_path, con):
    import docx
    d = docx.Document()
    d.add_paragraph("Compte rendu NOVA")
    d.add_paragraph("Le comité approuve le 22 octobre 2026.")
    buf = io.BytesIO(); d.save(buf)
    write(tmp_path, "CR.docx", buf.getvalue())
    ing.ingest(tmp_path, con=con)
    assert any("approuve le 22 octobre" in e["texte"] for e in evidence(con, "CR.docx"))


def test_version_modifiee_puis_revenue(tmp_path, con):
    for contenu in ("v1 NOVA", "v2 NOVA", "v1 NOVA", "v2 NOVA"):
        write(tmp_path, "plan.txt", contenu)
        ing.ingest(tmp_path, kind="upload", con=con)
    n = con.execute("SELECT COUNT(*) FROM files WHERE path='plan.txt'").fetchone()[0]
    assert n == 4 and files(con)["plan.txt"]["sha256"] == ing.sha(b"v2 NOVA")


def test_fichier_deplace(tmp_path, con):
    write(tmp_path / "a", "04/Note.txt", "Note NOVA unique")
    ing.ingest(tmp_path / "a", con=con)
    write(tmp_path / "b", "archives/Note_renommee.txt", "Note NOVA unique")
    r = ing.ingest(tmp_path / "b", kind="upload", con=con)
    assert r["deplace"] == ["04/Note.txt → archives/Note_renommee.txt"]


# ───────────────────────── E. Tableurs ─────────────────────────

def test_entete_pas_en_ligne_1_et_dates(tmp_path):
    raw = _xlsx([["REGISTRE DES RISQUES NOVA"], [], ["ID", "Statut", "Échéance"],
                 ["R-01", "Ouvert", dt.datetime(2026, 10, 22)]])
    _, u = parse("r.xlsx", raw)
    assert len(u) == 2   # titre + R-01, l'en-tête n'est pas une donnée
    r01 = [x for x in u if "R-01" in x["texte"]][0]
    assert "Statut [B4]: Ouvert" in r01["texte"] and "2026-10-22" in r01["texte"] and "00:00:00" not in r01["texte"]


def test_formule_sans_valeur_en_cache(tmp_path):
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["Poste", "Montant"]); ws.append(["Base", 156000]); ws.append(["CR-01", 24000]); ws.append(["Total", "=B2+B3"])
    buf = io.BytesIO(); wb.save(buf)
    _, u = parse("budget.xlsx", buf.getvalue())
    assert any("=B2+B3" in x["texte"] for x in u)


def test_commentaire_sur_cellule_vide_et_feuilles_multiples(tmp_path):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Plan"
    ws.append(["ID", "Note"]); ws.append(["P-06", None])
    ws["B2"].comment = Comment("Date non mise à jour depuis le comité du 10 sept.", "Nicolas")
    wb.create_sheet("Vide")
    ws2 = wb.create_sheet("Risques"); ws2.append(["ID"]); ws2.append(["R-01"])
    buf = io.BytesIO(); wb.save(buf)
    _, u = parse("p.xlsx", buf.getvalue())
    assert any("Date non mise à jour" in x["texte"] for x in u)
    assert any(x["repere"].startswith("Risques!") for x in u)


# ───────────────────────── F/G. PDF scanné, CSV ─────────────────────────

def test_pdf_scanne_sans_texte_passe_par_la_vision(tmp_path):
    doc = fitz.open(); page = doc.new_page()
    page.draw_rect(fitz.Rect(50, 50, 200, 200), color=(0, 0, 0), fill=(0.5, 0.5, 0.5))
    appels = []
    _, u = parse("scan.pdf", doc.tobytes(), transcrire=lambda b: appels.append(b) or "FACTURE NOVA 54 000 $")
    assert appels and "54 000" in u[0]["texte"]


def test_csv_point_virgule():
    _, u = parse("export.csv", "ID;Statut;Montant\nINV-003;En validation;54 000\n".encode("utf-8"))
    assert u[0]["texte"].startswith("ID: INV-003 | Statut: En validation")


# ───────────────────────── H. Vision ─────────────────────────

def test_capture_retentee_apres_echec(tmp_path, con):
    write(tmp_path, "runbook.png", b"\x89PNG fake")
    ing.ingest(tmp_path, con=con, transcrire=lambda b: "[capture non transcrite]")
    r = ing.ingest(tmp_path, kind="upload", con=con, transcrire=lambda b: "4. Retour arrière TODO")
    assert files(con)["runbook.png"]["status"] == "ok"
    assert "TODO" in evidence(con, "runbook.png")[-1]["texte"]


# ───────────────────────── I. Événements curés ─────────────────────────

CSV_HDR = "id,date,heure,sujet,type,resume,acteur,source,repere,validite_au_30sept,lien\n"


def test_seed_idempotent_et_nouvelle_version(tmp_path, con):
    p = write(tmp_path, "ev.csv", CSV_HDR + "EV001,2026-09-10,,Échéancier,DECISION,Date 22 oct,Comité,x.txt,l1,actuel,\n")
    seed_events.seed(p, con=con)
    r2 = seed_events.seed(p, con=con)
    assert r2["skipped"] and con.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    write(tmp_path, "ev.csv", CSV_HDR + "EV001,2026-09-10,,Échéancier,DECISION,Date 22 oct (cond.),Comité,x.txt,l1,actuel,\n")
    r3 = seed_events.seed(p, con=con)
    assert r3["supersedes"] == 1 or r3["supersedes"] is not None


def test_seed_colonnes_manquantes(tmp_path, con):
    p = write(tmp_path, "ev.csv", "id;date;resume\nEV1;2026-09-10;x\n")
    with pytest.raises(ValueError, match="colonnes"):
        seed_events.seed(p, con=con)


# ───────────────────────── J. Régression sur le vrai corpus ─────────────────────────

@pytest.mark.skipif(not config.CORPUS_DEFAULT.exists(), reason="corpus absent")
def test_corpus_reel(con):
    cache = __import__("json").loads(config.VISION_CACHE.read_text(encoding="utf-8")) if config.VISION_CACHE.exists() else {}
    r = ing.ingest(config.CORPUS_DEFAULT, con=con, transcrire=lambda b: cache.get(ing.sha(b), "[capture non transcrite]"))
    f = files(con)
    assert len(r["nouveau"]) == 62 and not r["erreurs"]
    assert f["08_Archives_et_documents_connexes/Courriel_archive_17sept.eml"]["duplicate_of"] == "01_Courriels/E12_Resolution_integration.eml"
    assert len(r["pj_liee"]) == 5
    assert f["08_Archives_et_documents_connexes/INV-778_Projet_ORION.pdf"]["source_class"] == "hors_projet_probable"
    assert f["08_Archives_et_documents_connexes/Notes_personnelles_quelquun.txt"]["source_class"] == "non_officiel"
    assert sum(1 for x in f.values() if x["source_class"] == "officiel") == 56
    m04 = {e["repere"]: e for e in evidence(con, "%M04_%")}
    assert m04["15:22 (ligne 17)"]["auteur"] == "Élodie" and "22 octobre 2026" in m04["15:22 (ligne 17)"]["texte"]
    int101 = [e for e in evidence(con, "%INT-101.txt") if e["unit"] == "commentaire"]
    assert ("2026-09-17T16:10", "Marc") in {(e["date_fait"], e["auteur"]) for e in int101}
    r01 = [e for e in evidence(con, "%Registre%") if "R-01" in e["texte"]][0]
    assert r01["repere"] == "Risques!A2:H2" and "Suivi au 9 septembre 2026" in r01["texte"]


# ───────────────────────── utilitaires ─────────────────────────

def _pdf(text: str) -> bytes:
    doc = fitz.open(); doc.new_page().insert_text((72, 72), text)
    return doc.tobytes()


def _xlsx(rows) -> bytes:
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Feuil1"
    for r in rows:
        ws.append(r)
    buf = io.BytesIO(); wb.save(buf)
    return buf.getvalue()


# ───────────────────────── K. Deuxième série : usages réels plus tordus ─────────────────────────

def test_csv_evenements_resauve_par_excel_fr(tmp_path, con):
    """Excel FR enregistre le CSV avec ';', en Windows-1252, et ajoute des lignes vides ';;;;'."""
    txt = CSV_HDR.replace(",", ";") + "EV001;2026-09-10;;Échéancier;DÉCISION;Report au 22 octobre;Comité;x.txt;15:22;actuel;\n" + ";" * 10 + "\n"
    p = write(tmp_path, "evenements.csv", txt.encode("cp1252"))
    r = seed_events.seed(p, con=con)
    assert r["count"] == 1
    ev = con.execute("SELECT * FROM events").fetchone()
    assert ev["sujet"] == "Échéancier" and ev["type"] == "DÉCISION"


def test_tour_sur_plusieurs_lignes():
    txt = ("TRANSCRIPTION NOVA\n10 septembre 2026\n15:22 Élodie : Je vais formuler la décision.\n"
           "La date est déplacée au 22 octobre.\n\nNote de la secrétaire : fin de la séance.")
    _, u = parse_lines(txt)
    tour = [x for x in u if x["unit"] == "tour"][0]
    assert "déplacée au 22 octobre" in tour["texte"] and tour["repere"] == "15:22 (lignes 3-4)"
    assert any(x["texte"].startswith("Note de la secrétaire") and x["unit"] == "ligne" for x in u)   # ligne vide : fin du tour


def test_teams_sur_plusieurs_jours():
    txt = "Canal : NOVA\n15 septembre 2026\n09:12 - Alex : bonjour\n16 septembre 2026\n08:40 - Nicolas : je reprends le projet"
    _, u = parse_lines(txt)
    tours = {x["auteur"]: x["date_fait"] for x in u if x["unit"] == "tour"}
    assert tours == {"Alex": "2026-09-15T09:12", "Nicolas": "2026-09-16T08:40"}


def test_date_courriel_en_francais(tmp_path, con):
    # EmailMessage refuse une date non RFC : on l'écrit à la main, comme dans un vrai .eml exporté
    raw = make_email(date=None).replace(b"To: ", b"Date: mar., 8 sept. 2026 11:16\nTo: ", 1)
    write(tmp_path, "E.eml", raw)
    ing.ingest(tmp_path, con=con)
    assert evidence(con, "E.eml")[0]["date_fait"].startswith("2026-09-08")


def test_extensions_en_majuscules(tmp_path, con):
    write(tmp_path, "INV-003.PDF", _pdf("FACTURE NOVA"))
    write(tmp_path, "E05.EML", make_email(body="Proposition NOVA"))
    r = ing.ingest(tmp_path, con=con)
    assert not r["erreurs"] and not r["non_supporte"]
    assert evidence(con, "INV-003.PDF") and evidence(con, "E05.EML")[0]["unit"] == "courriel"


def test_fichier_trop_gros(tmp_path, con, monkeypatch):
    monkeypatch.setattr(ing, "MAX_SIZE", 100)
    write(tmp_path, "video.mp4", b"\x00" * 1000)
    write(tmp_path, "ok.txt", "petit NOVA")
    r = ing.ingest(tmp_path, con=con)
    assert files(con)["video.mp4"]["status"] == "non_supporte" and evidence(con, "ok.txt")


def test_meme_fichier_deux_fois_dans_le_lot(tmp_path, con):
    write(tmp_path, "04/Note.txt", "Note NOVA")
    write(tmp_path, "04/Note - Copie.txt", "Note NOVA")
    ing.ingest(tmp_path, con=con)
    assert files(con)["04/Note.txt"]["duplicate_of"] is None
    assert files(con)["04/Note - Copie.txt"]["duplicate_of"] == "04/Note.txt"


def test_echec_en_cours_de_lot_annule_tout(tmp_path, con, monkeypatch):
    """Une erreur inattendue (ex. disque plein) ne doit pas laisser un lot à moitié écrit."""
    write(tmp_path, "a.txt", "NOVA a")
    write(tmp_path, "E.eml", make_email(attachments=[("x.txt", b"NOVA x", "text", "plain")]))
    con.execute("CREATE TRIGGER boom BEFORE INSERT ON attachments BEGIN SELECT RAISE(ABORT, 'disque plein'); END")
    with pytest.raises(Exception, match="disque plein"):
        ing.ingest(tmp_path, con=con)
    con.execute("DROP TRIGGER boom")
    con.commit()   # une interface qui garde la connexion ouverte et valide plus tard
    assert con.execute("SELECT COUNT(*) FROM files").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM batches").fetchone()[0] == 0


def test_meme_zip_televerse_deux_fois(tmp_path, con):
    z = tmp_path / "nova.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("Projet/01/E13.eml", make_email(msgid="<e13@x>"))
    ing.ingest(z, con=con)
    r = ing.ingest(z, kind="upload", con=con)
    assert r["inchange"] == ["01/E13.eml"] or r["inchange"] == ["Projet/01/E13.eml"]
    assert r["nouveau"] == []


def test_seed_avant_ingestion(tmp_path, con):
    p = write(tmp_path, "ev.csv", CSV_HDR + "EV001,2026-09-10,,Échéancier,DECISION,x,Comité,02/M04.txt,15:22,actuel,\n")
    r = seed_events.seed(p, con=con)
    assert r["missing"] == ["EV001: 02/M04.txt"]


def test_commentaire_ticket_sans_heure():
    txt = "TICKET ACC-301\nCréé : 11 août 2026\n\nCommentaires :\n15 août - Mélissa : Validé avec NVDA. Fermé.\n25 sept - Olivier : Il manque le rollback."
    _, u = parse_lines(txt)
    comms = [(x["auteur"], x["date_fait"]) for x in u if x["unit"] == "commentaire"]
    assert comms == [("Mélissa", "2026-08-15"), ("Olivier", "2026-09-25")]


def test_ligne_ordinaire_avec_tiret_pas_un_commentaire():
    # "12 tests - résultat : OK" ne doit pas devenir un commentaire de "résultat"
    _, u = parse_lines("CR NOVA\n7 juillet 2026\n12 tests - résultat : OK")
    assert all(x["unit"] != "commentaire" for x in u)


@pytest.mark.parametrize("ligne, jour", [
    ("16 septembre 2026", "2026-09-16"),
    ("Date : 7 juillet 2026", "2026-07-07"),
    ("Mardi 16 septembre 2026", "2026-09-16"),
    ("10 septembre 2026 - 15:00 à 15:42", "2026-09-10"),
    ("Décision : 15 octobre", None),            # contenu, pas un en-tête de jour
    ("Cible : 22 octobre 2026", None),
    ("Le 22 octobre reste la cible", None),
])
def test_entete_de_jour(ligne, jour):
    from nova_brain.dates import entete_de_jour
    assert entete_de_jour(ligne, 2026) == jour
