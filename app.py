"""Interface de la mémoire NOVA.

    streamlit run app.py            (base : nova_brain/data/memory.db, ou variable NOVA_DB)

Onglets : Chat · État du projet · Preuves · Chronologie · Nouvelle information · Baseline vs actuel.
Toute écriture dans la mémoire passe par un bouton de confirmation.
"""
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from nova_brain import assertions as asr
from nova_brain import config, db, ingest, nouvelle_info, rapport_maj, recherche
from nova_brain import policy as pol
from nova_brain.chat import DATE_REFERENCE, Session
from nova_brain.extraction import COLONNES_REVUE
from nova_brain.resolver import resoudre

st.set_page_config(page_title="Mémoire NOVA", page_icon="🧠", layout="wide")

st.markdown("""
<style>
/* Inspiration : LexieLingua (Phenomenon Studio) — cadre encre, canevas clair, accents violet / lime / lavande */
:root{
  --ink:#050609; --ink-2:#16181D; --canvas:#F8FAFA; --card:#FFFFFF; --line:#E6E8EC; --muted:#515157; --soft:#F1F2F4;
  --violet:#743EE0; --lavande:#C8B4E0; --lavande-bg:#F3EEFC; --lime:#CBFEA0; --lime-bg:#EEFFE0;
  --ok-fg:#2F6B12;   --ok-bg:#DFFCC6;
  --warn-fg:#92560B; --warn-bg:#FFF1C7;
  --bad-fg:#B4232A;  --bad-bg:#FFE1DF;
  --neu-fg:#515157;  --neu-bg:#EEF0F2;
  --info-fg:#5B2BC2; --info-bg:#EEE6FC;
  --shadow:0 1px 2px rgba(5,6,9,.04),0 6px 20px -8px rgba(5,6,9,.08);
}
.block-container{padding-top:3.2rem;padding-bottom:3rem;max-width:1280px;}
h1,h2,h3,h4{letter-spacing:-.01em;}

/* Barre latérale : cadre encre */
section[data-testid="stSidebar"] [data-testid="stMetric"]{background:var(--ink-2);border:1px solid #26292F;box-shadow:none;}
section[data-testid="stSidebar"] [data-testid="stMetricValue"]{color:#FFFFFF !important;}
section[data-testid="stSidebar"] [data-testid="stMetricLabel"] p{color:#9EA1AA !important;}
section[data-testid="stSidebar"] .stButton>button{background:var(--lime);color:var(--ink);border:none;}
section[data-testid="stSidebar"] .stButton>button:hover{background:#B8F57F;}
section[data-testid="stSidebar"] .stButton>button p{color:var(--ink) !important;}
.nova-brand{display:flex;align-items:center;gap:.65rem;margin:.2rem 0 .4rem;}
.nova-brand .mark{width:38px;height:38px;border-radius:11px;background:var(--lime);color:var(--ink);display:grid;place-items:center;
  font-size:1.2rem;font-weight:700;}
.nova-brand .nom{font-family:"Space Grotesk",sans-serif;font-weight:600;font-size:1.1rem;line-height:1.15;color:#fff;}
.nova-brand .sous{font-size:.75rem;color:#9EA1AA;}
.nova-side-row{display:flex;align-items:center;justify-content:space-between;gap:.5rem;font-size:.85rem;color:#C9CBD1;margin:.4rem 0;}

/* Hero : fond lime rayé, pastille encre, mot entouré */
.nova-hero{position:relative;overflow:hidden;border-radius:22px;padding:1.3rem 1.6rem;margin-bottom:1rem;
  background:repeating-linear-gradient(-58deg,transparent 0 34px,rgba(203,254,160,.6) 34px 44px,transparent 46px 70px),var(--lime-bg);
  display:flex;align-items:center;justify-content:space-between;gap:1.2rem;flex-wrap:wrap;border:1px solid #DDF6C6;}
.nova-hero .logo{display:inline-flex;align-items:center;gap:.5rem;background:var(--ink);color:#fff;border-radius:999px;
  padding:.55rem 1.15rem;font-family:"Space Grotesk",sans-serif;font-weight:600;font-size:1.15rem;}
.nova-hero .logo span{color:var(--lime);}
.nova-hero .tag{text-align:right;font-family:"Space Grotesk",sans-serif;font-size:1.2rem;line-height:1.35;color:#2A1460;max-width:560px;}
.nova-hero .tag em{font-style:normal;position:relative;white-space:nowrap;}
.nova-hero .tag em::after{content:"";position:absolute;inset:-5px -10px;border:1.5px solid var(--violet);border-radius:50%;
  transform:rotate(-3deg);opacity:.75;}
.nova-hero .meta{display:flex;gap:.5rem;justify-content:flex-end;margin-top:.6rem;flex-wrap:wrap;}

/* Onglets : barre de navigation encre en pilules */
.stTabs [data-baseweb="tab-list"]{background:var(--ink);padding:6px;border-radius:16px;gap:4px;border:none;}
.stTabs [data-baseweb="tab"]{height:auto;padding:.5rem 1.05rem;border-radius:999px;background:transparent;}
.stTabs [data-baseweb="tab"] p,.stTabs [data-baseweb="tab"] span{color:#B9BCC4;font-weight:500;font-size:.9rem;}
.stTabs [data-baseweb="tab"]:hover p,.stTabs [data-baseweb="tab"]:hover span{color:#FFFFFF;}
.stTabs [aria-selected="true"]{background:#FFFFFF !important;}
.stTabs [aria-selected="true"] p,.stTabs [aria-selected="true"] span{color:var(--ink) !important;font-weight:600;}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none;}
.stTabs [data-baseweb="tab-panel"]{padding-top:1.1rem;}

/* Titres de section ✦ */
.nova-section{display:flex;align-items:center;gap:.5rem;font-family:"Space Grotesk",sans-serif;font-weight:600;
  font-size:1.08rem;color:var(--ink);margin:1.3rem 0 .5rem;}
.nova-section .spark{color:var(--violet);}

/* Cartes KPI (st.metric) */
[data-testid="stMetric"]{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:.9rem 1.05rem;box-shadow:var(--shadow);}
[data-testid="stMetricLabel"] p{color:var(--muted);font-weight:500;font-size:.8rem;}
[data-testid="stMetricValue"]{color:var(--ink);font-family:"Space Grotesk",sans-serif;font-weight:600;font-size:1.4rem;line-height:1.25;
  white-space:normal;overflow-wrap:anywhere;}
[data-testid="stMetricValue"] > div{white-space:normal;overflow:visible;text-overflow:clip;}

/* Chat */
.st-key-accueil{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:1.1rem;box-shadow:var(--shadow);}
.nova-empty{text-align:center;padding:.4rem 1rem .6rem;}
.nova-empty h4{font-family:"Space Grotesk",sans-serif;font-weight:600;margin:0 0 .3rem;font-size:1.05rem;padding:0;}
.nova-empty h4 span{color:var(--violet);}
.nova-empty p{color:var(--muted);font-size:.88rem;margin:0 auto;max-width:640px;}
.st-key-accueil .stButton>button{background:var(--soft);border:1px solid transparent;min-height:76px;justify-content:flex-start;
  text-align:left;font-weight:500;color:var(--ink);height:100%;min-height:96px;align-items:flex-start;padding:.8rem .9rem;}
.st-key-accueil .stButton>button p{font-size:.86rem;line-height:1.4;}
.st-key-accueil [data-testid="stColumn"]>div,.st-key-accueil .stButton{height:100%;}
.st-key-accueil .stButton>button:hover{background:var(--lavande-bg);border-color:var(--lavande);color:var(--ink);}
div[data-testid="stChatMessage"]{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:.9rem 1rem;box-shadow:var(--shadow);}
div[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]){background:var(--lavande-bg);border-color:#E2D6F6;box-shadow:none;}

/* Carte de mise à jour proposée (en-tête violet, comme « Practice Pronunciation ») */
[class*="st-key-pending"]{background:var(--card);border:1px solid var(--lavande);border-radius:18px;box-shadow:var(--shadow);
  padding:0 1rem 1rem;overflow:hidden;}
.nova-pending-head{display:flex;justify-content:space-between;align-items:center;margin:0 -1rem .3rem;padding:.5rem 1rem;
  background:var(--violet);color:#fff;font-size:.82rem;font-weight:600;}

/* Conteneurs, alertes, tableaux, expanders */
div[data-testid="stVerticalBlockBorderWrapper"]{border-radius:18px !important;}
.stAlert{border-radius:14px;}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--card);}
[data-testid="stExpander"] details{border-radius:14px;background:var(--card);}
[data-testid="stFileUploaderDropzone"]{border-radius:16px;background:repeating-linear-gradient(transparent 0 27px,#E3E9F8 27px 28px),#FBFCFF;}

.stMultiSelect [data-baseweb="tag"]{background:var(--info-bg) !important;border-radius:999px;}
.stMultiSelect [data-baseweb="tag"] span,.stMultiSelect [data-baseweb="tag"] svg{color:var(--info-fg) !important;}

/* Boutons */
.stButton>button,.stDownloadButton>button{border-radius:10px;font-weight:600;}
.stButton>button[kind="primary"]{box-shadow:0 6px 16px -6px rgba(116,62,224,.55);}

/* Badges */
.nova-badge{display:inline-flex;align-items:center;gap:.35rem;padding:.18rem .62rem;border-radius:7px;
  font-weight:600;font-size:.76rem;white-space:nowrap;line-height:1.5;}
.nova-badge.ok{color:var(--ok-fg);background:var(--ok-bg);}
.nova-badge.warn{color:var(--warn-fg);background:var(--warn-bg);}
.nova-badge.bad{color:var(--bad-fg);background:var(--bad-bg);}
.nova-badge.neu{color:var(--neu-fg);background:var(--neu-bg);}
.nova-badge.info{color:var(--info-fg);background:var(--info-bg);}

/* Cartes des conditions de go-live (style « Insights ») */
.nova-cond{border:1px solid var(--line);background:var(--card);border-radius:18px;padding:1rem 1.1rem;height:100%;box-shadow:var(--shadow);}
.nova-cond.ok{background:var(--lime-bg);border-color:#D3F5B4;}
.nova-cond .num{display:inline-grid;place-items:center;width:26px;height:26px;border:1.5px solid var(--ink);border-radius:7px;
  font-weight:600;font-size:.8rem;background:#fff;}
.nova-cond h4{margin:.55rem 0 .2rem;font-size:.98rem;color:var(--ink);padding:0;}
.nova-cond p{margin:0;font-size:.83rem;color:var(--muted);}
.nova-cond .nova-badge{white-space:normal;}
</style>
""", unsafe_allow_html=True)

