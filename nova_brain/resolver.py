"""Résolveur : à partir des assertions (append-only) et de la politique, calcule les faits en vigueur.

Code déterministe : mêmes assertions + même politique = même résultat, et chaque verdict a une raison.

    python -m nova_brain.resolver                         # tous les faits
    python -m nova_brain.resolver --cle projet:date_golive # détail avec historique et verdicts
    python -m nova_brain.resolver --as-of 2026-09-09       # état du projet à une date
    python -m nova_brain.resolver --diff autre_policy.toml # ce qui change avec une autre politique

Étapes :
1. Rôles : chronologie des titulaires (role:*), pour connaître l'autorité de chacun À LA DATE du fait.
2. Autorité de chaque assertion (forcée, ou calculée depuis les rôles et l'organisation).
3. Recevabilité : seules certaines personnes peuvent « fermer » un sujet (policy [validation]).
4. Par clé : candidats = statuts gagnants de la famille ; départage selon l'ordre de la famille ;
   égalité parfaite avec valeurs différentes = CONFLIT (jamais tranché au hasard).
5. Verdict et raison pour chaque assertion non retenue.
6. Règles additionnelles (policy [regles]) : cohérence des reflets, calculs dérivés.
"""
import argparse
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field

from . import db
from . import policy as pol
from .regles import REGLES


@dataclass
class A:
    """Assertion enrichie par le résolveur."""
    id: int
    ref: str
    cle: str
    valeur: str
    statut: str
    acteur: str | None
    autorite_forcee: str | None
    date_fait: str | None
    lien: str | None
    ev_id: str | None
    source: str | None
    note: str | None
    origine: str
    niveau: str = ""
    recevable: bool = True
    verdict: str = ""
    raison: str = ""

    @property
    def date(self) -> str:
        return self.date_fait or ""

    def court(self) -> str:
        src = (self.source or self.origine).rsplit("/", 1)[-1]
        ancre = self.ev_id.split("#", 1)[1] if self.ev_id and "#" in self.ev_id else ""
        return f"{self.ref} · {self.acteur or '?'} · {self.date or 's.d.'} · {src}{' ' + ancre if ancre else ''}"


@dataclass
class Fait:
    cle: str
    valeur: str | None
    etat: str                     # retenu | non_decide | conflit | calcule
    retenu: A | None = None
    historique: list = field(default_factory=list)
    alertes: list = field(default_factory=list)
    explication: str = ""
    sources: list = field(default_factory=list)   # assertions utilisées par un calcul

    def par_statut(self, statut: str, meme_valeur=True) -> list:
        return [a for a in self.historique if a.statut == statut and a.recevable
                and (not meme_valeur or a.valeur == self.valeur)]

    @property
    def proposee_par(self):
        return self.par_statut("PROPOSITION")

    @property
    def decisions(self):
        return self.par_statut("DECISION")

    @property
    def validations(self):
        return self.par_statut("VALIDATION")


# ───────────────────────── Personnes et rôles ─────────────────────────

def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().casefold().strip()


def personnes(acteur: str | None) -> list:
    if not acteur:
        return []
    for sep in (" / ", ",", " et "):
        acteur = acteur.replace(sep, "|")
    return [p.strip() for p in acteur.split("|") if p.strip()]


