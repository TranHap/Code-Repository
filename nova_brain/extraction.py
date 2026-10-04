"""Extraction LLM : à partir des preuves d'un lot (nouveaux fichiers), PROPOSER des assertions.

Le LLM ne décide rien et n'écrit rien : il produit des propositions, validées par le code
(vocabulaire, statut, ancre de preuve existante), puis écrites dans un CSV de relecture.
Une personne relit (colonne « garder ») avant le chargement :

    python -m nova_brain.extraction --lot 7            # propositions pour les fichiers du lot 7
    python -m nova_brain.assertions <csv relu> --extraction   (ou via nova_brain.nouvelle_info)
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

from . import assertions as asr
from . import config, db, llm
from .resolver import resoudre
from .vocab import ENUMS, FAMILLES, STATUTS

COLONNES_REVUE = asr.COLONNES + ["garder", "confiance", "erreur"]

PROMPT = """Tu extrais des ASSERTIONS d'un document du projet NOVA pour une mémoire de projet.
Une assertion = UNE clé, UNE valeur, appuyée par UNE unité de preuve du document (son ancre).

VOCABULAIRE DES CLÉS (motif → type de valeur) :
{vocab}

STATUTS (choisis selon QUI parle et CE QU'IL fait) :
- DECISION : une instance ou une personne habilitée tranche (« approuvé », « on décide », « reporté à »).
- VALIDATION : la personne responsable vérifie et accepte (« validé », « re-test OK, je ferme »).
- CONSTAT : observation d'un état par quelqu'un (« toujours ouvert », « pas reçu »).
- DOCUMENT : document de référence (contrat, facture, CR signé, schéma) qui énonce une valeur.
- ENGAGEMENT : promesse ou action à faire (« on vise la prochaine build »).
- PROPOSITION : recommandation, demande, brouillon, estimation. JAMAIS une décision.
- DECLARATION : affirmation non vérifiée, typiquement le fournisseur (« c'est réglé », « livré »).
- REFLET : plan, registre, rapport de statut qui recopie un état.

RÈGLES
1. Réutilise les CLÉS EXISTANTES ci-dessous quand le sujet est le même (même ticket, même date de go-live...).
2. Le fournisseur (Boréal) qui dit avoir corrigé = DECLARATION (+ livraison:<ticket> = LIVRE), jamais VALIDATION.
3. Une demande de report ou de changement non tranchée = PROPOSITION. Ne conclus pas qu'elle est approuvée.
4. acteur = nom complet de la personne ou de l'instance qui s'exprime (voir personnes connues).
5. date_fait : laisse vide (la date de la preuve sera utilisée), sauf date d'effet explicite différente.
6. lien : pour golive:condition, risque, rapport → clé du ticket concerné (ex. ticket:SEC-210:statut).
7. ancre : exactement l'identifiant entre crochets de l'unité de preuve (ex. L17, msg, p1, capture).
8. N'invente rien. Ignore le bavardage. Si rien d'utile : liste vide.
9. confiance : haute / moyenne / basse.

CLÉS EXISTANTES ET VALEURS ACTUELLES :
{faits}

PERSONNES CONNUES : {personnes}

Réponds UNIQUEMENT par un objet JSON :
{{"assertions": [{{"ancre": "...", "cle": "...", "valeur": "...", "statut": "...", "acteur": "...",
  "date_fait": "", "lien": "", "note": "citation courte", "confiance": "haute"}}]}}

DOCUMENT : {path} (classe de source : {classe})
{unites}
"""


def _vocab() -> str:
    lignes = []
    for f in FAMILLES:
        if f.statuts is not None and not f.statuts:
            continue   # clés calculées : jamais extraites
        t = f.type
        if t.startswith("enum:"):
            t = "|".join(sorted(ENUMS[t[5:]]))
        contrainte = f" [statut : {', '.join(sorted(f.statuts))} uniquement]" if f.statuts else ""
        lignes.append(f"- {f.motif} → {t} ({f.aide}){contrainte}")
    return "\n".join(lignes)


def _contexte(con):
    faits = resoudre(con)
    lignes = [f"- {c} = {f.valeur}" for c, f in sorted(faits.items())
              if f.valeur is not None and f.etat != "calcule"]
    personnes = sorted({f.valeur for c, f in faits.items() if c.startswith("role:") and f.valeur}
                       | {c.split(":", 1)[1] for c in faits if c.startswith("organisation:")})
    roles = ", ".join(f"{c[5:]}={f.valeur}" for c, f in sorted(faits.items()) if c.startswith("role:") and f.valeur)
    return "\n".join(lignes), f"{', '.join(personnes)} (rôles : {roles}) ; fournisseur : Boréal"


def _unites(con, f) -> tuple[str, int]:
    """Unités à extraire. Pour une nouvelle VERSION d'un fichier, seules les unités nouvelles sont extractibles ;
    les anciennes (déjà dans la mémoire) sont données comme contexte, sans ancre."""
    rows = con.execute("SELECT ev_id, repere, auteur, texte FROM evidence WHERE file_id=? ORDER BY rowid",
                       (f["file_id"],)).fetchall()
    connus = set()
    if f["change"] == "modifie":
        prev = con.execute("SELECT MAX(file_id) FROM files WHERE path=? AND file_id<?", (f["path"], f["file_id"])).fetchone()[0]
        connus = {r["texte"] for r in con.execute("SELECT texte FROM evidence WHERE file_id=?", (prev,))}
    lignes, n = [], 0
    for r in rows:
        if r["texte"] in connus:
            lignes.append(f"(contexte déjà en mémoire, ne pas extraire) {r['repere']} | {r['auteur'] or ''} | {r['texte']}")
        else:
            n += 1
            lignes.append(f"[{r['ev_id'].split('#', 1)[1]}] {r['repere']} | {r['auteur'] or ''} | {r['texte']}")
    return "\n".join(lignes), n


def _json(texte: str) -> list:
    m = re.search(r"\{.*\}", texte or "", re.S)
    if not m:
        return []
    try:
        return json.loads(m.group(0)).get("assertions", [])
    except json.JSONDecodeError:
        return []


def _ancre(a: str) -> str:
    a = (a or "").strip().strip("[]#")
    if m := re.match(r"(?:ligne|line)\s*(\d+)$", a, re.I):
        return f"L{m.group(1)}"
    if m := re.match(r"p\.?\s*(\d+)$", a, re.I):
        return f"p{m.group(1)}"
    return a


def _textes_precedents(con, f) -> set:
    prev = con.execute("SELECT MAX(file_id) FROM files WHERE path=? AND file_id<?", (f["path"], f["file_id"])).fetchone()[0]
    return {r["texte"] for r in con.execute("SELECT texte FROM evidence WHERE file_id=?", (prev,))} if prev else set()


def fichiers_du_lot(con, batch: int) -> list:
    """Fichiers nouveaux ou modifiés du lot, hors doublons et hors pièces jointes déjà connues."""
    return con.execute("""SELECT * FROM files WHERE batch_id=? AND change IN ('nouveau','modifie')
                          AND duplicate_of IS NULL AND status IN ('ok','incomplet') ORDER BY path""", (batch,)).fetchall()


def extraire(con, batch: int, appel_llm=None) -> list:
    """Propositions pour chaque fichier du lot : [{...colonnes CSV..., garder, confiance, erreur}]."""
    appel_llm = appel_llm or (lambda prompt: llm.chat([{"role": "user", "content": prompt}], temperature=0.1)
                              .choices[0].message.content)
    faits, personnes = _contexte(con)
    vocab = _vocab()
    out = []
    for f in fichiers_du_lot(con, batch):
        unites, n_nouvelles = _unites(con, f)
        if n_nouvelles == 0:
            continue   # nouvelle version sans contenu nouveau (ex. mise en forme)
        prompt = PROMPT.format(vocab=vocab, faits=faits, personnes=personnes, path=f["path"],
                               classe=f["source_class"], unites=unites)
        try:
            props = _json(appel_llm(prompt))
        except Exception as e:
            out.append({"ref": f"ERREUR:{f['path']}", "cle": "", "garder": "non", "erreur": f"LLM : {type(e).__name__}: {e}"})
            continue
        for i, p in enumerate(props, start=1):
            row = {"ref": f"X{batch}-{Path(f['path']).stem[:20]}-{i}", "cle": (p.get("cle") or "").strip(),
                   "valeur": str(p.get("valeur") or ""), "statut": (p.get("statut") or "").upper(),
                   "acteur": p.get("acteur") or "", "autorite": "", "date_fait": p.get("date_fait") or "",
                   "source": f["path"], "ancre": _ancre(p.get("ancre")), "lien": p.get("lien") or "",
                   "note": p.get("note") or "", "confiance": p.get("confiance") or ""}
            try:
                a = asr.preparer(con, row)
                ev = con.execute("SELECT texte FROM evidence WHERE ev_id=?", (a["ev_id"],)).fetchone()
                if f["change"] == "modifie" and ev and ev["texte"] in _textes_precedents(con, f):
                    raise asr.AssertionInvalide("ancre sur un contenu déjà en mémoire (version précédente du fichier)")
                row.update(valeur=a["valeur"], statut=a["statut"], garder="oui", erreur="")
            except asr.AssertionInvalide as e:
                row.update(garder="non", erreur=str(e))
            out.append(row)
    return out


def ecrire_revue(rows: list, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLONNES_REVUE, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLONNES_REVUE})
    return path


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--lot", type=int, required=True)
    a = ap.parse_args()
    con = db.connect()
    rows = extraire(con, a.lot)
    p = ecrire_revue(rows, config.ROOT / "rendu" / "04_Mise_a_jour" / f"propositions_lot{a.lot}.csv")
    ok = sum(r.get("garder") == "oui" for r in rows)
    print(f"{len(rows)} propositions ({ok} valides, {len(rows) - ok} rejetées) → {p}")


if __name__ == "__main__":
    main()