con = db.connect()
policy = pol.load()
ss = st.session_state
ss.setdefault("utilisateur", "utilisateur")
ss.setdefault("messages", [])
ss.setdefault("pending", [])
if "session" not in ss:
    ss.session = Session(con=con, policy=policy, confirmer=lambda p: None, utilisateur=ss.utilisateur)
chat = ss.session
chat.con, chat.policy, chat.utilisateur = con, policy, ss.utilisateur   # connexion SQLite propre à cette exécution
faits = resoudre(con, policy)


# ───────────────────────── Utilitaires d'affichage ─────────────────────────

def montrer_preuve(ev_id: str, contexte: int = 3):
    r = recherche.lire(con, ev_id, contexte)
    if not r:
        st.caption("preuve introuvable")
        return
    p = r["preuve"]
    st.markdown(f"**`{p['path']}`** — {p['repere']} · {p['date_fait'] or 's.d.'}"
                + (f" · {p['auteur']}" if p["auteur"] else "")
                + (f" · _{p['source_class']}_" if p["source_class"] not in ("officiel", None) else "")
                + (f" · **doublon de** `{p['duplicate_of']}`" if p["duplicate_of"] else ""))
    for v in r["voisins"]:
        txt = v["texte"].replace("\n", "  \n")
        if v["ev_id"] == ev_id:
            st.markdown(f"> **{v['repere']}** {v['auteur'] or ''} — {txt}")
        else:
            st.caption(f"{v['repere']} {v['auteur'] or ''} — {v['texte'][:300]}")