def meme_personne(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    return a == b or a.split()[0] == b or b.split()[0] == a


def avant(d1: str, d2: str) -> bool:
    """d1 strictement avant d2. Si l'une n'a pas d'heure, on compare au jour près
    (« 16 septembre » et « 16 septembre 08:35 » sont le même moment, pas l'un avant l'autre)."""
    if len(d1) <= 10 or len(d2) <= 10:
        return d1[:10] < d2[:10]
    return d1 < d2


class Roles:
    """Qui détient quel rôle à quelle date, d'après les assertions role:* (faits datés)."""

    def __init__(self, assertions, policy):
        statuts = set(policy.famille("role:x")["gagnant"])
        self.chrono = defaultdict(list)
        self.org = {}
        for a in sorted(assertions, key=lambda a: a.date):
            if a.cle.startswith("role:") and a.statut in statuts:
                self.chrono[a.cle[5:]].append((a.date, a.valeur, a))
            if a.cle.startswith("organisation:"):
                self.org[_norm(a.cle.split(":", 1)[1])] = a.valeur
        self.fournisseurs = [_norm(f) for f in policy.fournisseurs]

    def titulaire(self, role: str, date: str, strict: bool = False):
        """Titulaire à cette date ; strict=True : juste AVANT (autorité de celui qui transmet un rôle)."""
        actuel = None
        for d, personne, a in self.chrono.get(role, []):
            if not date or (avant(d, date) if strict else not avant(date, d)):
                actuel = (personne, a)
        return actuel

    def detient(self, personne: str, role: str, date: str, strict: bool = False) -> bool:
        t = self.titulaire(role, date, strict)
        return bool(t and meme_personne(personne, t[0]))

    def est_fournisseur(self, personne: str) -> bool:
        n = _norm(personne)
        org = next((v for k, v in self.org.items() if meme_personne(k, n)), "")
        return any(f in n or f in _norm(org) for f in self.fournisseurs)


def niveau(a: A, roles: Roles, policy) -> str:
    if a.autorite_forcee:
        return a.autorite_forcee
    for niv, noms in policy.instances.items():
        if any(_norm(n) in _norm(a.acteur or "") for n in noms):
            return niv
    domaine = policy.domaine(a.cle)
    strict = a.cle.startswith("role:")   # qui nomme un successeur agit avec son autorité d'avant la passation
    meilleurs = []
    for p in personnes(a.acteur):
        if roles.detient(p, "charge_de_projet", a.date, strict):
            meilleurs.append("charge_de_projet")
        elif domaine and roles.detient(p, domaine, a.date, strict):
            meilleurs.append("responsable_domaine")
        elif roles.est_fournisseur(p):
            meilleurs.append("fournisseur")
        else:
            meilleurs.append("partie_prenante")
    return min(meilleurs, key=policy.rang) if meilleurs else "partie_prenante"


def recevable(a: A, roles: Roles, policy, gagnant: set) -> tuple[bool, str]:
    """Seuls le comité ou le responsable du domaine peuvent poser une valeur « fermante »."""
    if a.valeur not in policy.valeurs_controlees or a.statut not in gagnant:
        return True, ""
    if a.niveau == "comite":
        return True, ""
    domaine = policy.domaine(a.cle)
    if domaine:
        if any(roles.detient(p, domaine, a.date) for p in personnes(a.acteur)):
            return True, ""
        t = roles.titulaire(domaine, a.date)
        qui = f" ({t[0]})" if t else ""
        return False, f"« {a.valeur} » réservé au rôle {domaine}{qui} ou au comité"
    if a.niveau in ("fournisseur", "non_officiel"):
        return False, f"« {a.valeur} » ne peut pas être posé par {a.niveau}"
    return True, ""


# ───────────────────────── Résolution par clé ─────────────────────────

def _cle_tri(a: A, ordre, policy):
    return tuple(a.date if c == "date_fait" else -policy.rang(a.niveau) for c in ordre)


def resoudre_cle(cle: str, items: list, policy) -> Fait:
    fam = policy.famille(cle)
    gagnant, ordre = set(fam["gagnant"]), fam["ordre"]
    histo = sorted(items, key=lambda a: (a.date, a.id))
    candidats = [a for a in histo if a.statut in gagnant and a.recevable]
    if not candidats:
        for a in histo:
            if not a.verdict:
                a.verdict = {"PROPOSITION": "proposition en attente", "DECLARATION": "déclaration non confirmée"}.get(
                    a.statut, "en attente")
                a.raison = a.raison or "aucune assertion décisive pour cette clé"
        return Fait(cle, None, "non_decide", None, histo)

    best = max(candidats, key=lambda a: (_cle_tri(a, ordre, policy), a.id))
    k = _cle_tri(best, ordre, policy)
    rivaux = [a for a in candidats if _cle_tri(a, ordre, policy) == k and a.valeur != best.valeur]
    if rivaux:
        for a in [best] + rivaux:
            a.verdict, a.raison = "en conflit", "même autorité et même date, valeurs différentes : arbitrage humain requis"
        f = Fait(cle, None, "conflit", None, histo)
        f.alertes.append(f"CONFLIT : {' vs '.join(sorted({a.valeur for a in [best] + rivaux}))}")
        return f

    best.verdict = "retenu"
    best.raison = f"critères {' > '.join(ordre)} : {best.niveau}, {best.date or 's.d.'}"
    for a in histo:
        if a is best or a.verdict:
            continue
        same = a.valeur == best.valeur
        if a in candidats:
            if same:
                a.verdict, a.raison = "concordant", f"même valeur que {best.ref}"
            elif a.date > best.date:
                a.verdict = "écarté"
                a.raison = f"plus récent mais autorité {a.niveau} < {best.niveau} ({best.ref})"
            else:
                a.verdict, a.raison = "remplacé", f"remplacé par {best.ref} ({best.niveau}, {best.date})"
        elif a.statut == "PROPOSITION":
            a.verdict = "proposition adoptée" if same else "proposition non retenue"
            a.raison = f"décision : {best.ref}" if same else f"la valeur retenue est {best.valeur} ({best.ref})"
        elif a.statut == "DECLARATION":
            a.verdict = "déclaration confirmée" if same else "déclaration non confirmée"
            a.raison = f"confirmée par {best.ref}" if same else f"contredite par {best.ref} ({best.acteur}, {best.date})"
        elif a.statut == "REFLET":
            a.verdict = "reflet cohérent" if same else "reflet périmé"
            a.raison = "" if same else f"recopie {a.valeur} alors que {best.ref} ({best.date}) fixe {best.valeur}"
        else:
            a.verdict = "concordant" if same else "contexte"
            a.raison = "" if same else f"statut {a.statut} non décisif pour cette clé"
    return Fait(cle, best.valeur, "retenu", best, histo)


def _preuve_courante(con, source, ancre):
    """Unité de preuve dans la version courante du fichier (après re-parse ou nouvelle version)."""
    if not source:
        return None
    f = con.execute("SELECT file_id, doc_date FROM files WHERE path=? ORDER BY file_id DESC LIMIT 1", (source,)).fetchone()
    if f is None:
        return None
    e = con.execute("SELECT ev_id, date_fait FROM evidence WHERE file_id=? AND ev_id LIKE ?",
                    (f["file_id"], f"%#{ancre}")).fetchone() if ancre else None
    return {"ev_id": e["ev_id"] if e else None, "date_fait": e["date_fait"] if e else None, "doc_date": f["doc_date"]}


def charger(con, as_of=None, batch_max=None) -> list:
    out = []
    for r in db.active_assertions(con, batch_max):
        ev_id, date = r["ev_id"], r["date_fait"]
        p = _preuve_courante(con, r["source"], r["ancre"])
        if p:
            ev_id = p["ev_id"] or ev_id
            date = date or p["date_fait"] or p["doc_date"]
        if as_of and date and date[:len(as_of)] > as_of:
            continue
        out.append(A(r["assertion_id"], r["ref"], r["cle"], r["valeur"], r["statut"], r["acteur"], r["autorite"],
                     date, r["lien"], ev_id, r["source"], r["note"], r["origine"]))
    return out


def resoudre(con, policy=None, as_of: str | None = None, batch_max: int | None = None) -> dict:
    policy = policy or pol.load()
    assertions = charger(con, as_of, batch_max)
    roles = Roles(assertions, policy)
    par_cle = defaultdict(list)
    for a in assertions:
        a.niveau = niveau(a, roles, policy)
        fam = policy.famille(a.cle)
        a.recevable, raison = recevable(a, roles, policy, set(fam["gagnant"]))
        if not a.recevable:
            a.verdict, a.raison = "non recevable", raison
        par_cle[a.cle].append(a)
    faits = {cle: resoudre_cle(cle, items, policy) for cle, items in par_cle.items()}
    for nom in policy.regles:
        REGLES[nom](faits, policy)
    return faits


# ───────────────────────── Affichage ─────────────────────────

def ligne_fait(f: Fait) -> str:
    v = f.valeur if f.valeur is not None else "—"
    s = f"{f.cle} = {v}  [{f.etat}]"
    if f.retenu:
        s += f"  ← {f.retenu.court()}"
    return s


def detail(f: Fait) -> str:
    out = [ligne_fait(f)]
    if f.explication:
        out.append(f"  calcul : {f.explication}")
    for nom, lst in (("proposé", f.proposee_par), ("décidé", f.decisions), ("validé", f.validations)):
        for a in lst:
            out.append(f"  {nom} : {a.court()}")
    for al in f.alertes:
        out.append(f"  ⚠ {al}")
    for a in f.historique:
        out.append(f"    {a.date or 's.d.':16s} {a.statut:11s} {a.niveau:19s} {a.valeur[:28]:28s} {a.verdict}"
                   + (f" — {a.raison}" if a.raison and a.verdict != "retenu" else ""))
    return "\n".join(out)


def diff(f1: dict, f2: dict) -> list:
    out = []
    for cle in sorted(set(f1) | set(f2)):
        a, b = f1.get(cle), f2.get(cle)
        va = (a.valeur, a.etat, len(a.alertes)) if a else (None, "absent", 0)
        vb = (b.valeur, b.etat, len(b.alertes)) if b else (None, "absent", 0)
        if va == vb:
            continue
        parts = []
        if va[0] != vb[0] or va[1] != vb[1]:
            parts.append(f"{va[0] if va[0] is not None else '—'} [{va[1]}] → {vb[0] if vb[0] is not None else '—'} [{vb[1]}]")
        if va[2] != vb[2]:
            parts.append(f"alertes {va[2]} → {vb[2]}")
        out.append(f"{cle} : {' ; '.join(parts)}")
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default=str(pol.DEFAULT))
    ap.add_argument("--cle", help="préfixe de clé à détailler")
    ap.add_argument("--as-of", help="état à une date (AAAA-MM-JJ)")
    ap.add_argument("--diff", help="autre politique à comparer")
    a = ap.parse_args()
    con = db.connect()
    p = pol.load(a.policy)
    faits = resoudre(con, p, a.as_of)
    print(f"Politique {p.version} ({p.empreinte}){' — état au ' + a.as_of if a.as_of else ''}\n")
    if a.diff:
        p2 = pol.load(a.diff)
        changes = diff(faits, resoudre(con, p2, a.as_of))
        print(f"Différences avec {p2.version} : {len(changes)}")
        print("\n".join("  " + c for c in changes) or "  aucune")
        return
    for cle in sorted(faits):
        if a.cle and not cle.startswith(a.cle):
            continue
        print(detail(faits[cle]) if a.cle else ligne_fait(faits[cle]) + "".join(f"\n    ⚠ {x}" for x in faits[cle].alertes))


if __name__ == "__main__":
    main()
