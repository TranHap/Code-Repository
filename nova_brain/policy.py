"""Chargement et validation de la politique de résolution (policy.toml)."""
import fnmatch
import hashlib
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .vocab import STATUTS

DEFAULT = Path(__file__).with_name("policy.toml")
CRITERES = {"autorite", "date_fait"}


class PolicyError(ValueError):
    pass


@dataclass
class Policy:
    version: str
    autorite: dict
    fournisseurs: list
    domaines: dict
    valeurs_controlees: set
    familles: list
    regles: list
    coherence: dict
    conditions_remplies: set
    budget: dict
    instances: dict = field(default_factory=dict)
    empreinte: str = ""
    raw: dict = field(default_factory=dict)

    def rang(self, niveau: str) -> int:
        return self.autorite[niveau]

    def famille(self, cle: str) -> dict:
        for f in self.familles:
            if fnmatch.fnmatchcase(cle, f["motif"]):
                return f
        raise PolicyError(f"aucune famille ne couvre {cle}")

    def domaine(self, cle: str) -> str | None:
        best = None
        for prefixe, role in self.domaines.items():
            if cle.startswith(prefixe) and (best is None or len(prefixe) > len(best[0])):
                best = (prefixe, role)
        return best[1] if best else None


def load(path: Path | str = DEFAULT) -> Policy:
    path = Path(path)
    raw_bytes = path.read_bytes()
    try:
        d = tomllib.loads(raw_bytes.decode("utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise PolicyError(f"{path.name} : TOML invalide ({e})")

    niveaux = {"comite", "charge_de_projet", "responsable_domaine", "partie_prenante", "fournisseur", "reflet", "non_officiel"}
    aut = d.get("autorite", {})
    if set(aut) != niveaux:
        raise PolicyError(f"[autorite] doit définir exactement {sorted(niveaux)} (manquant : {sorted(niveaux - set(aut))}, "
                          f"inconnu : {sorted(set(aut) - niveaux)})")
    familles = d.get("famille", [])
    if not familles or familles[-1].get("motif") != "*":
        raise PolicyError("la dernière [[famille]] doit avoir motif = \"*\" (famille par défaut)")
    for f in familles:
        bad = set(f.get("gagnant", [])) - STATUTS
        if bad or not f.get("gagnant"):
            raise PolicyError(f"famille {f.get('motif')} : statuts gagnants invalides {sorted(bad) or '(vide)'}")
        if not f.get("ordre") or set(f["ordre"]) - CRITERES:
            raise PolicyError(f"famille {f['motif']} : ordre doit utiliser {sorted(CRITERES)}")

    from .regles import REGLES   # import tardif : les règles importent ce module
    actives = d.get("regles", {}).get("actives", [])
    inconnues = [r for r in actives if r not in REGLES]
    if inconnues:
        raise PolicyError(f"règles inconnues {inconnues} (disponibles : {sorted(REGLES)})")

    return Policy(
        version=d.get("version", path.stem),
        autorite=aut,
        fournisseurs=d.get("organisations", {}).get("fournisseurs", []),
        domaines=d.get("domaines", {}),
        valeurs_controlees=set(d.get("validation", {}).get("valeurs_controlees", [])),
        familles=familles,
        regles=actives,
        coherence=d.get("coherence", {}),
        conditions_remplies=set(d.get("conditions", {}).get("remplie_si", [])),
        budget=d.get("budget", {}),
        instances=d.get("instances", {}),
        empreinte=hashlib.sha256(raw_bytes).hexdigest()[:12],
        raw=d,
    )