def court_repere(r: str) -> str:
    return "courriel" if r.startswith("courriel du") else r


def valeur(cle: str) -> str:
    f = faits.get(cle)
    return "—" if f is None or f.valeur is None else str(f.valeur)


# Classement couleur d'une valeur métier (OUVERT, VERT, OUI...) — vert = ok, ambre = en cours, rouge = bloquant.
# Ordre important : les formes négatives ("NON REMPLIE") contiennent leur positif ("REMPLIE") comme sous-chaîne,
# donc "bad" doit être vérifié avant "ok" pour ne pas peindre un blocage en vert.
TONE_PAR_MOT = [
    ("bad", ("NON REMPLIE", "NON_LIVRE", "OUVERT", "ROUGE", "BLOQUEE", "REFUSE", "ABANDONNE", "EN_CONFLIT")),
    ("warn", ("EN_VALIDATION", "JAUNE", "EN_COURS", "BROUILLON", "A_FAIRE", "SOUMIS")),
    ("ok", ("REMPLIE", "FERME", "VERT", "PAYEE", "APPROUVE", "COMPLETEE", "FAIT", "LIVRE", "OUI")),
]
# États du résolveur (colonne "État" du fact store) : vocabulaire différent des valeurs métier ci-dessus.
TONE_ETAT = {"retenu": "ok", "calcule": "info", "non_decide": "warn", "conflit": "bad"}
# Verdicts d'une assertion dans l'historique d'un fait.
TONE_VERDICT = {
    "retenu": "ok", "concordant": "ok", "proposition adoptée": "ok", "reflet cohérent": "ok", "déclaration confirmée": "ok",
    "non recevable": "bad", "en conflit": "bad",
}


