"""Agent conversationnel : répond depuis la mémoire avec sources, et met à jour la mémoire sur confirmation.

    python -m nova_brain.chat [--utilisateur NOM]

Le LLM ne voit jamais les chemins de fichiers bruts : chaque preuve reçoit un identifiant court [S12]
et le code remplace ces identifiants par le fichier et le repère exacts. Un identifiant inventé
est signalé, pas affiché comme une source.
"""
import argparse
import difflib
import json
import re
import sys
from dataclasses import dataclass, field

from . import db, llm, mise_a_jour, recherche
from . import policy as pol
from .assertions import AssertionInvalide
from .resolver import resoudre
from .vocab import FAMILLES

DATE_REFERENCE = "2026-09-30 09:00 (heure de Montréal)"
MAX_TOURS = 8

SYSTEM = """Tu es la mémoire opérationnelle du projet NOVA. Date de référence : {date_ref}.

RÈGLES
1. Tu réponds UNIQUEMENT à partir des faits et preuves fournis par tes outils. Si une information manque : « non documenté ».
2. Chaque affirmation factuelle cite au moins une source sous la forme [S<n>] exactement comme donnée par les outils.
   N'invente jamais d'identifiant.
3. Distingue toujours : proposé (par qui, quand) / décidé ou approuvé (par qui, quand) / livré / validé.
   Une proposition n'est pas une décision ; « livré » ou « corrigé » par le fournisseur n'est pas « validé ».
4. Signale les contradictions écartées (plan, registre, rapport périmés) et pourquoi, d'après les verdicts.
5. Montants en CAD hors taxes ; distingue autorisé, facturé et payé.
6. Si l'utilisateur APPORTE une information nouvelle ou un changement (« X est maintenant responsable »,
   « SEC-210 a été validé »), appelle proposer_mise_a_jour. Ne prétends jamais l'avoir enregistrée :
   c'est l'utilisateur qui confirme, et le résultat de l'outil te dit ce qui a été fait.
   N'invente ni décideur, ni date, ni preuve : laisse vides ceux que l'utilisateur n'a pas donnés.
7. AVANT de répondre à une question, appelle detail_fait sur la ou les clés concernées (la liste ci-dessous ne
   montre que la valeur retenue, pas qui a proposé, la première décision, ni les sources écartées).
   Pour une question sur le go-live, consulte aussi golive:condition et golive:reserve.
   Pour un domaine (sécurité, accessibilité, exploitation, intégration), consulte TOUS ses tickets (préfixes
   ticket:SEC, ticket:ACC, ticket:OPS, ticket:INT), le rapport:<domaine> et la condition de go-live liée :
   dis ce qui est fermé (et par qui), ce qui reste ouvert, et ce qui est seulement livré.
   Un rapport, un plan ou un registre (REFLET) n'est jamais une livraison ni une validation ; s'il porte une
   ALERTE « reflet périmé », c'est une contradiction à signaler.
8. Question ambiguë (ex. « le changement », « il ») : rattache-la au sujet de l'échange précédent et écris
   en une ligne l'interprétation retenue ; sans échange précédent, choisis le sens le plus probable et mentionne l'autre.
9. Réponds dans la langue de la question. Structure :
   **Réponse** (une ou deux phrases) · **Proposé / décidé / validé** (qui, quand, sources) ·
   **Contradictions écartées** (si pertinent) · **Reste à faire / incertain** (si pertinent).

FAITS EN VIGUEUR (résolus depuis la mémoire ; détails et historique via les outils)
{faits}
"""

