"""Ingestion d'un dossier (ou d'un .zip) de projet dans la mémoire, initiale ou incrémentale.

    python -m nova_brain.ingest [dossier|archive.zip] [--kind upload] [--partial] [--label "..."] [--no-vision]

- Fichier déjà connu avec le même contenu : ignoré (sauf capture restée non transcrite : retentée).
- Fichier connu au contenu différent : nouvelle version (l'ancienne reste en mémoire).
- Fichier déplacé/renommé (même contenu, autre chemin) : signalé comme déplacé.
- Pièce jointe identique à un fichier connu (même contenu, quel que soit le nom) : liée au courriel,
  pas comptée comme source indépendante. Sinon : ingérée comme fichier propre "courriel::nom".
- Doublons (même Message-ID ou même contenu, y compris avec un lot précédent) : marqués duplicate_of.
- --partial : le dossier ne contient que des nouveautés ; aucun fichier n'est signalé « absent ».
- Un fichier illisible ou d'un format inconnu est enregistré avec son statut, sans bloquer le lot.
"""
import argparse
import hashlib
import json
import re
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path

from . import config, db, llm
from .parsers import PARSER_VERSION, PLACEHOLDER, VISION_PROMPT, NonSupporte, parse

SKIP_NAMES = {"MANIFEST.csv", "README.txt", ".DS_Store", "Thumbs.db", "desktop.ini"}
SKIP_DIRS = {"__MACOSX", ".git", "__pycache__"}
MAX_SIZE = 50 * 1024 * 1024   # au-delà (vidéo, export massif) : enregistré comme non supporté, non lu
RE_COPIE = re.compile(r"(copie|copy|\(\d+\))", re.I)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def is_junk(rel_parts) -> bool:
    name = rel_parts[-1]
    return (name in SKIP_NAMES or name.startswith(("~$", ".~lock", "._", "."))
            or any(p in SKIP_DIRS for p in rel_parts[:-1]))


def make_transcriber(enabled: bool):
    if not enabled or not config.LLM_API_KEY:
        return None
    cache = json.loads(config.VISION_CACHE.read_text(encoding="utf-8")) if config.VISION_CACHE.exists() else {}

    def transcrire(raw: bytes) -> str:
        key = sha(raw)
        if key not in cache:
            print("    … transcription vision", flush=True)
            try:
                cache[key] = llm.vision(raw, VISION_PROMPT)
            except Exception as e:  # l'échec n'est pas mis en cache : statut "incomplet", retenté au prochain lot
                print(f"    ! vision indisponible ({type(e).__name__}) : capture à transcrire plus tard", flush=True)
                return PLACEHOLDER
            config.DATA.mkdir(parents=True, exist_ok=True)
            config.VISION_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        return cache[key]
    return transcrire


PROJET = "NOVA"
# Nom de projet en capitales, sur la même ligne : "Projet ORION", "Projet : ORION"
RE_AUTRE_PROJET = re.compile(r"\b[Pp]rojet[ \t]*:?[ \t]+([A-Z][A-Z0-9]{2,})\b")


def classify(path: str, unites: list) -> str:
    """Règles simples de fiabilité de la source ; à revoir par une personne."""
    texte = "\n".join(u["texte"] for u in unites)
    autres = {m.upper() for m in RE_AUTRE_PROJET.findall(texte + " " + path.replace("_", " "))} - {PROJET}
    if autres and PROJET.lower() not in texte.lower():
        return "hors_projet_probable"
    if "non officiel" in texte.lower() or "auteur non identifié" in texte.lower():
        return "non_officiel"
    if path.split("/")[0].startswith("08_"):
        return "archive"
    return "officiel"


# ───────────────────────── Localisation des fichiers ─────────────────────────

def _extract_zip(z: Path, dest: Path) -> Path:
    with zipfile.ZipFile(z) as zf:
        for info in zf.infolist():
            name = info.filename
            if not info.flag_bits & 0x800:   # nom non UTF-8 : souvent du cp437 mal décodé (accents)
                try:
                    name = name.encode("cp437").decode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
            target = (dest / name).resolve()
            if not str(target).startswith(str(dest.resolve())):   # zip-slip : chemin hors du dossier
                continue
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(info))
    return dest


def _listing(root: Path):
    out = []
    for p in root.rglob("*"):
        if p.is_file():
            parts = p.relative_to(root).parts
            if not is_junk(parts):
                out.append((unicodedata.normalize("NFC", "/".join(parts)), p))
    return out