def tone(valeur: str, defaut="neu") -> str:
    v = (valeur or "").upper()
    for t, mots in TONE_PAR_MOT:
        if any(m in v for m in mots):
            return t
    if v.strip() == "NON":   # ex. cr:facturable = NON : trop court/générique pour la liste ci-dessus
        return "bad"
    return defaut


def badge(valeur: str, t: str | None = None) -> str:
    if not valeur:
        return '<span class="nova-badge neu">—</span>'
    return f'<span class="nova-badge {t or tone(valeur)}">{valeur}</span>'


def section(titre: str):
    st.markdown(f'<div class="nova-section"><span class="spark">✦</span>{titre}</div>', unsafe_allow_html=True)


def colorer(df: pd.DataFrame, colonne: str, tons: dict, defaut="neu"):
    """Teinte le fond/texte d'une colonne selon un dictionnaire valeur→tonalité (ok/warn/bad/info/neu)."""
    bg = {"ok": "#DFFCC6", "warn": "#FFF1C7", "bad": "#FFE1DF", "info": "#EEE6FC", "neu": "#EEF0F2"}
    fg = {"ok": "#2F6B12", "warn": "#92560B", "bad": "#B4232A", "info": "#5B2BC2", "neu": "#515157"}
    t = [tons.get(v, defaut) for v in df[colonne]]
    return df.style.apply(lambda _: [f"background-color:{bg[x]};color:{fg[x]};font-weight:600;border-radius:6px;"
                                     for x in t], subset=[colonne])


# ───────────────────────── Barre latérale ─────────────────────────

with st.sidebar:
    st.markdown("""<div class="nova-brand"><div class="mark">✳</div>
      <div><div class="nom">Mémoire NOVA</div><div class="sous">Portail 360 — projet NOVA</div></div></div>""",
                unsafe_allow_html=True)
    ss.utilisateur = st.text_input("Votre nom (trace des mises à jour)", ss.utilisateur)
    n_files = con.execute("SELECT COUNT(DISTINCT path) FROM files").fetchone()[0]
    n_ass = len(db.active_assertions(con))
    try:
        b0 = db.snapshot(con, "baseline")
    except ValueError:
        b0 = None
    c1, c2 = st.columns(2)
    c1.metric("Sources", n_files)
    c2.metric("Assertions", n_ass)
    pret = faits.get("golive:pret")
    if pret and pret.valeur:
        st.markdown(f'<div class="nova-side-row"><span>Go-live</span>{badge(pret.valeur)}</div>', unsafe_allow_html=True)
    st.divider()
    st.caption(f":material/calendar_today: Référence : {DATE_REFERENCE}")
    st.caption(f":material/tune: Politique {policy.version} · baseline ≤ lot {b0 if b0 is not None else '—'} · dernier lot {db.dernier_lot(con)}")
    if st.button("Nouvelle conversation", icon=":material/add:", use_container_width=True):
        ss.messages, ss.pending = [], []
        del ss["session"]
        st.rerun()

