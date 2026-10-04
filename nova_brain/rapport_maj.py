"""Rapport de mise à jour : état actuel comparé à un snapshot (par défaut la baseline du 30 septembre).

    python -m nova_brain.rapport_maj [--depuis baseline]

Distingue, pour chaque information nouvelle : l'état du problème, la décision antérieure (maintenue ou
remplacée) et la nouvelle proposition. N'infère aucune approbation et ne ferme aucune condition :
tout vient du résolveur, avec la preuve de chaque élément. La baseline n'est jamais modifiée :
elle est recalculée à partir des lots qu'elle contenait.
"""
import argparse
import json
import re
import sys
import time

from . import config, db
from . import policy as pol
from .resolver import diff, resoudre

SANS_EFFET = {
    "proposition non retenue": "Nouvelles propositions — décision antérieure maintenue",
    "proposition en attente": "Nouvelles propositions — aucune décision documentée",
    "déclaration non confirmée": "Déclarations non confirmées",
    "non recevable": "Affirmations non recevables (rôle insuffisant)",
    "écarté": "Décisions d'autorité insuffisante",
    "en conflit": "Conflits à arbitrer",
    "concordant": "Confirmations (même valeur qu'avant)",
    "déclaration confirmée": "Confirmations (même valeur qu'avant)",
    "reflet cohérent": "Confirmations (même valeur qu'avant)",
}


def _preuve(con, a) -> str:
    if not a or not a.ev_id:
        return "sans preuve"
    r = con.execute("SELECT e.repere, f.path FROM evidence e JOIN files f USING(file_id) WHERE e.ev_id=?",
                    (a.ev_id,)).fetchone()
    if not r:
        return a.ev_id
    rep = r["repere"]
    if rep.startswith("courriel du"):   # « courriel du Thu, 01 Oct 2026 10:12:00 -0400, de X <x@y> » → « courriel »
        rep = "courriel"
    return f"`{r['path']}` — {rep}"


def _v(f):
    return "—" if f is None or f.valeur is None else f"{f.valeur}" + ("" if f.etat in ("retenu", "calcule") else f" [{f.etat}]")


def exporter(faits) -> dict:
    return {c: {"valeur": f.valeur, "etat": f.etat, "alertes": f.alertes, "explication": f.explication,
                "retenu": f.retenu.court() if f.retenu else None} for c, f in sorted(faits.items())}


