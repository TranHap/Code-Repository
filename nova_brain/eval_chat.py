"""Évaluation de l'agent réel (LLM) sur les 10 questions du défi, dans une même conversation.

    python -m nova_brain.eval_chat

Chaque réponse est vérifiée par des mots-clés attendus (réponse ET nuance) et doit citer des sources.
Le rapport complet (questions, réponses, sources, vérifications) est écrit dans rendu/06_Eval/.
Aucune mise à jour n'est enregistrée (confirmation toujours refusée).
"""
import sys
import time
import unicodedata

from . import config
from .chat import Session, afficher

QUESTIONS = [
    ("Q01", "Quelle est la date de mise en production actuellement approuvée, et avec quelle réserve?",
     [["22 octobre", "2026-10-22"], ["sec-210"], ["acc-303"], ["runbook"]]),
    ("Q02", "Pourquoi la date a-t-elle changé, et quel est l'état actuel de la cause initiale?",
     [["int-101", "connecteur"], ["ferme", "resolu"]]),
    ("Q03", "Qui a approuvé le changement et quand? Distinguez proposition et approbation.",
     [["julien"], ["10 septembre", "2026-09-10"], ["comite"]]),
    ("Q04", "Qui est responsable du projet et depuis quand?",
     [["nicolas"], ["16 septembre", "2026-09-16"]]),
    ("Q05", "Quel est le montant contractuel autorisé et comment se calcule-t-il?",
     [["204 000", "204000"], ["180 000", "180000"], ["cr-01"]]),
    ("Q06", "Quel problème présente INV-003? Précisez le montant concerné et le traitement à prévoir.",
     [["18 000", "18000"], ["cr-04"], ["credit", "corrig", "retir", "bloqu", "contest", "approbation", "ne pas payer"]]),
    ("Q07", "Où les données de production doivent-elles être hébergées? Quelle preuve confirme la mise en œuvre?",
     [["canada central"], ["verifi", "m03", "27 aout", "2026-08-27"]]),
    ("Q08", "La sécurité est-elle acceptée? Distinguez livraison et validation.",
     [["en validation", "en_validation"], ["livr"], ["sophie"]]),
    ("Q09", "L'accessibilité est-elle complétée? Identifiez ce qui reste à corriger.",
     [["acc-303"], ["ouvert"], ["enregistrer", "modale", "focus", "clavier"]]),
    ("Q10", "Quelles sont les trois conditions de go-live? Précisez les travaux manquants du runbook à partir de sa capture.",
     [["sec-210"], ["acc-303"], ["rollback", "retour arriere"], ["validation fonctionnelle", "post-deploiement"]]),
]


def norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    s = Session(confirmer=lambda p: False, utilisateur="evaluation")
    out_dir = config.ROOT / "rendu" / "06_Eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M")
    rapport = [f"# Évaluation de l'agent — {stamp}\n", f"Modèle : {config.TEXT_MODEL} · politique par défaut\n"]
    total = 0
    for qid, q, attendus in QUESTIONS:
        t = time.time()
        try:
            r = s.repondre(q)
            texte = afficher(r)
        except Exception as e:   # quota, réseau : noté, l'évaluation continue
            r, texte = None, f"ERREUR : {type(e).__name__}: {e}"
        n = norm(r.texte if r else "")
        manquants = [" / ".join(g) for g in attendus if not any(norm(x) in n for x in g)]
        ok = r is not None and not manquants and bool(r.sources)
        total += ok
        ligne = f"{qid} {'OK ' if ok else 'KO '} {time.time() - t:5.1f}s  sources={len(r.sources) if r else 0}" \
                + (f"  manque : {manquants}" if manquants else "")
        print(ligne, flush=True)
        rapport += [f"\n## {qid} — {q}\n", f"`{ligne}`\n", f"Outils : {[o[0] for o in r.outils] if r else []}\n",
                    "```text", texte, "```"]
    rapport.insert(2, f"**Score mots-clés : {total}/{len(QUESTIONS)}**\n")
    path = out_dir / f"eval_chat_{stamp}.md"
    path.write_text("\n".join(rapport), encoding="utf-8")
    print(f"\n{total}/{len(QUESTIONS)} — rapport : {path}")


if __name__ == "__main__":
    main()
