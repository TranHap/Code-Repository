"""Règles additionnelles du résolveur, activées par nom dans policy.toml ([regles] actives).

Ajouter une règle = écrire une fonction décorée @regle("nom") ; le cœur du résolveur ne change pas.
Signature : f(faits: dict[cle, Fait], policy) -> None (ajoute alertes ou faits calculés).
"""
REGLES = {}


def regle(nom):
    def deco(fn):
        REGLES[nom] = fn
        return fn
    return deco


def _fait_calcule(cle, valeur, explication, sources):
    from .resolver import Fait
    return Fait(cle, valeur, "calcule", None, [], [], explication, [s for s in sources if s])


def _fmt(n) -> str:
    return f"{int(float(n)):,}".replace(",", " ") + " $"


@regle("coherence_reflet")
def coherence_reflet(faits, policy):
    """Un reflet (plan, registre, rapport) lié à une clé doit être cohérent avec l'état actuel de celle-ci."""
    for f in list(faits.values()):
        for a in f.historique:
            if a.statut != "REFLET" or not a.lien or a.valeur not in policy.coherence:
                continue
            lie = faits.get(a.lien)
            if not lie or lie.valeur is None:
                continue
            attendus = policy.coherence[a.valeur]
            if lie.valeur not in attendus:
                src = lie.retenu.court() if lie.retenu else lie.cle
                f.alertes.append(f"reflet périmé : {a.ref} indique {a.valeur} ({(a.source or '').rsplit('/', 1)[-1]}, "
                                 f"{a.date or 's.d.'}) mais {a.lien} = {lie.valeur} ({src})")
                if a.verdict in ("retenu", "reflet cohérent"):
                    a.raison = f"contredit par {a.lien} = {lie.valeur}"


@regle("budget_autorise")
def budget_autorise(faits, policy):
    """Montant autorisé = plafond contractuel + CR approuvés ; les CR non approuvés sont listés à part."""
    plafond = faits.get(policy.budget.get("plafond", "contrat:plafond"))
    if not plafond or plafond.valeur is None:
        return
    total, parts, exclus, sources = float(plafond.valeur), [f"{_fmt(plafond.valeur)} (plafond)"], [], [plafond.retenu]
    crs = sorted({c.split(":")[1] for c in faits if c.startswith("cr:") and c.endswith(":statut")})
    for cr in crs:
        st, mt = faits[f"cr:{cr}:statut"], faits.get(f"cr:{cr}:montant")
        montant = (mt.valeur if mt and mt.valeur else
                   next((a.valeur for a in (mt.historique if mt else [])), None))
        if st.valeur == policy.budget.get("statut_cr_approuve", "APPROUVE") and mt and mt.valeur:
            total += float(mt.valeur)
            parts.append(f"{_fmt(mt.valeur)} ({cr} approuvé)")
            sources += [st.retenu, mt.retenu]
        else:
            exclus.append(f"{cr} {('(' + _fmt(montant) + ') ') if montant else ''}: {st.valeur or 'non décidé'}")
    expl = " + ".join(parts) + f" = {_fmt(total)}"
    if exclus:
        expl += " ; exclus : " + ", ".join(exclus)
    faits["budget:autorise"] = _fait_calcule("budget:autorise", str(int(total)), expl, sources)


@regle("facture_cr_non_approuve")
def facture_cr_non_approuve(faits, policy):
    """Une ligne de facture qui référence un CR non approuvé est contestée (contrat : CR approuvé avant facturation)."""
    approuve = policy.budget.get("statut_cr_approuve", "APPROUVE")
    par_facture = {}
    for cle, f in faits.items():
        parts = cle.split(":")
        if len(parts) == 4 and parts[0] == "facture" and parts[2] == "ligne" and parts[3].startswith("CR-") and f.valeur:
            st = faits.get(f"cr:{parts[3]}:statut")
            if st is None or st.valeur != approuve:
                par_facture.setdefault(parts[1], []).append((parts[3], f, st))
    for inv, lignes in par_facture.items():
        total = sum(float(f.valeur) for _, f, _ in lignes)
        details = []
        for cr, f, st in lignes:
            fact = faits.get(f"cr:{cr}:facturable")
            details.append(f"{cr} {_fmt(f.valeur)} : statut {st.valeur if st else 'inconnu'}"
                           + (f", facturable = {fact.valeur} ({fact.retenu.court()})" if fact and fact.retenu else ""))
        expl = "; ".join(details)
        tot = faits.get(f"facture:{inv}:total")
        if tot and tot.valeur:
            reste = float(tot.valeur) - total
            expl += (f" ; montant non contesté : {_fmt(reste)} (autres lignes, à traiter selon le processus normal)"
                     f" ; traitement : retirer la ligne contestée (facture corrigée ou note de crédit de {_fmt(total)})")
        regle = faits.get("contrat:regle_changement")
        if regle and regle.valeur:
            expl += f" ; règle contractuelle : {regle.valeur}"
        faits[f"facture:{inv}:montant_conteste"] = _fait_calcule(
            f"facture:{inv}:montant_conteste", str(int(total)), expl,
            [f.retenu for _, f, _ in lignes] + [st.retenu for _, _, st in lignes if st])
        if f"facture:{inv}:statut" in faits:
            faits[f"facture:{inv}:statut"].alertes.append(f"{_fmt(total)} facturés sans CR approuvé — {expl}")


@regle("conditions_golive")
def conditions_golive(faits, policy):
    """État de chaque condition de go-live d'après la clé liée, puis go-live prêt ou non."""
    conds = [f for c, f in faits.items() if c.startswith("golive:condition:") and c.count(":") == 2 and f.valeur]
    if not conds:
        return
    ouvertes = []
    for f in conds:
        lien = f.retenu.lien if f.retenu else None
        lie = faits.get(lien) if lien else None
        if lie is None or lie.valeur is None:
            etat, src = "INCONNU (aucune clé liée résolue)", None
        elif lie.valeur in policy.conditions_remplies:
            etat, src = f"REMPLIE ({lien} = {lie.valeur})", lie.retenu
        else:
            etat, src = f"NON REMPLIE ({lien} = {lie.valeur})", lie.retenu
        if not etat.startswith("REMPLIE"):
            ouvertes.append(f.cle.split(":")[-1])
        faits[f"{f.cle}:etat"] = _fait_calcule(f"{f.cle}:etat", etat, f"{f.valeur} → {etat}", [f.retenu, src])
    pret = "NON" if ouvertes else "OUI"
    faits["golive:pret"] = _fait_calcule(
        "golive:pret", pret, f"{len(conds) - len(ouvertes)}/{len(conds)} conditions remplies"
        + (f" ; ouvertes : {', '.join(sorted(ouvertes))}" if ouvertes else ""), [f.retenu for f in conds])
