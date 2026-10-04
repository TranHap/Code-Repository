"""Ajout d'assertions dans la mémoire, avec validation (vocabulaire, statut, preuve).

Point d'entrée unique pour toutes les origines : curation CSV, mise à jour par chat, extraction LLM.

    python -m nova_brain.assertions [rendu/02_Memoire/assertions.csv]

Fichier CSV (séparateur , ou ;) : ref, cle, valeur, statut, acteur, autorite, date_fait, source, ancre, lien, note
- source + ancre désignent la preuve : ancre = suffixe de l'unité (L17, msg, p1, "Risques!2", capture).
- date_fait vide : reprise de la date de la preuve.
- Tout le fichier est validé avant d'écrire quoi que ce soit.
"""
import csv
import hashlib
import sys
from pathlib import Path

from . import config, db
from .parsers import decode_text
from .vocab import STATUTS, VocabError, normaliser_valeur, verifier_statut

DEFAULT = config.ROOT / "rendu" / "02_Memoire" / "assertions.csv"
COLONNES = ["ref", "cle", "valeur", "statut", "acteur", "autorite", "date_fait", "source", "ancre", "lien", "note"]
AUTORITES_FORCEES = {"comite", "reflet", "non_officiel"}


class AssertionInvalide(ValueError):
    pass


def preparer(con, row: dict) -> dict:
    """Valide une assertion et complète preuve, date et autorité. Lève AssertionInvalide."""
    ref = row.get("ref") or "?"
    try:
        cle = (row.get("cle") or "").strip()
        valeur = normaliser_valeur(cle, row.get("valeur", ""))
    except VocabError as e:
        raise AssertionInvalide(f"{ref} : {e}")
    statut = (row.get("statut") or "").strip().upper()
    if statut not in STATUTS:
        raise AssertionInvalide(f"{ref} : statut « {statut} » hors de {sorted(STATUTS)}")
    try:
        verifier_statut(cle, statut)
    except VocabError as e:
        raise AssertionInvalide(f"{ref} : {e}")
    autorite = (row.get("autorite") or "").strip() or None
    if autorite and autorite not in AUTORITES_FORCEES:
        raise AssertionInvalide(f"{ref} : autorite forcée « {autorite} » hors de {sorted(AUTORITES_FORCEES)}")
    lien = (row.get("lien") or "").strip() or None

    ev_id, date_fait, source = None, (row.get("date_fait") or "").strip() or None, (row.get("source") or "").strip() or None
    if source:
        f = con.execute("""SELECT * FROM files WHERE path=? ORDER BY file_id DESC LIMIT 1""", (source,)).fetchone()
        if f is None:
            raise AssertionInvalide(f"{ref} : source introuvable « {source} »")
        ancre = (row.get("ancre") or "").strip()
        ev = con.execute("SELECT * FROM evidence WHERE file_id=? AND ev_id LIKE ?",
                         (f["file_id"], f"%#{ancre}")).fetchone() if ancre else None
        if ancre and ev is None:
            raise AssertionInvalide(f"{ref} : ancre « {ancre} » introuvable dans {source}")
        ev_id = ev["ev_id"] if ev else None
        # date_fait vide : NON copiée ici ; le résolveur la lit sur la version courante de la preuve
        # (ainsi une correction du parseur ou une nouvelle version du fichier est prise en compte).
        if not autorite and f["source_class"] in ("non_officiel", "hors_projet_probable"):
            autorite = "non_officiel"
    if date_fait and not date_fait[:4].isdigit():
        raise AssertionInvalide(f"{ref} : date_fait « {date_fait} » invalide (attendu AAAA-MM-JJ)")
    if statut == "REFLET" and not autorite:
        autorite = "reflet"
    return {"ref": ref, "cle": cle, "valeur": valeur, "statut": statut, "acteur": (row.get("acteur") or "").strip() or None,
            "autorite": autorite, "date_fait": date_fait, "lien": lien, "ev_id": ev_id, "source": source,
            "ancre": (row.get("ancre") or "").strip() or None, "note": (row.get("note") or "").strip() or None}


def inserer(con, a: dict, origine: str, batch: int) -> int:
    cur = con.execute(
        """INSERT INTO assertions(ref, cle, valeur, statut, acteur, autorite, date_fait, lien, ev_id, source, ancre,
                                  note, origine, inserted_at, batch_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (a["ref"], a["cle"], a["valeur"], a["statut"], a["acteur"], a["autorite"], a["date_fait"], a["lien"],
         a["ev_id"], a["source"], a.get("ancre"), a["note"], origine, db.now(), batch))
    return cur.lastrowid


def charger_csv(path: Path, con=None, kind: str = "curation") -> dict:
    """kind : curation (saisie manuelle) ou extraction (propositions LLM relues). Colonne optionnelle
    « garder » : les lignes marquées non / n / 0 sont ignorées."""
    con = con or db.connect()
    raw = path.read_bytes()
    h = hashlib.sha256(raw).hexdigest()
    if con.execute("SELECT 1 FROM batches WHERE kind=? AND source_sha=?", (kind, h)).fetchone():
        return {"skipped": True, "count": 0, "batch_id": None, "supersedes": None}
    text = decode_text(raw)
    try:
        dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;\t")
    except (csv.Error, IndexError):
        dialect = csv.excel
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    manquantes = [c for c in COLONNES if c not in (reader.fieldnames or [])]
    if manquantes:
        raise AssertionInvalide(f"{path.name} : colonnes manquantes {manquantes}")
    rows = [r for r in reader if (r.get("cle") or "").strip() and not (r.get("ref") or "").startswith("#")
            and (r.get("garder") or "oui").strip().lower() not in ("non", "n", "no", "0", "false")]

    prepared, erreurs = [], []
    for i, r in enumerate(rows, start=2):
        try:
            prepared.append(preparer(con, r))
        except AssertionInvalide as e:
            erreurs.append(f"ligne {i} : {e}")
    if erreurs:
        raise AssertionInvalide(f"{path.name} : {len(erreurs)} assertion(s) invalide(s), rien n'est chargé\n  "
                                + "\n  ".join(erreurs))

    prev = con.execute("SELECT MAX(batch_id) FROM batches WHERE kind=? AND label=?", (kind, path.name)).fetchone()[0]
    batch = db.new_batch(con, kind, path.name, source_sha=h, supersedes=prev)
    for a in prepared:
        inserer(con, a, f"{kind}:{path.name}", batch)
    con.commit()
    return {"skipped": False, "count": len(prepared), "batch_id": batch, "supersedes": prev}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    try:
        r = charger_csv(path)
    except AssertionInvalide as e:
        print(e)
        sys.exit(1)
    if r["skipped"]:
        print(f"{path.name} déjà chargé avec ce contenu : rien à faire.")
    else:
        print(f"Lot {r['batch_id']} : {r['count']} assertions chargées"
              + (f" (remplace le lot {r['supersedes']})" if r["supersedes"] else ""))


if __name__ == "__main__":
    main()
