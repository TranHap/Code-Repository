"""Construit l'archive de remise, puis la vérifie dans un dossier vierge.

    python emballer_rendu.py               # avec le corpus NOVA_ETUDIANTS/
    python emballer_rendu.py --sans-corpus

Liste blanche : seuls les chemins de INCLURE entrent dans l'archive. Le .env (clé d'API), les bases de démo,
les imports d'essai et les caches n'y entrent jamais. La base memory.db est copiée par l'API de sauvegarde
SQLite, ce qui donne un instantané cohérent même si l'application est ouverte.
"""
import argparse
import os
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INCLURE = ["app.py", "requirements.txt", ".env.example", ".streamlit", "nova_brain", "rendu", "tests"]
CORPUS = "NOVA_ETUDIANTS"
EXCLURE_DOSSIERS = {"__pycache__", ".pytest_cache", "uploads", "demo_rendu"}
EXCLURE_FICHIERS = {".env", "demo.db", "memory_playground.db"}
BASE = Path("nova_brain/data/memory.db")


def a_exclure(rel: Path) -> bool:
    if any(p in EXCLURE_DOSSIERS for p in rel.parts):
        return True
    nom = rel.name
    return nom in EXCLURE_FICHIERS or nom.endswith(("-wal", "-shm", ".pyc")) or nom.startswith(("demo.db", "memory_playground.db"))


def fichiers(avec_corpus: bool):
    for racine in INCLURE + ([CORPUS] if avec_corpus else []):
        p = ROOT / racine
        if p.is_file():
            yield Path(racine)
        else:
            for f in sorted(p.rglob("*")):
                rel = f.relative_to(ROOT)
                if f.is_file() and not a_exclure(rel) and rel != BASE:
                    yield rel


def construire(sortie: Path, avec_corpus: bool) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        instantane = Path(tmp) / "memory.db"
        src, dst = sqlite3.connect(ROOT / BASE), sqlite3.connect(instantane)
        src.backup(dst)
        dst.close()
        src.close()
        n = 0
        with zipfile.ZipFile(sortie, "w", zipfile.ZIP_DEFLATED) as z:
            for rel in fichiers(avec_corpus):
                z.write(ROOT / rel, rel.as_posix())
                n += 1
            z.write(instantane, BASE.as_posix())
    return n + 1


def verifier(archive: Path) -> list[str]:
    """Contrôles : aucun secret, livrables présents, application lancée depuis l'archive sans .env."""
    erreurs = []
    with zipfile.ZipFile(archive) as z:
        noms = set(z.namelist())
        cle = dict(l.split("=", 1) for l in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
                   if "=" in l and not l.startswith("#")).get("ZAI_API_KEY", "") if (ROOT / ".env").exists() else ""
        if ".env" in noms:
            erreurs.append(".env présent dans l'archive")
        if cle and any(cle.encode() in z.read(n) for n in noms):
            erreurs.append("la clé d'API apparaît dans un fichier de l'archive")
        for attendu in ["rendu/01_Brief_reprise.pdf", "rendu/02_Memoire/actions.pdf", "rendu/02_Memoire/contradictions.pdf",
                        "rendu/03_Reponses_Q01-Q10.md", "rendu/03_Reponses_Q01-Q10.pdf","rendu/05_Mode_emploi.pdf", BASE.as_posix()]:
            if attendu not in noms:
                erreurs.append(f"manquant : {attendu}")
        if not any(n.startswith("rendu/04_Mise_a_jour/") for n in noms):
            erreurs.append("AVERTISSEMENT : rendu/04_Mise_a_jour/ absent (livrable 4, après la nouvelle information)")
        with tempfile.TemporaryDirectory() as tmp:
            z.extractall(tmp)
            code = ("from streamlit.testing.v1 import AppTest; at = AppTest.from_file('app.py', default_timeout=90).run(); "
                    "print('EXC', len(at.exception), 'ONGLETS', len(at.tabs))")
            env = {k: v for k, v in os.environ.items() if k != "NOVA_DB"}
            r = subprocess.run([sys.executable, "-c", code], cwd=tmp, capture_output=True, text=True, env=env, timeout=300)
            ligne = next((l for l in r.stdout.splitlines() if l.startswith("EXC")), "")
            if ligne != "EXC 0 ONGLETS 6":
                erreurs.append(f"l'application ne démarre pas depuis l'archive : {ligne or r.stderr[-500:]}")
    return erreurs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-corpus", action="store_true", help="ne pas inclure NOVA_ETUDIANTS/")
    ap.add_argument("--sortie", default=str(ROOT.parent / "NOVA_rendu.zip"))
    a = ap.parse_args()
    sortie = Path(a.sortie)
    n = construire(sortie, not a.sans_corpus)
    print(f"Archive : {sortie} ({n} fichiers, {sortie.stat().st_size / 1e6:.1f} Mo)")
    erreurs = verifier(sortie)
    for e in erreurs:
        print(" -", e)
    bloquantes = [e for e in erreurs if not e.startswith("AVERTISSEMENT")]
    print("Vérification : OK" if not bloquantes else "Vérification : ÉCHEC")
    sys.exit(1 if bloquantes else 0)


if __name__ == "__main__":
    main()
