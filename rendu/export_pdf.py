"""Exporte les livrables Markdown en PDF (Chrome/Edge headless).

    python rendu/export_pdf.py            # brief (1 page, portrait) + actions (paysage)
"""
import re
import subprocess
import sys
from pathlib import Path

import markdown

ICI = Path(__file__).resolve().parent
NAVIGATEURS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
               r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]

CSS = """
@page { size: PAGE; margin: MARGE; }
body { font-family: "Times New Roman", Times, serif; font-size: TAILLE; line-height: 1.2; color: #000; margin: 0; }
h1 { font-size: 15pt; margin: 0 0 4px; }
h2 { font-size: 11.5pt; margin: 9px 0 2px; page-break-after: avoid; }
h3 { font-size: 10.5pt; margin: 6px 0 2px; page-break-after: avoid; }
p { margin: 2px 0; text-align: justify; }
blockquote { margin: 4px 0; padding-left: 8px; border-left: 0.6pt solid #000; }
table { border-collapse: collapse; width: 100%; margin: 4px 0; }
tr { page-break-inside: avoid; }
th, td { border: 0.6pt solid #000; padding: 2px 4px; vertical-align: top; text-align: left; }
th { font-weight: bold; }
ol, ul { margin: 2px 0; padding-left: 18px; } li { margin: 1px 0; }
hr { border: 0; border-top: 0.6pt solid #000; margin: 7px 0 3px; }
code { font-family: "Courier New", monospace; font-size: 0.92em; }
pre { margin: 3px 0 3px 12px; }
small { font-size: 9pt; }
a { color: #000; text-decoration: none; }
"""

DOCUMENTS = [
    # (source, titre de l'onglet, format de page, marges, taille du texte)
    ("01_Brief_reprise.md", "Projet NOVA : brief de reprise", "Letter", "10mm 14mm", "9.6pt"),
    ("02_Memoire/actions.md", "Projet NOVA : actions restantes", "Letter landscape", "11mm 12mm", "9.4pt"),
    ("02_Memoire/contradictions.md", "Projet NOVA : décisions et contradictions", "Letter landscape", "11mm 12mm", "9.4pt"),
    ("03_Reponses_Q01-Q10.md", "Projet NOVA : réponses Q01 à Q10", "Letter", "12mm 13mm", "9.6pt"),
    ("05_Mode_emploi.md", "Projet NOVA : mode d'emploi", "Letter", "14mm 16mm", "10.5pt"),
]


def exporter(source: str, titre: str, page: str, marge: str, taille: str, nav: str) -> Path:
    md = ICI / source
    html, pdf = md.with_suffix(".html"), md.with_suffix(".pdf")
    corps = markdown.markdown(md.read_text(encoding="utf-8"), extensions=["tables", "nl2br", "fenced_code"])
    corps = corps.replace("« ", "«\u00a0").replace(" »", "\u00a0»")   # guillemets jamais séparés de leur texte
    corps = re.sub(r"<a [^>]*>(.*?)</a>", r"\1", corps)                 # liens relatifs inutiles sur papier
    style = CSS.replace("PAGE", page).replace("MARGE", marge).replace("TAILLE", taille)
    html.write_text(f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>{titre}</title>'
                    f"<style>{style}</style></head><body>{corps}</body></html>", encoding="utf-8")
    subprocess.run([nav, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", html.as_uri()], check=True, capture_output=True, timeout=60)
    html.unlink()
    return pdf


def main():
    nav = next((n for n in NAVIGATEURS if Path(n).exists()), None)
    if not nav:
        sys.exit("Chrome ou Edge introuvable.")
    for doc in DOCUMENTS:
        print(f"PDF : {exporter(*doc, nav)}")


if __name__ == "__main__":
    main()
