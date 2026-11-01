"""Brouillon assisté par IA : des notes brutes deviennent un contenu de spécification."""

import json
import os
import re

from .modeles import charger, verifier

MODELE_IA = os.environ.get("SPECS_STUDIO_MODELE", "claude-sonnet-5-5")

CONSIGNES = (
    "Tu es consultant SAP FI/CO senior. À partir des notes fournies, tu rédiges le contenu d'une "
    "spécification. Règles : ne rien inventer ; si une information manque, laisse la section vide "
    "et ajoute la question dans « points_ouverts » quand cette section existe ; phrases courtes, "
    "termes SAP exacts (transactions, tables, objets) uniquement s'ils figurent dans les notes ; "
    "une règle ou un test vérifiable par ligne. Réponds uniquement par un objet JSON valide, "
    "sans texte autour."
)


def _forme(s):
    if s["type"] == "tableau":
        return [dict.fromkeys(s["colonnes"], "...")]
    if s["type"] == "liste":
        return ["..."]
    return "..."


def construire_prompt(type_doc, notes):
    modele = charger(type_doc)
    forme = {
        "metadonnees": dict.fromkeys(modele["metadonnees"], ""),
        "sections": {s["id"]: _forme(s) for s in modele["sections"]},
    }
    utilisateur = (
        f"Type de document : {modele['titre']}.\n\n"
        f"Notes fournies :\n{notes}\n\n"
        "Structure JSON attendue. Pour un tableau, chaque ligne est une liste de valeurs dans "
        "l'ordre des colonnes indiquées par les clés :\n"
        f"{json.dumps(forme, ensure_ascii=False, indent=1)}"
    )
    return CONSIGNES, utilisateur


def extraire_json(texte):
    texte = re.sub(r"```(?:json)?", "", texte)
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut < 0 or fin < debut:
        raise ValueError("Aucun objet JSON dans la réponse du modèle")
    return json.loads(texte[debut : fin + 1])


def _lignes_en_listes(modele, contenu):
    """Le modèle peut renvoyer des lignes sous forme d'objets : on les remet en listes."""
    for s in modele["sections"]:
        valeur = contenu.get("sections", {}).get(s["id"])
        if s["type"] == "tableau" and isinstance(valeur, list):
            contenu["sections"][s["id"]] = [
                [str(l.get(c, "")) for c in s["colonnes"]] if isinstance(l, dict) else l for l in valeur
            ]
    return contenu


def rediger(type_doc, notes, client=None, modele_ia=MODELE_IA, max_tokens=8000):
    """Appelle le modèle de langage et renvoie (contenu, problèmes de conformité)."""
    if client is None:
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError("Installer le SDK : pip install anthropic") from e
        client = anthropic.Anthropic()
    systeme, utilisateur = construire_prompt(type_doc, notes)
    reponse = client.messages.create(
        model=modele_ia,
        max_tokens=max_tokens,
        system=systeme,
        messages=[{"role": "user", "content": utilisateur}],
    )
    texte = "".join(b.text for b in reponse.content if getattr(b, "type", "") == "text")
    modele = charger(type_doc)
    contenu = _lignes_en_listes(modele, extraire_json(texte))
    contenu["type"] = type_doc
    return contenu, verifier(modele, contenu)
