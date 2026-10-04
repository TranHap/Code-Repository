"""Lecture des dates écrites en français dans le contenu des documents."""
import re
from datetime import date
from email.utils import parsedate_to_datetime

MOIS = {
    "janvier": 1, "janv": 1, "février": 2, "fevrier": 2, "févr": 2, "fevr": 2, "fév": 2, "fev": 2,
    "mars": 3, "avril": 4, "avr": 4, "mai": 5, "juin": 6, "juillet": 7, "juil": 7, "août": 8, "aout": 8,
    "septembre": 9, "sept": 9, "octobre": 10, "oct": 10, "novembre": 11, "nov": 11,
    "décembre": 12, "decembre": 12, "déc": 12, "dec": 12,
}
_MOIS_RE = "|".join(sorted(MOIS, key=len, reverse=True))
# Le mois doit être un mot entier ("5 décisions" n'est pas le 5 décembre).
RE_FR = re.compile(rf"\b(\d{{1,2}})(?:er)?\s+({_MOIS_RE})\.?(?![a-zà-ÿ])(?:\s+(\d{{4}}))?", re.I)
RE_ISO = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)")
RE_NUM = re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d\d)\b")   # jj/mm/aaaa (usage québécois)


def _iso(y, m, d) -> str | None:
    try:
        return date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return None


def find_date(text: str, default_year: int | None = None) -> str | None:
    """Première date valide trouvée dans le texte, au format ISO (AAAA-MM-JJ)."""
    found = []
    for m in RE_ISO.finditer(text):
        found.append((m.start(), _iso(m[1], m[2], m[3])))
    for m in RE_NUM.finditer(text):
        found.append((m.start(), _iso(m[3], m[2], m[1])))
    for m in RE_FR.finditer(text):
        year = m[3] or default_year
        if year:
            found.append((m.start(), _iso(year, MOIS[m[2].lower()], m[1])))
    found = sorted(f for f in found if f[1])
    return found[0][1] if found else None


def date_en_tete(text: str, default_year: int | None = None) -> str | None:
    """Date qui OUVRE la ligne (« 9 septembre - lot rejoué », « 2026-09-05T11:15 ... »).

    Une date citée au milieu d'une phrase (« Cible : 15 octobre 2026 ») est un contenu,
    pas la date à laquelle le fait s'est produit.
    """
    t = text.lstrip("-•* ")
    for rx in (RE_ISO, RE_NUM, RE_FR):
        m = rx.match(t)
        if m:
            d = find_date(t[:m.end()], default_year)
            if d:
                return d
    return None


RE_PREFIXE_JOUR = re.compile(r"^(?:date\s*:\s*)?(?:(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+)?(?:le\s+)?", re.I)
RE_PLAGE_HORAIRE = re.compile(r"^\s*(?:-\s*)?\d{1,2}[:h]\d{2}(?:\s*(?:à|-)\s*\d{1,2}[:h]\d{2})?\s*$")


def entete_de_jour(text: str, default_year: int | None = None) -> str | None:
    """Ligne qui n'est QU'une date (« 16 septembre 2026 », « Date : 7 juillet 2026 »,
    « 10 septembre 2026 - 15:00 à 15:42 ») : elle ouvre un nouveau jour dans un fil Teams ou un CR.
    « Décision : 15 octobre » n'en est pas une : c'est un contenu."""
    t = RE_PREFIXE_JOUR.sub("", text.strip())
    for rx in (RE_ISO, RE_NUM, RE_FR):
        m = rx.match(t)
        if m:
            reste = t[m.end():].strip(" .,")
            if not reste or RE_PLAGE_HORAIRE.match(reste):
                return find_date(t[:m.end()], default_year)
    return None


def email_date(header: str) -> str | None:
    """Heure locale de l'expéditeur, sans fuseau (comparable aux heures des transcripts)."""
    try:
        return parsedate_to_datetime(header).replace(tzinfo=None).isoformat(timespec="minutes")
    except Exception:
        return None