def _wrapper_chain(folder: Path):
    """Le dossier, puis chaque sous-dossier unique qui l'enveloppe (ex. NOVA_ETUDIANTS/Projet360/)."""
    chain = [folder]
    while True:
        entries = [e for e in chain[-1].iterdir() if not is_junk((e.name,)) and e.name not in SKIP_DIRS]
        if len(entries) == 1 and entries[0].is_dir():
            chain.append(entries[0])
        else:
            return chain


def choose_root(folder: Path, known: dict) -> Path:
    """Racine qui fait correspondre le plus de chemins aux fichiers déjà connus (sinon le dossier donné)."""
    chain = _wrapper_chain(folder)
    if not known:
        return folder
    scores = [(sum(rel in known for rel, _ in _listing(c)), -i, c) for i, c in enumerate(chain)]
    best = max(scores, key=lambda s: (s[0], s[1]))
    return best[2] if best[0] > 0 else folder


# ───────────────────────── Ingestion ─────────────────────────

def ingest(folder: Path, label: str = "", kind: str = "corpus", transcrire=None, partial: bool = False,
           con=None) -> dict:
    folder = Path(folder)
    if folder.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory() as tmp:
            return ingest(_extract_zip(folder, Path(tmp)), label or folder.name, kind, transcrire, partial, con)

    con = con or db.connect()
    try:
        return _ingest(con, folder, label, kind, transcrire, partial)
    except BaseException:
        con.rollback()   # jamais de lot à moitié écrit, même si l'appelant valide plus tard
        raise


