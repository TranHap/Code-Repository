import sys
from email.message import EmailMessage
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from nova_brain import db  # noqa: E402


@pytest.fixture
def con(tmp_path_factory):
    # Base hors du dossier ingéré (tmp_path), sinon la base s'ingère elle-même.
    c = db.connect(tmp_path_factory.mktemp("db") / "memory_test.db")
    yield c
    c.close()


def write(root: Path, rel: str, data) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    return p


def make_email(subject="NOVA - test", body="Bonjour NOVA", html=None, msgid="<m1@nova.local>",
               date="Tue, 08 Sep 2026 11:16:00 -0400", attachments=()):
    m = EmailMessage()
    if subject is not None:
        m["Subject"] = subject
    m["From"] = "Julien Moreau <julien@boreal.example>"
    m["To"] = "nicolas@demo.example"
    if date:
        m["Date"] = date
    if msgid:
        m["Message-ID"] = msgid
    if body is not None:
        m.set_content(body)
        if html:
            m.add_alternative(html, subtype="html")
    elif html:
        m.set_content(html, subtype="html")
    for name, payload, maintype, subtype in attachments:
        if maintype == "message":
            m.add_attachment(payload)  # EmailMessage → message/rfc822
        else:
            m.add_attachment(payload, maintype=maintype, subtype=subtype, filename=name)
    return bytes(m)


def files(con):
    return {f["path"]: f for f in db.current_files(con)}


def evidence(con, path_like):
    return con.execute("""SELECT e.* FROM evidence e JOIN files f USING(file_id)
                          WHERE f.path LIKE ? ORDER BY e.rowid""", (path_like,)).fetchall()


@pytest.fixture(scope="session")
def memoire_reelle(tmp_path_factory):
    """Construit une fois la mémoire du vrai corpus ; chaque test en reçoit une copie (il peut écrire dedans)."""
    import json
    from nova_brain import assertions, config, ingest, seed_events
    if not config.CORPUS_DEFAULT.exists():
        pytest.skip("corpus absent")
    path = tmp_path_factory.mktemp("reelle") / "m.db"
    c = db.connect(path)
    cache = json.loads(config.VISION_CACHE.read_text(encoding="utf-8")) if config.VISION_CACHE.exists() else {}
    ingest.ingest(config.CORPUS_DEFAULT, con=c, transcrire=lambda b: cache.get(ingest.sha(b), "[capture non transcrite]"))
    seed_events.seed(seed_events.DEFAULT, con=c)
    assertions.charger_csv(config.ROOT / "rendu" / "02_Memoire" / "assertions.csv", con=c)
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    c.close()
    return path


@pytest.fixture
def copie_reelle(memoire_reelle, tmp_path):
    import shutil
    dst = tmp_path / "copie.db"
    shutil.copy(memoire_reelle, dst)
    c = db.connect(dst)
    yield c
    c.close()