_pret = valeur("golive:pret")
_hero_badge = badge(f"Go-live {_pret}", tone(_pret, "neu")) if "golive:pret" in faits else ""
st.markdown(f"""<div class="nova-hero">
  <div class="logo"><span>✳</span> Mémoire NOVA</div>
  <div><div class="tag">Décisions, preuves et <em>contradictions</em><br>du projet en un seul endroit</div>
       <div class="meta">{_hero_badge}</div></div>
</div>""", unsafe_allow_html=True)

tabs = st.tabs([":material/forum: Chat", ":material/dashboard: État du projet", ":material/search: Preuves",
                ":material/timeline: Chronologie", ":material/upload_file: Nouvelle information",
                ":material/compare_arrows: Baseline vs actuel"])

# ───────────────────────── 1. Chat ─────────────────────────

with tabs[0]:
    exemples = [(":material/event:", "Quelle est la date de mise en production approuvée, et avec quelle réserve ?"),
                (":material/shield:", "La sécurité est-elle acceptée ? Distinguez livraison et validation."),
                (":material/receipt_long:", "Quel problème présente INV-003 ?"),
                (":material/flag:", "Quelles sont les trois conditions de go-live ?")]
    if not ss.messages:
        with st.container(key="accueil"):
            st.markdown("""<div class="nova-empty"><h4><span>✦</span> Discutez avec la mémoire du projet</h4>
              <p>Posez une question sur le projet, ou apportez une information nouvelle
              (ex. « Anna Roy est maintenant chargée de projet »). Rien n'est enregistré sans votre confirmation.</p></div>""",
                        unsafe_allow_html=True)
            cols = st.columns(len(exemples))
            for c, (icone, q) in zip(cols, exemples):
                if c.button(q, icon=icone, use_container_width=True):
                    ss.question = q
                    st.rerun()

    AVATAR = {"user": ":material/person:", "assistant": ":material/neurology:"}
    for i, m in enumerate(ss.messages):
        with st.chat_message(m["role"], avatar=AVATAR.get(m["role"])):
            st.markdown(m["texte"])
            if m.get("sources"):
                with st.expander(f"Sources ({len(m['sources'])})"):
                    for n, path, rep, date, auteur, ev in m["sources"]:
                        c1, c2 = st.columns([6, 1])
                        c1.markdown(f"**[{n}]** `{path}` — {court_repere(rep)} · {date or 's.d.'}")
                        with c2.popover("voir"):
                            montrer_preuve(ev)
            for av in m.get("avertissements", []):
                st.warning(av, icon="⚠️")

    for k, p in enumerate(ss.pending):
        if p["etat"] != "attente":
            continue
        prop = p["prop"]
        with st.container(key=f"pending{k}"):
            st.markdown('<div class="nova-pending-head"><span>✦ Mise à jour proposée</span><span>En attente de confirmation</span></div>',
                        unsafe_allow_html=True)
            st.markdown(f"`{prop.cle}` = **{prop.valeur}** {badge(prop.statut, 'info')}"
                        + (f" · {prop.acteur}" if prop.acteur else "") + (f" · effet {prop.date_fait}" if prop.date_fait else ""),
                        unsafe_allow_html=True)
            if prop.preuve:
                st.caption(f"📎 Preuve citée : {prop.preuve}")
            for av in prop.avertissements:
                st.warning(av, icon="⚠️")
            if prop.impacts:
                st.markdown("Impacts si enregistrée :\n" + "\n".join(f"- `{x}`" for x in prop.impacts))
            c1, c2, _ = st.columns([1, 1, 4])
            if c1.button("Enregistrer", icon=":material/check:", key=f"ok{k}", type="primary"):
                aid = chat.enregistrer(prop, p["message"])
                p["etat"] = f"enregistrée #{aid}"
                note = f"✔ Enregistré (assertion #{aid}) : {prop.resume()}"
                ss.messages.append({"role": "assistant", "texte": note})
                chat.historique.append({"role": "assistant", "content": f"[Interface] {note}"})
                st.rerun()
            if c2.button("Rejeter", icon=":material/close:", key=f"ko{k}"):
                p["etat"] = "rejetée"
                note = f"✘ Rejeté par {ss.utilisateur} : {prop.resume()}"
                ss.messages.append({"role": "assistant", "texte": note})
                chat.historique.append({"role": "assistant", "content": f"[Interface] {note}"})
                st.rerun()

    question = st.chat_input("Posez une question ou apportez une information…") or ss.pop("question", None)
    if question:
        ss.messages.append({"role": "user", "texte": question})
        with st.spinner("Consultation de la mémoire…"):
            try:
                rep = chat.repondre(question)
                ss.messages.append({"role": "assistant", "texte": rep.texte, "sources": rep.sources,
                                    "avertissements": rep.avertissements})
                for prop, msg in rep.en_attente:
                    ss.pending.append({"prop": prop, "message": msg, "etat": "attente"})
            except Exception as e:   # quota, réseau : l'interface reste utilisable
                ss.messages.append({"role": "assistant", "texte": f"Le modèle est indisponible ({type(e).__name__}). "
                                    "Les onglets État du projet, Preuves et Chronologie restent consultables."})
        st.rerun()