def _ingest(con, folder, label, kind, transcrire, partial) -> dict:
    known = {f["path"]: f for f in db.current_files(con)}
    root = choose_root(folder, known)
    batch = db.new_batch(con, kind, label or str(folder))
    report = {k: [] for k in ("nouveau", "modifie", "reparse", "inchange", "absent", "deplace", "doublon",
                              "pj_liee", "pj_differente", "erreurs", "non_supporte")}
    report["root"] = str(root)

    # Index des contenus et Message-ID déjà en mémoire : un doublon peut viser un lot précédent.
    seen_sha, seen_msgid = {}, {}
    for f in known.values():
        if not f["duplicate_of"]:
            seen_sha.setdefault(f["sha256"], f["path"])
            if f["message_id"]:
                seen_msgid.setdefault(f["message_id"], f["path"])

    # Ordre de traitement = qui est "l'original" en cas de doublon : hors archives d'abord,
    # puis les noms qui ne ressemblent pas à une copie ("Note - Copie.txt", "Note (1).txt").
    listing = sorted(_listing(root), key=lambda x: (x[0].split("/")[0].startswith("08_"),
                                                    bool(RE_COPIE.search(x[0].rsplit("/", 1)[-1])), x[0]))
    present = {rel for rel, _ in listing}
    new_paths = {}   # sha → chemin, pour détecter les déplacements

    def store(path: str, raw: bytes):
        h = sha(raw)
        prev = known.get(path)
        if prev and prev["sha256"] == h and prev["status"] != "incomplet" and prev["parser_version"] == PARSER_VERSION:
            report["inchange"].append(path)
            return None
        change = "reparse" if prev and prev["sha256"] == h else "modifie" if prev else "nouveau"
        print(f"  [{change}] {path}", flush=True)
        status, error, meta, unites = "ok", None, {}, []
        try:
            meta, unites = parse(path, raw, transcrire)
            status = "incomplet" if meta.get("incomplet") else "ok"
        except NonSupporte as e:
            status, error = "non_supporte", str(e)
            report["non_supporte"].append(path)
        except Exception as e:
            status, error = "erreur", f"{type(e).__name__}: {e}"
            report["erreurs"].append(f"{path} : {error}")
        dup = prev["duplicate_of"] if change == "reparse" else None
        if change != "reparse":
            dup = seen_sha.get(h) or (seen_msgid.get(meta.get("message_id")) if meta.get("message_id") else None)
            if dup == path:
                dup = None
            if dup:
                report["doublon"].append(f"{path} = {dup}")
        seen_sha.setdefault(h, path)
        if meta.get("message_id"):
            seen_msgid.setdefault(meta["message_id"], path)
        cur = con.execute(
            """INSERT INTO files(path, sha256, ext, size, doc_date, title, message_id, duplicate_of, source_class,
                                 change, status, error, parser_version, batch_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (path, h, path.rsplit(".", 1)[-1].lower() if "." in path else "", len(raw), meta.get("doc_date"),
             meta.get("title"), meta.get("message_id"), dup, classify(path, unites), change, status, error,
             PARSER_VERSION, batch))
        fid = cur.lastrowid
        tag = f"@v{fid}" if prev else ""
        con.executemany(
            "INSERT INTO evidence(ev_id, file_id, unit, repere, date_fait, auteur, texte, batch_id) VALUES (?,?,?,?,?,?,?,?)",
            [(f"{path}{tag}#{u['suffix']}", fid, u["unit"], u["repere"], u["date_fait"], u["auteur"], u["texte"], batch)
             for u in unites])
        report[change].append(path)
        if change == "nouveau":
            new_paths.setdefault(h, path)
        return meta

    pending = []   # (courriel, pièces jointes) à traiter après tous les fichiers séparés
    for rel, p in listing:
        if p.stat().st_size > MAX_SIZE:
            con.execute("""INSERT INTO files(path, sha256, ext, size, source_class, change, status, error, batch_id)
                           VALUES (?,?,?,?,?,?,?,?,?)""",
                        (rel, f"taille:{p.stat().st_size}", p.suffix.lower().lstrip("."), p.stat().st_size,
                         "officiel", "nouveau", "non_supporte", f"fichier > {MAX_SIZE} octets", batch))
            report["non_supporte"].append(rel)
            continue
        meta = store(rel, p.read_bytes())
        if meta and meta.get("attachments"):
            pending.append((rel, meta["attachments"]))

    # Fichiers séparés connus, par contenu et par nom (après ce lot).
    separate = {f["sha256"]: f["path"] for f in db.current_files(con) if "::" not in f["path"]}
    by_name = {}
    for path in list(present) + [k for k in known if "::" not in k]:
        by_name.setdefault(path.rsplit("/", 1)[-1], set()).add(path)

    while pending:   # file d'attente : un message transféré peut lui-même contenir des pièces jointes
        eml_path, pjs = pending.pop(0)
        for name, payload in pjs:
            h = sha(payload)
            if h in separate:
                target = separate[h]
                report["pj_liee"].append(f"{name} ⊂ {eml_path} = {target}")
            else:
                target = f"{eml_path}::{name}"
                if by_name.get(name):
                    report["pj_differente"].append(f"{name} dans {eml_path} ≠ {sorted(by_name[name])}")
                meta = store(target, payload)
                if meta and meta.get("attachments"):
                    pending.append((target, meta["attachments"]))
            con.execute("INSERT INTO attachments(email_path, name, file_path, sha256, batch_id) VALUES (?,?,?,?,?)",
                        (eml_path, name, target, h, batch))

    if not partial:
        absent = [k for k in known if "::" not in k and k not in present]
        for old in absent:
            new = new_paths.get(known[old]["sha256"])
            if new:
                report["deplace"].append(f"{old} → {new}")
                con.execute("UPDATE files SET change='deplace', duplicate_of=NULL WHERE path=? AND batch_id=?", (new, batch))
                report["doublon"] = [d for d in report["doublon"] if not d.startswith(f"{new} =")]
            else:
                report["absent"].append(old)
    con.commit()
    report["batch_id"] = batch
    return report


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="?", default=str(config.CORPUS_DEFAULT))
    ap.add_argument("--label", default="")
    ap.add_argument("--kind", default="corpus", choices=["corpus", "upload"])
    ap.add_argument("--partial", action="store_true", help="le dossier ne contient que des nouveautés")
    ap.add_argument("--no-vision", action="store_true")
    a = ap.parse_args()
    r = ingest(Path(a.folder), a.label, a.kind, make_transcriber(not a.no_vision), a.partial)
    print(f"\nLot {r['batch_id']} (racine : {r['root']}) :")
    for k in ("nouveau", "modifie", "reparse", "inchange", "absent"):
        print(f"  {k:10s} {len(r[k])}")
    for k in ("deplace", "doublon", "pj_liee", "pj_differente", "erreurs", "non_supporte"):
        for x in r[k]:
            print(f"  {k}: {x}")
    if r["absent"]:
        print("  absents (conservés en mémoire, non supprimés) :", *r["absent"], sep="\n    ")


if __name__ == "__main__":
    main()
