"""Mise à jour de la mémoire depuis une conversation : proposition → aperçu des impacts → confirmation humaine.

Garde-fous appliqués par le CODE (pas seulement par le prompt du LLM) :
- rien n'est écrit sans confirmation explicite de l'utilisateur ;
- sans décideur, date et référence de preuve, une affirmation est enregistrée comme DECLARATION :
  le résolveur ne la laissera jamais remplacer une décision documentée ;
- le message de l'utilisateur devient lui-même une preuve citable (chat/<horodatage>#msg) ;
- rien n'est modifié ni supprimé : l'ancienne valeur reste dans l'historique.
"""
import hashlib
from dataclasses import dataclass, field

from . import assertions as asr
from . import db
from .resolver import diff, resoudre

STATUTS_PROUVES = {"DECISION", "VALIDATION", "DOCUMENT", "CONSTAT"}


@dataclass
class Proposition:
    cle: str
    valeur: str
    statut: str
    acteur: str | None
    date_fait: str | None
    preuve: str | None             # référence fournie par l'utilisateur (« CR du comité du 2 octobre »)
    note: str | None
    lien: str | None = None
    avertissements: list = field(default_factory=list)
    impacts: list = field(default_factory=list)

    def resume(self) -> str:
        s = f"{self.cle} = {self.valeur}  [{self.statut}]"
        if self.acteur:
            s += f" par {self.acteur}"
        if self.date_fait:
            s += f", effet {self.date_fait}"
        if self.preuve:
            s += f" — preuve citée : {self.preuve}"
        return s


def preparer(con, cle, valeur, statut="DECLARATION", acteur=None, date_fait=None, preuve=None, note=None,
             lien=None, policy=None, utilisateur="utilisateur") -> Proposition:
    """Valide (vocabulaire, statut) et calcule l'impact, SANS rien écrire. Lève AssertionInvalide."""
    statut = (statut or "DECLARATION").upper()
    av = []
    if statut in STATUTS_PROUVES and not (acteur and date_fait and preuve):
        manque = [n for n, v in (("décideur", acteur), ("date", date_fait), ("référence de preuve", preuve)) if not v]
        av.append(f"{statut} demandé mais {', '.join(manque)} manquant(s) : enregistré comme DECLARATION "
                  "(ne remplace aucune décision documentée)")
        statut = "DECLARATION"
        if acteur:   # « le comité a décidé » sans preuve : c'est l'utilisateur qui l'affirme, pas le comité
            note = "; ".join(x for x in (note, f"selon l'utilisateur : {acteur}") if x)
            acteur = None
    elif statut in STATUTS_PROUVES:
        av.append(f"preuve citée (« {preuve} ») mais non versée dans la mémoire : téléverser le document "
                  "pour qu'elle soit vérifiable")
    if statut in ("DECLARATION", "PROPOSITION") and not acteur:
        acteur = f"{utilisateur} (chat)"      # l'auteur de l'affirmation, pas la personne concernée
    a = asr.preparer(con, dict(ref="chat", cle=cle, valeur=valeur, statut=statut, acteur=acteur,
                               autorite="", date_fait=date_fait or "", source="", ancre="", lien=lien or "", note=note or ""))
    p = Proposition(a["cle"], a["valeur"], a["statut"], a["acteur"], a["date_fait"], preuve, note, a["lien"], av)
    p.impacts = impact(con, p, policy)
    if not p.impacts:
        p.avertissements.append("aucun fait ne change : l'information est conservée dans l'historique seulement")
    return p


def impact(con, p: Proposition, policy=None) -> list:
    """Résout avant / après dans une transaction annulée : ce qui changerait si on enregistrait."""
    con.commit()
    avant = resoudre(con, policy)
    con.execute("SAVEPOINT apercu")
    try:
        asr.inserer(con, _assertion(p, None, None), "apercu", 0)
        apres = resoudre(con, policy)
    finally:
        con.execute("ROLLBACK TO apercu")
        con.execute("RELEASE apercu")
    return diff(avant, apres)


def _assertion(p: Proposition, source, ancre) -> dict:
    note = " ; ".join(x for x in (p.note, f"preuve citée : {p.preuve}" if p.preuve else None) if x) or None
    return {"ref": "chat", "cle": p.cle, "valeur": p.valeur, "statut": p.statut, "acteur": p.acteur, "autorite": None,
            "date_fait": p.date_fait, "lien": p.lien, "ev_id": f"{source}#{ancre}" if source else None,
            "source": source, "ancre": ancre, "note": note}


def appliquer(con, p: Proposition, utilisateur: str, message: str) -> int:
    """Écrit la proposition confirmée : un lot « chat », le message comme preuve, puis l'assertion."""
    ts = db.now()
    batch = db.new_batch(con, "chat", f"{utilisateur} : {message[:60]}")
    path = f"chat/{ts}"
    fid = con.execute("""INSERT INTO files(path, sha256, ext, size, doc_date, title, source_class, change, status,
                                           batch_id) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (path, hashlib.sha256(message.encode()).hexdigest(), "chat", len(message), ts[:10],
                       f"Message de {utilisateur}", "chat", "nouveau", "ok", batch)).lastrowid
    con.execute("INSERT INTO evidence(ev_id, file_id, unit, repere, date_fait, auteur, texte, batch_id) VALUES (?,?,?,?,?,?,?,?)",
                (f"{path}#msg", fid, "message", f"message du {ts}", ts, utilisateur, message, batch))
    aid = asr.inserer(con, _assertion(p, path, "msg"), f"chat:{utilisateur}", batch)
    con.commit()
    return aid