# ───────────────────────── 2. État du projet ─────────────────────────

with tabs[1]:
    c = st.columns(5)
    c[0].metric("Mise en production", valeur("projet:date_golive"))
    c[1].metric("Go-live prêt", valeur("golive:pret"))
    c[2].metric("Chargé de projet", valeur("role:charge_de_projet"))
    c[3].metric("Montant autorisé", f"{int(valeur('budget:autorise')):,} $".replace(",", " ")
                if valeur("budget:autorise").isdigit() else "—")
    c[4].metric("Montant contesté INV-003", f"{int(valeur('facture:INV-003:montant_conteste')):,} $".replace(",", " ")
                if valeur("facture:INV-003:montant_conteste").isdigit() else "—")
    if "golive:reserve" in faits:
        st.caption(f"Réserve : {valeur('golive:reserve')}")

    section("Conditions de go-live")
    conds = [(c.split(":")[2], faits[c.rsplit(":", 1)[0]].valeur, f.valeur) for c, f in sorted(faits.items())
             if c.startswith("golive:condition:") and c.endswith(":etat")]
    if conds:
        for i, (col, (nom, definition, etat)) in enumerate(zip(st.columns(len(conds)), conds), 1):
            classe = "ok" if tone(etat) == "ok" else ""
            col.markdown(f"""<div class="nova-cond {classe}"><span class="num">{i}</span><h4>{nom}</h4><p>{definition}</p>
                         <div style="margin-top:.6rem">{badge(etat)}</div></div>""", unsafe_allow_html=True)
    else:
        st.caption("Aucune condition de go-live définie.")

    section("Contradictions et alertes")
    alertes = [(cle, a) for cle, f in sorted(faits.items()) for a in f.alertes]
    for cle, a in alertes:
        st.warning(f"`{cle}` — {a}", icon="⚠️")
    if not alertes:
        st.success("Aucune alerte — les sources se recoupent sans contradiction détectée.")

    section("Faits en vigueur")
    filtre = st.text_input("Filtrer les clés", placeholder="ex. ticket:, facture:INV-003, role")
    lignes = [{"Clé": cle, "Valeur": f.valeur, "État": f.etat, "Retenu": f.retenu.court() if f.retenu else f.explication[:80],
               "Alertes": len(f.alertes)} for cle, f in sorted(faits.items()) if filtre.lower() in cle.lower()]
    df_faits = pd.DataFrame(lignes)
    if not df_faits.empty:
        st.dataframe(colorer(df_faits, "État", TONE_ETAT), hide_index=True, use_container_width=True)
    else:
        st.caption("Aucune clé ne correspond au filtre.")

    cle = st.selectbox("Détail d'un fait (historique, verdicts, preuves)", [l["Clé"] for l in lignes] or ["—"])
    f = faits.get(cle)
    if f:
        st.markdown(f"### `{cle}` = {f.valeur if f.valeur is not None else '—'}  _[{f.etat}]_")
        if f.explication:
            st.info(f.explication)
        for nom, lst in (("Proposé", f.proposee_par), ("Décidé", f.decisions), ("Validé", f.validations)):
            if lst:
                st.markdown(f"**{nom}** : " + " ; ".join(a.court() for a in lst))
        for a in f.alertes:
            st.warning(a, icon="⚠️")
        hist = [{"Date": a.date or "s.d.", "Statut": a.statut, "Acteur": a.acteur, "Autorité": a.niveau,
                 "Valeur": a.valeur, "Verdict": a.verdict, "Raison": a.raison, "Note": a.note or "",
                 "Origine": a.origine, "Preuve": a.ev_id or ""} for a in f.historique]
        st.dataframe(pd.DataFrame(hist), hide_index=True, use_container_width=True)
        evs = [h["Preuve"] for h in hist if h["Preuve"]]
        if evs:
            ev = st.selectbox("Lire une preuve", evs, key="ev_fait")
            montrer_preuve(ev)