def rapport(con, depuis: str = "baseline", policy=None) -> tuple[str, dict, dict]:
    policy = policy or pol.load()
    b0 = db.snapshot(con, depuis)
    avant, apres = resoudre(con, policy, batch_max=b0), resoudre(con, policy)
    lots = con.execute("SELECT * FROM batches WHERE batch_id > ? ORDER BY batch_id", (b0,)).fetchall()
    nouveaux = {r[0] for r in con.execute("SELECT assertion_id FROM assertions WHERE batch_id > ?", (b0,))}
    changes = diff(avant, apres)
    L = [f"# Mise à jour de la mémoire NOVA — état actuel comparé à « {depuis} »\n",
         f"Généré le {time.strftime('%Y-%m-%d %H:%M')} · politique {policy.version} · baseline = lots ≤ {b0} "
         "(conservée : recalculable à tout moment)\n",
         "## Lots intégrés depuis la baseline\n"]
    L += [f"- lot {b['batch_id']} · {b['kind']} · {b['created_at']} · {b['label']}" for b in lots] or ["- aucun"]

    # 1. Synthèse
    L += ["\n## 1. Synthèse\n", "| | Baseline | Actuel |", "|---|---|---|"]
    for cle, lib in (("projet:date_golive", "Date de mise en production"), ("golive:pret", "Go-live prêt"),
                     ("role:charge_de_projet", "Chargé de projet"), ("budget:autorise", "Montant autorisé")):
        L.append(f"| {lib} | {_v(avant.get(cle))} | {_v(apres.get(cle))} |")
    L.append(f"\n{len(changes)} fait(s) modifié(s) ; {len(nouveaux)} nouvelle(s) assertion(s).")

    # 2. Faits modifiés
    L += ["\n## 2. Faits modifiés (état du problème)\n"]
    if not changes:
        L.append("Aucun fait n'a changé : les nouvelles informations sont conservées dans l'historique (voir §3).")
    else:
        L += ["| Clé | Baseline | Actuel | Ce qui l'établit | Nature |", "|---|---|---|---|---|"]
        for c in changes:
            cle = c.split(" : ", 1)[0]
            f = apres.get(cle)
            src = (_preuve(con, f.retenu) if f and f.retenu else (f.explication[:120] if f and f.explication else "—"))
            nature = (f"{f.retenu.statut} · {f.retenu.acteur} · {f.retenu.date}" if f and f.retenu
                      else ("calculé" if f and f.etat == "calcule" else "—"))
            L.append(f"| `{cle}` | {_v(avant.get(cle))} | {_v(f)} | {src} | {nature} |")

    # 3. Nouvelles informations sans effet sur l'état
    groupes = {}
    for cle, f in apres.items():
        for a in f.historique:
            if a.id in nouveaux and a.verdict in SANS_EFFET:
                groupes.setdefault(SANS_EFFET[a.verdict], []).append((cle, f, a))
    L += ["\n## 3. Informations nouvelles qui ne changent pas l'état\n"]
    if not groupes:
        L.append("Aucune.")
    for titre, items in groupes.items():
        L.append(f"\n**{titre}**\n")
        for cle, f, a in items:
            maintenu = (f" → décision antérieure maintenue : **{f.valeur}** ({f.retenu.court()})"
                        if f.retenu and a.valeur != f.valeur else "")
            L.append(f"- `{cle}` = {a.valeur} · {a.statut} · {a.acteur} · {a.date or 's.d.'} — {a.raison or a.verdict}"
                     f"{maintenu}\n  - preuve : {_preuve(con, a)}")

    # 4. Conditions de go-live
    L += ["\n## 4. Conditions de go-live\n", "| Condition | Baseline | Actuel |", "|---|---|---|"]
    conds = sorted({c for c in list(avant) + list(apres) if c.startswith("golive:condition:") and c.endswith(":etat")})
    for c in conds:
        L.append(f"| {c.split(':')[2]} | {_v(avant.get(c))} | {_v(apres.get(c))} |")
    L.append("\nUne condition n'est remplie que si le ticket lié est fermé par le responsable du domaine ou le comité "
             "(policy.toml, [validation]) ; aucune n'est fermée par déduction.")

    # 5. Alertes
    # Une même contradiction dont seule la preuve citée a changé n'est ni nouvelle ni résolue.
    sans_src = lambda x: re.sub(r"\s*\([^()]*\)$", "", x)
    a0 = {(c, sans_src(x)) for c, f in avant.items() for x in f.alertes}
    a1 = {(c, sans_src(x)) for c, f in apres.items() for x in f.alertes}
    L += ["\n## 5. Contradictions et alertes\n"]
    L += [f"- NOUVELLE · `{c}` : {x}" for c, x in sorted(a1 - a0)]
    L += [f"- RÉSOLUE · `{c}` : {x}" for c, x in sorted(a0 - a1)]
    if a0 == a1:
        L.append(f"- inchangées ({len(a1)} alerte(s) en cours)")

    # 6. Actions touchées
    touchees = sorted({cle for cle, f in apres.items() if cle.startswith("action:")
                       and (any(a.id in nouveaux for a in f.historique) or _v(f) != _v(avant.get(cle)))})
    L += ["\n## 6. Actions touchées\n"]
    L += [f"- `{c}` : {_v(avant.get(c))} → {_v(apres.get(c))}" for c in touchees] or ["- aucune"]

    # 7. Garanties
    L += ["\n## 7. Ce que ce rapport ne fait pas\n",
          "- Aucune approbation n'est déduite : une proposition ou une déclaration reste telle quelle tant qu'aucune "
          "décision ou validation documentée ne la confirme (§3).",
          "- Aucune condition n'est fermée sans validation du responsable (§4).",
          f"- La baseline n'est pas modifiée : `python -m nova_brain.resolver` avec `batch_max={b0}` la reproduit."]
    return "\n".join(L), exporter(avant), exporter(apres)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--depuis", default="baseline")
    a = ap.parse_args()
    con = db.connect()
    md, f0, f1 = rapport(con, a.depuis)
    out = config.ROOT / "rendu" / "04_Mise_a_jour"
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M")
    (out / f"rapport_{a.depuis}_vs_actuel_{stamp}.md").write_text(md, encoding="utf-8")
    (out / f"faits_{a.depuis}.json").write_text(json.dumps(f0, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / f"faits_actuel_{stamp}.json").write_text(json.dumps(f1, ensure_ascii=False, indent=1), encoding="utf-8")
    print(md)
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
