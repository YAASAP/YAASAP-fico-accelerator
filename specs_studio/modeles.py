"""Chargement, squelette et validation des gabarits SF, ST et SP."""

import json
from pathlib import Path

TYPES = ("sf", "st", "sp")
_DIR = Path(__file__).parent / "gabarits"


def charger(type_doc):
    if type_doc not in TYPES:
        raise ValueError(f"Type inconnu : {type_doc!r} (attendu : {', '.join(TYPES)})")
    return json.loads((_DIR / f"{type_doc}.json").read_text(encoding="utf-8"))


def squelette(type_doc):
    """Contenu vide, prêt à être rempli à la main ou par le brouillon IA."""
    modele = charger(type_doc)
    sections = {}
    for s in modele["sections"]:
        if s["type"] == "tableau":
            sections[s["id"]] = [[""] * len(s["colonnes"])]
        elif s["type"] == "liste":
            sections[s["id"]] = [""]
        else:
            sections[s["id"]] = ""
    return {"type": type_doc, "metadonnees": {k: "" for k in modele["metadonnees"]}, "sections": sections}


def est_vide(valeur):
    if valeur is None:
        return True
    if isinstance(valeur, str):
        return not valeur.strip()
    if isinstance(valeur, list):
        return all(est_vide(v) for v in valeur)
    return False


def verifier(modele, contenu):
    """Renvoie la liste des problèmes (vide si le contenu est conforme)."""
    problemes = []
    sections = contenu.get("sections", {})
    connus = {s["id"] for s in modele["sections"]}
    for cle in sections:
        if cle not in connus:
            problemes.append(f"Section inconnue : {cle}")
    for s in modele["sections"]:
        valeur = sections.get(s["id"])
        if s.get("obligatoire") and est_vide(valeur):
            problemes.append(f"Section obligatoire vide : {s['titre']}")
        if s["type"] == "tableau" and isinstance(valeur, list):
            n = len(s["colonnes"])
            for i, ligne in enumerate(valeur, 1):
                if not isinstance(ligne, list) or len(ligne) != n:
                    problemes.append(f"{s['titre']}, ligne {i} : {n} colonnes attendues")
    return problemes