# ───────────────────────── 3. Preuves ─────────────────────────

with tabs[2]:
    c1, c2 = st.columns([3, 1])
    q = c1.text_input("Rechercher dans les courriels, CR, tickets, Teams, PDF, tableurs, captures",
                      placeholder="ex. rollback runbook")
    fich = c2.text_input("Filtre fichier", placeholder="ex. SEC-210")
    if q:
        res = recherche.chercher(con, q, n=15, fichier=fich or None)
        st.caption(f"{len(res)} résultat(s)")
        for r in res:
            titre = f"{r['path'].rsplit('/', 1)[-1]} — {court_repere(r['repere'])} — {r['date_fait'] or 's.d.'}"
            if r["source_class"] != "officiel" or r["duplicate_of"]:
                titre += f"  ·  {r['source_class']}{' · doublon' if r['duplicate_of'] else ''}"
            with st.expander(titre):
                montrer_preuve(r["ev_id"])
    with st.expander("Inventaire des fichiers"):
        rows = [dict(r) for r in con.execute("""
            SELECT f.path AS Fichier, f.source_class AS Classe, f.status AS Statut, f.doc_date AS Date,
                   f.duplicate_of AS "Doublon de",
                   (SELECT group_concat(email_path, ', ') FROM attachments a WHERE a.file_path = f.path) AS "Joint à"
            FROM files f WHERE f.file_id IN (SELECT MAX(file_id) FROM files GROUP BY path) ORDER BY f.path""")]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# ───────────────────────── 4. Chronologie ─────────────────────────

with tabs[3]:
    toutes = sorted(((a, cle) for cle, f in faits.items() for a in f.historique), key=lambda x: (x[0].date, x[0].id))
    c1, c2, c3 = st.columns([2, 2, 1])
    statuts = c1.multiselect("Statuts", sorted({a.statut for a, _ in toutes}), default=["DECISION", "VALIDATION", "PROPOSITION"])
    cle_f = c2.text_input("Clé contient", placeholder="ex. date_golive")
    seuls = c3.checkbox("Écartés seulement", help="remplacés, périmés, non confirmés, non recevables")
    lignes = [{"Date": a.date or "s.d.", "Clé": cle, "Valeur": a.valeur, "Statut": a.statut, "Acteur": a.acteur,
               "Verdict": a.verdict, "Raison": a.raison, "Source": (a.source or a.origine).rsplit("/", 1)[-1]}
              for a, cle in toutes
              if (not statuts or a.statut in statuts) and cle_f.lower() in cle.lower()
              and (not seuls or a.verdict not in ("retenu", "concordant", "proposition adoptée", "reflet cohérent"))]
    df_chrono = pd.DataFrame(lignes)
    if not df_chrono.empty:
        st.dataframe(colorer(df_chrono, "Verdict", TONE_VERDICT, defaut="warn"), hide_index=True,
                    use_container_width=True, height=560)
    else:
        st.caption("Aucun événement ne correspond aux filtres.")

# ───────────────────────── 5. Nouvelle information ─────────────────────────

