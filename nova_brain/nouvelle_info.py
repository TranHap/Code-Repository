"""Intégrer une nouvelle information (dossier ou .zip) de bout en bout.

    python -m nova_brain.nouvelle_info <dossier|zip> [--partial] [--auto]

1. Ingestion (lot « upload ») : nouveaux fichiers, versions modifiées, doublons, pièces jointes.
2. Extraction LLM : propositions d'assertions → rendu/04_Mise_a_jour/propositions_lot<N>.csv
3. Relecture : sans --auto, on s'arrête ici. Ouvrir le CSV, mettre « non » dans la colonne garder pour rejeter,
   corriger au besoin, puis relancer :  python -m nova_brain.nouvelle_info --charger <csv>
   Avec --auto (démonstration), les propositions valides sont chargées directement.
4. Rapport : état actuel comparé à la baseline → rendu/04_Mise_a_jour/

La baseline (snapshot « baseline ») est créée automatiquement au premier passage si elle n'existe pas.
"""
import argparse
import sys
import time
from pathlib import Path

from . import assertions as asr
from . import config, db, extraction, ingest, rapport_maj

OUT = config.ROOT / "rendu" / "04_Mise_a_jour"


def assurer_baseline(con) -> int:
    try:
        return db.snapshot(con, "baseline")
    except ValueError:
        return db.creer_snapshot(con, "baseline", "État au 30 septembre 2026 09:00, avant la nouvelle information")


def integrer(con, source: Path, partial: bool, auto: bool, transcrire=None, appel_llm=None, out_dir: Path = OUT) -> dict:
    b0 = assurer_baseline(con)
    r = ingest.ingest(source, label=f"Nouvelle information : {source.name}", kind="upload",
                      transcrire=transcrire, partial=partial, con=con)
    rows = extraction.extraire(con, r["batch_id"], appel_llm=appel_llm)
    csv_path = extraction.ecrire_revue(rows, out_dir / f"propositions_lot{r['batch_id']}.csv")
    res = {"baseline": b0, "ingestion": r, "propositions": rows, "csv": csv_path, "charge": None}
    if auto:
        res["charge"] = asr.charger_csv(csv_path, con=con, kind="extraction")
    return res


def ecrire_rapport(con) -> Path:
    md, f0, f1 = rapport_maj.rapport(con, "baseline")
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"rapport_baseline_vs_actuel_{time.strftime('%Y%m%d-%H%M')}.md"
    p.write_text(md, encoding="utf-8")
    return p


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("source", nargs="?")
    ap.add_argument("--partial", action="store_true", help="le dossier ne contient que les nouveautés")
    ap.add_argument("--auto", action="store_true", help="charger les propositions valides sans relecture (démo)")
    ap.add_argument("--charger", help="charger un CSV de propositions relu")
    a = ap.parse_args()
    con = db.connect()
    if a.charger:
        r = asr.charger_csv(Path(a.charger), con=con, kind="extraction")
        print(f"Lot {r['batch_id']} : {r['count']} assertions chargées" if not r["skipped"] else "Déjà chargé.")
        print(f"Rapport : {ecrire_rapport(con)}")
        return
    if not a.source:
        ap.error("indiquer un dossier ou un .zip (ou --charger <csv>)")
    res = integrer(con, Path(a.source), a.partial, a.auto, transcrire=ingest.make_transcriber(True))
    ing, rows = res["ingestion"], res["propositions"]
    print(f"Lot {ing['batch_id']} : {len(ing['nouveau'])} nouveau(x), {len(ing['modifie'])} modifié(s), "
          f"{len(ing['inchange'])} inchangé(s), {len(ing['doublon'])} doublon(s)")
    ok = [r for r in rows if r.get("garder") == "oui"]
    print(f"{len(rows)} propositions, {len(ok)} valides → {res['csv']}")
    for r in rows:
        print(f"  {'✔' if r.get('garder') == 'oui' else '✘'} {r.get('cle')} = {r.get('valeur')} [{r.get('statut')}] "
              f"{r.get('acteur')} ({r.get('source', '').rsplit('/', 1)[-1]} {r.get('ancre')})"
              + (f" — {r['erreur']}" if r.get("erreur") else ""))
    if res["charge"]:
        print(f"Chargé : lot {res['charge']['batch_id']} ({res['charge']['count']} assertions)")
        print(f"Rapport : {ecrire_rapport(con)}")
    else:
        print("Relire le CSV puis : python -m nova_brain.nouvelle_info --charger", res["csv"])


if __name__ == "__main__":
    main()
