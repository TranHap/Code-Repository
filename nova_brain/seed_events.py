"""Charge un registre d'événements curé à la main (ex. rendu/02_Memoire/evenements.csv) dans la table events.

    python -m nova_brain.seed_events [chemin.csv]

- Même fichier, même contenu : ignoré (pas de doublons si la commande est relancée).
- Même fichier, contenu modifié : nouveau lot de curation qui remplace le précédent (supersedes) ;
  l'ancien lot reste en mémoire pour l'historique.
- Chaque source est vérifiée contre les fichiers ingérés pour détecter les références cassées.
"""
import csv
import hashlib
import re
import sys
from pathlib import Path

from . import config, db
from .parsers import decode_text

DEFAULT = config.ROOT / "rendu" / "02_Memoire" / "evenements.csv"
REQUIRED = ["id", "date", "heure", "sujet", "type", "resume", "acteur", "source", "repere", "validite_au_30sept", "lien"]


def seed(path: Path, con=None) -> dict:
    con = con or db.connect()
    raw = path.read_bytes()
    h = hashlib.sha256(raw).hexdigest()
    if con.execute("SELECT 1 FROM batches WHERE kind='curation' AND source_sha=?", (h,)).fetchone():
        return {"batch_id": None, "count": 0, "missing": [], "skipped": True, "supersedes": None}

    # Fichier réenregistré par Excel FR : séparateur ";" et encodage Windows-1252.
    text = decode_text(raw)
    try:
        dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;\t")
    except (csv.Error, IndexError):
        dialect = csv.excel
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    cols = reader.fieldnames or []
    rows = [r for r in reader if (r.get("id") or "").strip()]   # lignes vides ";;;;" ignorées
    missing_cols = [c for c in REQUIRED if c not in cols]
    if missing_cols:
        raise ValueError(f"{path.name} : colonnes manquantes {missing_cols}")

    prev = con.execute("SELECT MAX(batch_id) FROM batches WHERE kind='curation' AND label=?", (path.name,)).fetchone()[0]
    files = {f["path"] for f in db.current_files(con)}
    names = {p.rsplit("/", 1)[-1] for p in files}
    batch = db.new_batch(con, "curation", path.name, source_sha=h, supersedes=prev)
    ts = db.now()
    missing = []
    for r in rows:
        src = (r["source"] or "").strip()
        # Une source peut citer plusieurs fichiers : "a.pdf + b.pdf" ou "a ; b"
        for part in re.split(r"\s*[+;]\s*", src):
            if part and part not in files and part.rsplit("/", 1)[-1] not in names:
                missing.append(f"{r['id']}: {part}")
        con.execute(
            """INSERT INTO events(ref, date_fait, heure, sujet, type, resume, acteur, source, repere, note, liens,
                                  origine, inserted_at, batch_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["id"], r["date"], r["heure"], r["sujet"], r["type"], r["resume"], r["acteur"], src, r["repere"],
             r["validite_au_30sept"], r["lien"], f"curation:{path.name}", ts, batch))
    con.commit()
    return {"batch_id": batch, "count": len(rows), "missing": missing, "skipped": False, "supersedes": prev}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    r = seed(path)
    if r["skipped"]:
        print(f"{path.name} déjà chargé avec ce contenu : rien à faire.")
        return
    print(f"Lot {r['batch_id']} : {r['count']} événements chargés depuis {path.name}"
          + (f" (remplace le lot {r['supersedes']})" if r["supersedes"] else ""))
    for m in r["missing"]:
        print("  source introuvable :", m)


if __name__ == "__main__":
    main()