TOOLS = [
    {"type": "function", "function": {
        "name": "detail_fait",
        "description": "Détail d'un fait : valeur retenue, qui a proposé/décidé/validé, historique complet avec verdicts "
                       "(remplacé, reflet périmé, déclaration non confirmée...) et alertes. Accepte une clé ou un préfixe.",
        "parameters": {"type": "object", "properties": {"cle": {"type": "string", "description": "ex. projet:date_golive, ticket:SEC-210"}},
                       "required": ["cle"]}}},
    {"type": "function", "function": {
        "name": "chercher_preuves",
        "description": "Recherche plein texte dans les courriels, comptes rendus, tickets, Teams, PDF, tableurs et captures.",
        "parameters": {"type": "object", "properties": {
            "texte": {"type": "string"},
            "fichier": {"type": "string", "description": "filtre optionnel sur le nom de fichier (ex. M04, SEC-210)"}},
            "required": ["texte"]}}},
    {"type": "function", "function": {
        "name": "lire_preuve",
        "description": "Texte complet d'une preuve [S<n>] avec les lignes voisines (contexte d'un tour de parole).",
        "parameters": {"type": "object", "properties": {"source": {"type": "string", "description": "ex. S12"}},
                       "required": ["source"]}}},
    {"type": "function", "function": {
        "name": "proposer_mise_a_jour",
        "description": "Propose d'enregistrer une information nouvelle apportée par l'utilisateur. Rien n'est écrit sans sa "
                       "confirmation. Sans décideur + date + référence de preuve, l'information est gardée comme DECLARATION.",
        "parameters": {"type": "object", "properties": {
            "cle": {"type": "string", "description": "clé du vocabulaire (ex. role:charge_de_projet, ticket:SEC-210:statut)"},
            "valeur": {"type": "string"},
            "statut": {"type": "string", "enum": ["DECLARATION", "DECISION", "VALIDATION", "CONSTAT", "PROPOSITION", "ENGAGEMENT"]},
            "acteur": {"type": "string", "description": "qui a décidé / constaté, tel que dit par l'utilisateur ; vide si inconnu"},
            "date_fait": {"type": "string", "description": "AAAA-MM-JJ ; vide si inconnue"},
            "preuve": {"type": "string", "description": "document ou réunion cité par l'utilisateur ; vide si aucun"},
            "note": {"type": "string"}},
            "required": ["cle", "valeur"]}}},
]


@dataclass
class Reponse:
    texte: str
    sources: list = field(default_factory=list)          # [(n, path, repère, date, auteur, ev_id)]
    avertissements: list = field(default_factory=list)
    mises_a_jour: list = field(default_factory=list)      # assertions enregistrées
    en_attente: list = field(default_factory=list)        # propositions à confirmer dans l'interface
    outils: list = field(default_factory=list)            # trace des appels (pour la démo / le débogage)


