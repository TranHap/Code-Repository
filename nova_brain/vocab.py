"""Vocabulaire contrôlé des assertions : quelles clés existent et quel type de valeur chacune accepte.

Une clé désigne UNE chose sur laquelle le projet peut se contredire ("projet:date_golive",
"ticket:SEC-210:statut"). Deux assertions sur la même clé sont comparables par le résolveur ;
c'est pourquoi les clés sont normalisées ici, pour la curation manuelle comme pour l'extraction LLM.

Ajouter un type de sujet = ajouter une ligne dans FAMILLES (aucun changement du résolveur).
"""
import re
from dataclasses import dataclass

from .dates import find_date

STATUTS = {
    "DECISION",      # tranché par une instance ou une personne qui en a l'autorité
    "VALIDATION",    # vérification par la personne responsable (ex. re-test sécurité)
    "DOCUMENT",      # document de référence (contrat, facture, CR signé, schéma)
    "CONSTAT",       # observation factuelle d'un état
    "ENGAGEMENT",    # promesse ou action à faire
    "PROPOSITION",   # recommandation, demande, brouillon : jamais une décision
    "DECLARATION",   # affirmation non vérifiée (souvent le fournisseur : « c'est réglé »)
    "REFLET",        # document qui recopie un état (plan, registre, rapport) : peut être périmé
}

ENUMS = {
    "ticket": {"OUVERT", "EN_VALIDATION", "FERME"},
    "risque": {"OUVERT", "FERME"},
    "cr": {"BROUILLON", "SOUMIS", "APPROUVE", "REFUSE", "REPORTE_PHASE2"},
    "facture": {"EN_VALIDATION", "BLOQUEE", "APPROUVEE", "PAYEE"},
    "oui_non": {"OUI", "NON"},
    "migration": {"A_FAIRE", "EN_COURS", "COMPLETEE"},
    "portee": {"INCLUS", "EXCLU", "REPORTE"},
    "action": {"A_FAIRE", "EN_COURS", "FAIT", "ABANDONNE"},
    "livraison": {"LIVRE", "NON_LIVRE"},
    "rapport": {"VERT", "JAUNE", "ROUGE"},
}


@dataclass(frozen=True)
class Famille:
    motif: str      # "ticket:{id}:statut" ; {x} = segment libre (sans ":")
    type: str       # date | montant | texte | personne | enum:<nom>
    aide: str
    statuts: frozenset | None = None   # statuts autorisés (None = tous) ; frozenset() = clé calculée, jamais saisie


DECISION_SEULE = frozenset({"DECISION"})
CALCULEE = frozenset()


FAMILLES = [
    Famille("projet:date_golive", "date", "date de mise en production cible"),
    Famille("projet:budget_initial", "montant", "budget initial approuvé au démarrage"),
    Famille("golive:reserve", "texte", "réserve générale sur la date de mise en production", DECISION_SEULE),
    Famille("golive:condition:{id}", "texte", "condition de go-live (lien = clé dont l'état la satisfait)", DECISION_SEULE),
    Famille("analyse:{sujet}", "texte", "analyse ou cause (ex. cause du report)"),
    Famille("role:{role}", "personne", "titulaire d'un rôle (charge_de_projet, securite, accessibilite...)"),
    Famille("organisation:{personne}", "texte", "organisation d'une personne"),
    Famille("contrat:plafond", "montant", "montant maximal initial du contrat"),
    Famille("contrat:fin", "date", "fin de la période contractuelle"),
    Famille("contrat:regle_changement", "texte", "règle de gestion des changements"),
    Famille("portee:{element}", "texte", "contenu de portée (ex. phase1)"),
    Famille("portee:{element}:{phase}", "enum:portee", "inclusion d'un élément dans une phase"),
    Famille("cr:{id}:statut", "enum:cr", "statut d'une demande de changement"),
    Famille("cr:{id}:montant", "montant", "montant d'une demande de changement"),
    Famille("cr:{id}:facturable", "enum:oui_non", "le CR peut-il être facturé"),
    Famille("facture:{id}:statut", "enum:facture", "statut d'une facture"),
    Famille("facture:{id}:total", "montant", "total d'une facture"),
    Famille("facture:{id}:ligne:{ref}", "montant", "ligne d'une facture (ref = CR-04, jalon3...)"),
    Famille("hebergement:production", "texte", "région d'hébergement des données de production"),
    Famille("hebergement:migration", "enum:migration", "migration vers la région décidée"),
    Famille("exigence:{id}", "texte", "exigence (sécurité, exploitation...)"),
    Famille("ticket:{id}:statut", "enum:ticket", "état d'un ticket"),
    Famille("livraison:{id}", "enum:livraison", "livraison d'un correctif (≠ validation)"),
    Famille("risque:{id}:statut", "enum:risque", "statut d'un risque au registre"),
    Famille("rapport:{dimension}", "enum:rapport", "couleur d'une dimension dans un rapport de statut"),
    Famille("action:{id}", "enum:action", "action ou engagement à suivre"),
    Famille("communication:{id}", "texte", "consigne de communication"),
    # Clés calculées par les règles du résolveur (jamais saisies) :
    Famille("budget:autorise", "montant", "montant autorisé (calculé par le résolveur)", CALCULEE),
    Famille("facture:{id}:montant_conteste", "montant", "montant facturé sans approbation (calculé)", CALCULEE),
    Famille("golive:condition:{id}:etat", "texte", "état d'une condition de go-live (calculé)", CALCULEE),
    Famille("golive:pret", "enum:oui_non", "toutes les conditions de go-live remplies (calculé)", CALCULEE),
]


def _regex(motif: str) -> re.Pattern:
    return re.compile("^" + re.sub(r"\\\{\w+\\\}", r"[^:]+", re.escape(motif)) + "$")


_COMPILED = [(f, _regex(f.motif)) for f in FAMILLES]


def famille(cle: str) -> Famille | None:
    for f, rx in _COMPILED:
        if rx.match(cle):
            return f
    return None


class VocabError(ValueError):
    pass


def verifier_statut(cle: str, statut: str) -> None:
    f = famille(cle)
    if f and f.statuts is not None:
        if not f.statuts:
            raise VocabError(f"{cle} est calculée par le résolveur : elle ne se saisit pas")
        if statut not in f.statuts:
            raise VocabError(f"{cle} n'accepte que {sorted(f.statuts)} (reçu {statut})")


def normaliser_valeur(cle: str, valeur: str) -> str:
    """Valeur canonique selon le type de la clé ; lève VocabError si invalide."""
    f = famille(cle)
    if f is None:
        raise VocabError(f"clé inconnue « {cle} » (voir vocab.FAMILLES)")
    v = (valeur or "").strip()
    if not v:
        raise VocabError(f"{cle} : valeur vide")
    if f.type == "date":
        d = find_date(v)
        if not d:
            raise VocabError(f"{cle} : date invalide « {v} »")
        return d
    if f.type == "montant":
        digits = re.sub(r"[\s $ CAD  ]", "", v).replace(",", ".")
        try:
            n = float(digits)
        except ValueError:
            raise VocabError(f"{cle} : montant invalide « {v} »")
        return str(int(n)) if n == int(n) else str(n)
    if f.type.startswith("enum:"):
        vals = ENUMS[f.type[5:]]
        u = v.upper().replace(" ", "_").replace("É", "E").replace("È", "E")
        if u not in vals:
            raise VocabError(f"{cle} : « {v} » hors de {sorted(vals)}")
        return u
    return v
