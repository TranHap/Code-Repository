"""Recherche plein texte dans les preuves (version courante de chaque fichier).

Le corpus est petit (quelques centaines d'unités) : un score TF-IDF calculé à la volée suffit,
sans index ni base vectorielle. Interface stable : chercher(con, texte) -> liste de preuves,
remplaçable par BM25 ou des embeddings si le corpus grossit.
"""
import math
import re
import unicodedata
from collections import Counter

STOP = set("""le la les un une des de du d l a à au aux et ou en dans pour par sur avec sans ce cette ces
qui que quoi est sont été être pas ne plus se sa son ses leur leurs nous vous il elle on y je tu
quel quelle quels quelles comment pourquoi quand combien the of to and""".split())


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def tokens(s: str) -> list:
    return [t for t in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", _norm(s)) if len(t) > 1 and t not in STOP]


def chercher(con, texte: str, n: int = 8, fichier: str | None = None) -> list:
    rows = con.execute("""
        SELECT e.ev_id, e.repere, e.date_fait, e.auteur, e.texte, f.path, f.source_class, f.duplicate_of
        FROM evidence e JOIN files f USING(file_id)
        WHERE f.file_id IN (SELECT MAX(file_id) FROM files GROUP BY path)""").fetchall()
    if fichier:
        rows = [r for r in rows if fichier.lower() in r["path"].lower()]
    q = tokens(texte)
    if not q or not rows:
        return []
    docs = [Counter(tokens(r["texte"] + " " + r["path"].rsplit("/", 1)[-1])) for r in rows]
    df = Counter(t for d in docs for t in set(d))
    N = len(docs)
    scored = []
    for r, d in zip(rows, docs):
        s = sum((1 + math.log(d[t])) * math.log(1 + N / df[t]) for t in q if d[t])
        if s:
            if r["duplicate_of"] or r["source_class"] in ("hors_projet_probable", "non_officiel"):
                s *= 0.5   # reste trouvable, mais derrière les sources officielles
            scored.append((s, r))
    scored.sort(key=lambda x: -x[0])
    return [dict(r) for _, r in scored[:n]]


def lire(con, ev_id: str, contexte: int = 2) -> dict | None:
    """Une preuve et ses voisines dans le même fichier (pour lire un tour de parole dans son contexte)."""
    e = con.execute("SELECT e.*, f.path, f.source_class, f.duplicate_of FROM evidence e JOIN files f USING(file_id) "
                    "WHERE e.ev_id = ?", (ev_id,)).fetchone()
    if e is None:
        return None
    voisins = con.execute("SELECT ev_id, repere, auteur, texte FROM evidence WHERE file_id = ? ORDER BY rowid",
                          (e["file_id"],)).fetchall()
    idx = next(i for i, v in enumerate(voisins) if v["ev_id"] == ev_id)
    return {"preuve": dict(e), "voisins": [dict(v) for v in voisins[max(0, idx - contexte): idx + contexte + 1]]}
