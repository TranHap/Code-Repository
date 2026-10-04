"""Vue d'ensemble de la mémoire : lots, fichiers, classes de source, preuves, événements.

    python -m nova_brain.stats [--file CHEMIN]   # --file : affiche les preuves d'un fichier
"""
import argparse
import sys

from . import db


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    a = ap.parse_args()
    con = db.connect()

    if a.file:
        for e in con.execute("""SELECT e.* FROM evidence e JOIN files f USING(file_id)
                                WHERE f.path LIKE ? ORDER BY e.rowid""", (f"%{a.file}%",)):
            print(f"[{e['repere']}] {e['date_fait'] or '-'} {e['auteur'] or ''}\n    {e['texte'][:300]}")
        return

    print("LOTS")
    for b in con.execute("SELECT * FROM batches"):
        print(f"  {b['batch_id']:>3} {b['kind']:9s} {b['created_at']}  {b['label']}")
    print("\nFICHIERS (version courante)")
    for f in sorted(db.current_files(con), key=lambda f: f["path"]):
        n = con.execute("SELECT COUNT(*) FROM evidence WHERE file_id=?", (f["file_id"],)).fetchone()[0]
        pj = {r[0].split("/")[-1] for r in con.execute("SELECT email_path FROM attachments WHERE file_path=?", (f["path"],))}
        flags = " ".join(x for x in (
            f"[{f['status']}]" if f["status"] != "ok" else "",
            f"PJ de {', '.join(sorted(pj))}" if pj else "",
            f"DOUBLON de {f['duplicate_of'].split('/')[-1]}" if f["duplicate_of"] else "") if x)
        print(f"  {f['source_class']:21s} {f['doc_date'] or '-':16s} {n:>3} u.  {f['path']}  {flags}")
    print("\nTOTAUX")
    for row in con.execute("SELECT unit, COUNT(*) n FROM evidence GROUP BY unit"):
        print(f"  preuves/{row['unit']}: {row['n']}")
    print(f"  événements: {con.execute('SELECT COUNT(*) FROM events').fetchone()[0]}")


if __name__ == "__main__":
    main()
