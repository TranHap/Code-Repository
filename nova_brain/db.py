"""Schéma SQLite de la mémoire.

Principe : rien n'est jamais modifié ni supprimé (append-only).
- batches  : chaque ingestion / mise à jour = un lot horodaté (sert de point de snapshot)
- files    : une ligne par version d'un fichier. Une nouvelle version (ou un retour à l'ancien contenu) = nouvelle ligne.
- attachments : liens courriel → pièce jointe (un même fichier peut être joint à plusieurs courriels)
- evidence : unités de preuve citables (ligne, tour de parole, commentaire, rangée, page, capture)
- events   : assertions sur le projet (proposition, décision, validation...) reliées à une source
"""
import sqlite3
from datetime import datetime

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    batch_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT NOT NULL,          -- corpus | upload | curation | chat
    label       TEXT,
    source_sha  TEXT,                   -- empreinte du fichier chargé (lots de curation)
    supersedes  INTEGER,                -- lot de curation remplacé par celui-ci
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
    file_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    path         TEXT NOT NULL,         -- relatif à la racine du corpus ; "E02.eml::x.pdf" pour une PJ sans fichier séparé
    sha256       TEXT NOT NULL,
    ext          TEXT,
    size         INTEGER,
    doc_date     TEXT,                  -- date du document lue dans son contenu (pas la date système)
    title        TEXT,
    message_id   TEXT,                  -- normalisé (sans <>, minuscules)
    duplicate_of  TEXT,                 -- chemin du fichier dont celui-ci est une copie
    source_class TEXT,                  -- officiel | archive | non_officiel | hors_projet_probable
    change       TEXT,                  -- nouveau | modifie | reparse | deplace
    status       TEXT NOT NULL DEFAULT 'ok',  -- ok | incomplet (capture non transcrite) | erreur | non_supporte
    error        TEXT,
    parser_version INTEGER,
    batch_id     INTEGER NOT NULL REFERENCES batches(batch_id)
);
CREATE TABLE IF NOT EXISTS attachments (
    email_path  TEXT NOT NULL,
    name        TEXT NOT NULL,          -- nom de la pièce jointe dans le courriel
    file_path   TEXT NOT NULL,          -- fichier séparé identique, ou "courriel::nom" si ingérée à part
    sha256      TEXT NOT NULL,
    batch_id    INTEGER NOT NULL REFERENCES batches(batch_id)
);
CREATE TABLE IF NOT EXISTS evidence (
    ev_id      TEXT PRIMARY KEY,        -- ex. "02_Reunions/M04_...txt#L12"
    file_id    INTEGER NOT NULL REFERENCES files(file_id),
    unit       TEXT,                    -- ligne | tour | commentaire | rangee | page | capture | courriel
    repere     TEXT NOT NULL,           -- repère lisible : "15:22 (ligne 18)", "Risques!A2:H2", "p.1"
    date_fait  TEXT,                    -- ISO, date du fait si connue
    auteur     TEXT,
    texte      TEXT NOT NULL,
    batch_id   INTEGER NOT NULL REFERENCES batches(batch_id)
);
CREATE TABLE IF NOT EXISTS events (
    event_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ref          TEXT,                  -- identifiant d'origine (ex. EV012)
    date_fait    TEXT,
    heure        TEXT,
    sujet        TEXT,
    type         TEXT,                  -- DECISION | PROPOSITION | VALIDATION | DECLARATION | CONSTAT | ...
    resume       TEXT,
    acteur       TEXT,
    source       TEXT,                  -- chemin du fichier source
    repere       TEXT,
    note         TEXT,
    liens        TEXT,
    origine      TEXT NOT NULL,         -- corpus | curation:<fichier> | chat:<utilisateur>
    inserted_at  TEXT NOT NULL,
    batch_id     INTEGER NOT NULL REFERENCES batches(batch_id)
);
CREATE TABLE IF NOT EXISTS assertions (
    assertion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref          TEXT,                  -- événement d'origine (ex. EV034) ou identifiant de chat
    cle          TEXT NOT NULL,         -- clé normalisée (vocab.FAMILLES)
    valeur       TEXT NOT NULL,         -- valeur canonique (date ISO, montant entier, ENUM...)
    statut       TEXT NOT NULL,         -- vocab.STATUTS
    acteur       TEXT,                  -- personne(s) ou instance ("Comité de direction")
    autorite     TEXT,                  -- forçage du niveau (comite, reflet, non_officiel) ; sinon calculé
    date_fait    TEXT,                  -- seulement si saisie explicitement ; sinon lue sur la preuve courante
    lien         TEXT,                  -- clé liée (ex. ticket:SEC-210:statut pour une condition)
    ev_id        TEXT REFERENCES evidence(ev_id),   -- preuve exacte
    source       TEXT,
    ancre        TEXT,                  -- suffixe de l'unité de preuve (L17, msg, p1, capture...)
    note         TEXT,
    origine      TEXT NOT NULL,         -- curation:<fichier> | chat:<utilisateur> | extraction:<modèle>
    inserted_at  TEXT NOT NULL,
    batch_id     INTEGER NOT NULL REFERENCES batches(batch_id)
);
CREATE TABLE IF NOT EXISTS snapshots (
    nom         TEXT PRIMARY KEY,       -- ex. baseline
    batch_max   INTEGER NOT NULL,       -- état = tous les lots jusqu'à celui-ci
    note        TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_assert_cle ON assertions(cle);
CREATE INDEX IF NOT EXISTS ix_files_path ON files(path);
CREATE INDEX IF NOT EXISTS ix_ev_file ON evidence(file_id);
CREATE INDEX IF NOT EXISTS ix_events_sujet ON events(sujet);
"""


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def connect(path=None) -> sqlite3.Connection:
    config.DATA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path or config.DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")   # lecture par l'interface pendant une ingestion
    con.executescript(SCHEMA)
    _migrer(con)
    return con


# Colonnes ajoutées après la création initiale : ajoutées aux bases existantes sans perte de données.
MIGRATIONS = [("files", "parser_version", "INTEGER"), ("assertions", "ancre", "TEXT")]


def _migrer(con):
    for table, col, typ in MIGRATIONS:
        cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
        if col not in cols:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
    con.commit()


def new_batch(con, kind: str, label: str = "", source_sha=None, supersedes=None) -> int:
    cur = con.execute("INSERT INTO batches(kind, label, source_sha, supersedes, created_at) VALUES (?,?,?,?,?)",
                      (kind, label, source_sha, supersedes, now()))
    return cur.lastrowid


def dernier_lot(con) -> int:
    return con.execute("SELECT COALESCE(MAX(batch_id), 0) FROM batches").fetchone()[0]


def creer_snapshot(con, nom: str, note: str = "", batch_max: int | None = None) -> int:
    """Fige l'état courant sous un nom. Un snapshot existant n'est jamais écrasé (la baseline reste la baseline)."""
    if con.execute("SELECT 1 FROM snapshots WHERE nom=?", (nom,)).fetchone():
        raise ValueError(f"le snapshot « {nom} » existe déjà")
    b = batch_max if batch_max is not None else dernier_lot(con)
    con.execute("INSERT INTO snapshots(nom, batch_max, note, created_at) VALUES (?,?,?,?)", (nom, b, note, now()))
    con.commit()
    return b


def snapshot(con, nom: str) -> int:
    r = con.execute("SELECT batch_max FROM snapshots WHERE nom=?", (nom,)).fetchone()
    if r is None:
        raise ValueError(f"snapshot « {nom} » inconnu")
    return r["batch_max"]


def annuler_lot(con, batch_id: int, raison: str) -> int:
    """Retire un lot (ex. mise à jour par chat erronée) SANS l'effacer : un lot « annulation » le remplace.
    Les snapshots antérieurs continuent de le voir ; l'état courant ne le voit plus."""
    b = con.execute("SELECT kind FROM batches WHERE batch_id=?", (batch_id,)).fetchone()
    if b is None:
        raise ValueError(f"lot {batch_id} inconnu")
    if b["kind"] in ("corpus", "upload"):
        raise ValueError("un lot de fichiers ne s'annule pas : téléverser une version corrigée du fichier")
    if con.execute("SELECT 1 FROM batches WHERE supersedes=?", (batch_id,)).fetchone():
        raise ValueError(f"le lot {batch_id} est déjà remplacé ou annulé")
    n = new_batch(con, "annulation", raison, supersedes=batch_id)
    con.commit()
    return n


def active_assertions(con, batch_max: int | None = None):
    """Assertions en vigueur : hors lots de curation remplacés, et jusqu'au lot batch_max (snapshot)."""
    q = """SELECT a.* FROM assertions a
           WHERE a.batch_id NOT IN (SELECT supersedes FROM batches
                                    WHERE supersedes IS NOT NULL AND (? IS NULL OR batch_id <= ?))
             AND (? IS NULL OR a.batch_id <= ?)
           ORDER BY a.assertion_id"""
    return con.execute(q, (batch_max, batch_max, batch_max, batch_max)).fetchall()


def current_files(con):
    """Version la plus récente de chaque chemin."""
    return con.execute("""
        SELECT f.* FROM files f
        JOIN (SELECT path, MAX(file_id) AS m FROM files GROUP BY path) last ON f.file_id = last.m
    """).fetchall()