class Session:
    def __init__(self, con=None, policy=None, appel_llm=None, confirmer=None, utilisateur="utilisateur",
                 date_ref=DATE_REFERENCE):
        self.con = con or db.connect()
        self.policy = policy or pol.load()
        self.appel_llm = appel_llm or (lambda msgs: llm.chat(msgs, tools=TOOLS, temperature=0.2))
        self.confirmer = confirmer or (lambda prop: False)   # par défaut : on n'écrit jamais sans humain
        self.utilisateur = utilisateur
        self.date_ref = date_ref
        self.historique = []
        self.refs = {}          # "S12" -> ev_id
        self._rev = {}

    # ── identifiants courts de preuves ──
    def handle(self, ev_id: str | None) -> str:
        if not ev_id:
            return "[sans preuve]"
        if ev_id not in self._rev:
            h = f"S{len(self.refs) + 1}"
            self.refs[h], self._rev[ev_id] = ev_id, h
        return f"[{self._rev[ev_id]}]"

    def faits(self):
        return resoudre(self.con, self.policy)

    def resume_faits(self, faits) -> str:
        lignes = []
        for cle in sorted(faits):
            f = faits[cle]
            v = f.valeur if f.valeur is not None else "—"
            s = f"- {cle} = {v} [{f.etat}]"
            if f.retenu:
                s += f" {self.handle(f.retenu.ev_id)} ({f.retenu.acteur}, {f.retenu.date or 's.d.'})"
            if f.explication:
                s += f" ; {f.explication}"
            if f.alertes:
                s += " ; ALERTE : " + " | ".join(f.alertes)
            lignes.append(s)
        return "\n".join(lignes)

    # ── outils ──
    def outil(self, nom: str, args: dict, message: str, rep: Reponse) -> str:
        if nom == "detail_fait":
            return self._detail(args.get("cle", ""))
        if nom == "chercher_preuves":
            res = recherche.chercher(self.con, args.get("texte", ""), fichier=args.get("fichier") or None)
            if not res:
                return "aucune preuve trouvée"
            return "\n".join(
                f"{self.handle(r['ev_id'])} {r['path'].rsplit('/', 1)[-1]} — {r['repere']} — {r['date_fait'] or 's.d.'}"
                f" — {r['auteur'] or ''}{' [' + r['source_class'] + ']' if r['source_class'] != 'officiel' else ''}"
                f"{' [DOUBLON de ' + r['duplicate_of'] + ']' if r['duplicate_of'] else ''} : {r['texte'][:300]}"
                for r in res)
        if nom == "lire_preuve":
            ev = self.refs.get(args.get("source", "").strip("[] "))
            r = recherche.lire(self.con, ev) if ev else None
            if not r:
                return "identifiant inconnu : utilise un [S<n>] donné par un outil"
            p = r["preuve"]
            ctx = "\n".join(f"  {v['repere']} {v['auteur'] or ''} : {v['texte']}" for v in r["voisins"])
            return f"{self.handle(ev)} {p['path']} — {p['repere']} — {p['date_fait'] or 's.d.'}\n{p['texte']}\nContexte :\n{ctx}"
        if nom == "proposer_mise_a_jour":
            return self._mise_a_jour(args, message, rep)
        return f"outil inconnu : {nom}"

    def _detail(self, cle: str) -> str:
        faits = self.faits()
        cles = [c for c in faits if c == cle] or [c for c in faits if c.startswith(cle)]
        if not cles:
            proches = difflib.get_close_matches(cle, list(faits), n=5, cutoff=0.4)
            return f"clé inconnue « {cle} ». Clés proches : {', '.join(proches) or 'aucune'}"
        out = []
        for c in sorted(cles)[:6]:
            f = faits[c]
            out.append(f"{c} = {f.valeur if f.valeur is not None else '—'} [{f.etat}]")
            out += self._synthese(f)
            if f.explication:
                out.append(f"  calcul : {f.explication}")
            for al in f.alertes:
                out.append(f"  ALERTE : {al}")
            out.append("  historique complet (date | statut | acteur (autorité) | valeur | verdict) :")
            for a in f.historique:
                out.append(f"  {a.date or 's.d.'} | {a.statut} | {a.acteur} ({a.niveau}) | {a.valeur} | {a.verdict}"
                           f"{' — ' + a.raison if a.raison and a.verdict != 'retenu' else ''} {self.handle(a.ev_id)}"
                           f"{' — note : ' + a.note if a.note else ''}")
        return "\n".join(out)

    def _synthese(self, f) -> list:
        """Lecture déjà faite par le code : le modèle n'a qu'à la reformuler."""
        def qui(a):
            return f"{a.acteur} le {a.date or 's.d.'} {self.handle(a.ev_id)}"
        out = []
        if f.proposee_par:
            out.append("  PROPOSÉ PAR : " + " ; ".join(qui(a) for a in f.proposee_par))
        if f.decisions:
            out.append(f"  PREMIÈRE DÉCISION : {qui(f.decisions[0])}")
            if len(f.decisions) > 1:
                out.append("  CONFIRMÉ ENSUITE : " + " ; ".join(qui(a) for a in f.decisions[1:]))
        porteurs = [a for a in f.historique if a.valeur == f.valeur and a.recevable
                    and a.statut in ("DECISION", "VALIDATION", "DOCUMENT")]
        if f.valeur is not None and porteurs:
            out.append(f"  EN VIGUEUR DEPUIS : {qui(porteurs[0])}")
        if f.validations:
            out.append("  VALIDÉ PAR : " + " ; ".join(qui(a) for a in f.validations))
        ecartes = {}
        for a in f.historique:
            if a.verdict not in ("retenu", "concordant", "proposition adoptée", "reflet cohérent", "déclaration confirmée"):
                ecartes.setdefault(a.verdict, []).append(f"{a.acteur} ({a.valeur}) {self.handle(a.ev_id)}")
        for verdict, lst in ecartes.items():
            out.append(f"  {verdict.upper()} : " + " ; ".join(lst))
        return out

    def _mise_a_jour(self, args: dict, message: str, rep: Reponse) -> str:
        try:
            prop = mise_a_jour.preparer(self.con, args.get("cle", ""), args.get("valeur", ""), args.get("statut"),
                                        args.get("acteur") or None, args.get("date_fait") or None,
                                        args.get("preuve") or None, args.get("note") or None, policy=self.policy,
                                        utilisateur=self.utilisateur)
        except AssertionInvalide as e:
            cles = sorted({f.motif for f in FAMILLES})
            return f"proposition invalide : {e}. Motifs de clés valides : {', '.join(cles)}"
        decision = self.confirmer(prop)
        if decision is None:   # interface graphique : l'utilisateur confirmera avec un bouton, plus tard
            rep.en_attente.append((prop, message))
            return (f"EN ATTENTE : proposition affichée à l'utilisateur, qui l'enregistrera ou la rejettera lui-même "
                    f"avec un bouton. Ne dis PAS qu'elle est enregistrée. Proposition : {prop.resume()}"
                    + (f" Avertissements : {' | '.join(prop.avertissements)}" if prop.avertissements else "")
                    + (f" Impacts si enregistrée : {' | '.join(prop.impacts)}" if prop.impacts else ""))
        if not decision:
            return f"NON ENREGISTRÉ : l'utilisateur a refusé. Proposition : {prop.resume()}"
        aid = mise_a_jour.appliquer(self.con, prop, self.utilisateur, message)
        rep.mises_a_jour.append((aid, prop))
        av = (" Avertissements : " + " | ".join(prop.avertissements)) if prop.avertissements else ""
        imp = (" Impacts : " + " | ".join(prop.impacts)) if prop.impacts else ""
        return f"ENREGISTRÉ (assertion #{aid}) : {prop.resume()}.{av}{imp}"

    def enregistrer(self, prop, message: str) -> int:
        """Confirmation donnée dans l'interface (bouton) pour une proposition en attente."""
        return mise_a_jour.appliquer(self.con, prop, self.utilisateur, message)

    # ── boucle de l'agent ──
    def repondre(self, message: str) -> Reponse:
        rep = Reponse("")
        system = SYSTEM.format(date_ref=self.date_ref, faits=self.resume_faits(self.faits()))
        msgs = [{"role": "system", "content": system}] + self.historique + [{"role": "user", "content": message}]
        relance = False
        for _ in range(MAX_TOURS):
            r = self.appel_llm(msgs)
            m = r.choices[0].message
            if not m.tool_calls:
                if not rep.outils and not relance:
                    # Réponse sans consultation de la mémoire : on redemande une fois avec les outils.
                    relance = True
                    msgs.append({"role": "assistant", "content": m.content or ""})
                    msgs.append({"role": "user", "content": "Vérifie d'abord avec detail_fait (et chercher_preuves si "
                                 "besoin) qui a proposé, décidé ou validé, puis réponds selon la structure demandée."})
                    continue
                rep.texte = m.content or ""
                break
            msgs.append({"role": "assistant", "content": m.content or "",
                         "tool_calls": [{"id": t.id, "type": "function",
                                         "function": {"name": t.function.name, "arguments": t.function.arguments}}
                                        for t in m.tool_calls]})
            for t in m.tool_calls:
                try:
                    args = json.loads(t.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                res = self.outil(t.function.name, args, message, rep)
                rep.outils.append((t.function.name, args))
                msgs.append({"role": "tool", "tool_call_id": t.id, "content": res})
        else:
            rep.texte = "Je n'ai pas pu conclure en un nombre raisonnable d'étapes."
            rep.avertissements.append("limite d'appels d'outils atteinte")
        brut = rep.texte
        self._citer(rep)
        # L'historique garde les identifiants [S..] : sinon le modèle imite les [1] affichés et ses citations
        # suivantes ne sont plus vérifiables.
        self.historique += [{"role": "user", "content": message}, {"role": "assistant", "content": brut}]
        return rep

    def _citer(self, rep: Reponse):
        """[S12] → [1] + liste des sources ; identifiants inventés signalés."""
        numeros = {}

        def remplace(m):
            h = m.group(1)
            if h not in self.refs:
                rep.avertissements.append(f"référence inventée par le modèle : [{h}]")
                return "[réf. inconnue]"
            if h not in numeros:
                numeros[h] = len(numeros) + 1
                ev = self.refs[h]
                row = self.con.execute("SELECT e.repere, e.date_fait, e.auteur, f.path FROM evidence e JOIN files f "
                                       "USING(file_id) WHERE e.ev_id=?", (ev,)).fetchone()
                rep.sources.append((numeros[h], row["path"], row["repere"], row["date_fait"], row["auteur"], ev))
            return f"[{numeros[h]}]"

        # « [S1, S2] » ou « [S1][S2] » → un identifiant par crochet, puis numérotation
        rep.texte = re.sub(r"\[((?:S\d+\s*[,;]\s*)+S\d+)\]",
                           lambda m: "".join(f"[{x.strip()}]" for x in re.split(r"[,;]", m.group(1))), rep.texte)
        rep.texte = re.sub(r"\[(S\d+)\]", remplace, rep.texte)
        # identifiant cité sans crochets, ex. « (S54) » : converti s'il existe, sinon laissé tel quel
        rep.texte = re.sub(r"(?<![\w\[])(S\d+)(?![\w\]])",
                           lambda m: remplace(m) if m.group(1) in self.refs else m.group(0), rep.texte)
        if not rep.sources and not rep.mises_a_jour and not rep.en_attente:
            rep.avertissements.append("réponse sans source citée")


def afficher(rep: Reponse) -> str:
    out = [rep.texte.strip()]
    if rep.sources:
        out.append("\nSources :")
        for n, p, r, d, a, _ in rep.sources:
            r = "courriel" if r.startswith("courriel du") else r
            a = re.sub(r"\s*<[^>]+>", "", a or "")
            out.append(f"  [{n}] {p} — {r} ({d or 's.d.'}{', ' + a if a else ''})")
    for aid, prop in rep.mises_a_jour:
        out.append(f"\n✔ enregistré #{aid} : {prop.resume()}")
    for av in rep.avertissements:
        out.append(f"⚠ {av}")
    return "\n".join(out)


def confirmer_terminal(prop: mise_a_jour.Proposition) -> bool:
    print("\n┌─ Mise à jour proposée ─────────────────────────────")
    print(f"│ {prop.resume()}")
    for av in prop.avertissements:
        print(f"│ ⚠ {av}")
    for imp in prop.impacts:
        print(f"│ → {imp}")
    print("└────────────────────────────────────────────────────")
    return input("Enregistrer ? [o/N] ").strip().lower() in ("o", "oui", "y", "yes")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--utilisateur", default="utilisateur")
    a = ap.parse_args()
    s = Session(confirmer=confirmer_terminal, utilisateur=a.utilisateur)
    print("Mémoire NOVA — posez une question ou apportez une information (Ctrl+C pour quitter).")
    while True:
        try:
            q = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q:
            print(afficher(s.repondre(q)))


if __name__ == "__main__":
    main()