with tabs[4]:
    st.markdown("Téléversez un **.zip** du dossier (structure conservée : un fichier modifié est reconnu comme nouvelle "
                "version) ou des fichiers isolés. Les propositions du LLM sont à relire avant chargement.")
    up = st.file_uploader("Dossier (.zip) ou fichiers", accept_multiple_files=True)
    partiel = st.checkbox("Le dépôt ne contient que les nouveautés (ne rien signaler comme absent)", value=True)
    if up and st.button("Ingérer et proposer des assertions", type="primary"):
        dest = config.DATA / "uploads" / time.strftime("%Y%m%d-%H%M%S")
        dest.mkdir(parents=True, exist_ok=True)
        for f in up:
            (dest / f.name).write_bytes(f.getvalue())
        source = next(dest.glob("*.zip")) if len(up) == 1 and up[0].name.lower().endswith(".zip") else dest
        with st.spinner("Ingestion et extraction (quelques dizaines de secondes)…"):
            try:
                res = nouvelle_info.integrer(con, source, partial=partiel, auto=False,
                                             transcrire=ingest.make_transcriber(True))
                ss.extraction = {"rows": res["propositions"], "ingestion": res["ingestion"], "csv": str(res["csv"])}
            except Exception as e:
                st.error(f"Échec : {type(e).__name__}: {e}")
    if "extraction" in ss:
        ing = ss.extraction["ingestion"]
        st.success(f"Lot {ing['batch_id']} : {len(ing['nouveau'])} nouveau(x), {len(ing['modifie'])} modifié(s), "
                   f"{len(ing['inchange'])} inchangé(s), {len(ing['doublon'])} doublon(s), "
                   f"{len(ing['erreurs'])} erreur(s)")
        for k in ("doublon", "pj_liee", "pj_differente", "erreurs", "non_supporte", "deplace"):
            for x in ing[k]:
                st.caption(f"{k} : {x}")
        df = pd.DataFrame(ss.extraction["rows"], columns=COLONNES_REVUE).fillna("")
        df.insert(0, "garder ?", df["garder"] == "oui")
        st.markdown("**Propositions** — décochez pour rejeter ; les cellules sont modifiables.")
        edit = st.data_editor(df.drop(columns=["garder"]), hide_index=True, use_container_width=True,
                              column_config={"garder ?": st.column_config.CheckboxColumn()}, key="revue")
        if st.button("Charger les propositions retenues", type="primary"):
            edit = edit.rename(columns={"garder ?": "garder"})
            edit["garder"] = edit["garder"].map(lambda v: "oui" if v else "non")
            relu = Path(ss.extraction["csv"]).with_name(Path(ss.extraction["csv"]).stem + "_relu.csv")
            edit[COLONNES_REVUE].to_csv(relu, index=False, encoding="utf-8")
            try:
                r = asr.charger_csv(relu, con=con, kind="extraction")
                st.success(f"Lot {r['batch_id']} : {r['count']} assertions chargées. Voir l'onglet Baseline vs actuel.")
                del ss["extraction"]
            except asr.AssertionInvalide as e:
                st.error(str(e))

    with st.expander("Annuler un lot (mise à jour erronée) — rien n'est effacé"):
        lots = [r for r in con.execute("""SELECT * FROM batches WHERE kind IN ('chat','extraction','curation')
                 AND batch_id NOT IN (SELECT supersedes FROM batches WHERE supersedes IS NOT NULL)
                 ORDER BY batch_id DESC""")]
        if lots:
            libelles = {r["batch_id"]: f"{r['batch_id']} · {r['kind']} · {r['label']}" for r in lots}
            choix = st.selectbox("Lot", list(libelles), format_func=libelles.get)
            raison = st.text_input("Raison")
            if st.button("Annuler ce lot") and raison:
                db.annuler_lot(con, choix, f"{ss.utilisateur} : {raison}")
                st.rerun()

# ───────────────────────── 6. Baseline vs actuel ─────────────────────────

with tabs[5]:
    if b0 is None:
        st.info("Aucune baseline : figer l'état actuel comme référence avant d'intégrer une nouvelle information.")
        if st.button("Créer la baseline maintenant"):
            db.creer_snapshot(con, "baseline", f"créée par {ss.utilisateur}")
            st.rerun()
    else:
        md, f0, f1 = rapport_maj.rapport(con, "baseline", policy)
        st.download_button("Télécharger le rapport (.md)", md, file_name="rapport_baseline_vs_actuel.md")
        st.markdown(md)
