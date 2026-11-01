"""Ligne de commande : python -m specs_studio <commande>."""

import argparse
import json
import sys
from pathlib import Path

from . import brouillon
from .modeles import TYPES, charger, squelette, verifier
from .rendu import rendre


def _lire(chemin):
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


def _ecrire_json(chemin, contenu):
    Path(chemin).write_text(json.dumps(contenu, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser(prog="specs_studio", description="Spécifications SAP FI/CO : SF, ST, SP.")
    sp = p.add_subparsers(dest="cmd", required=True)

    a = sp.add_parser("modele", help="écrit un contenu vide à remplir")
    a.add_argument("type", choices=TYPES)
    a.add_argument("-o", "--sortie", default="-")

    a = sp.add_parser("verifier", help="contrôle un contenu par rapport à son gabarit")
    a.add_argument("contenu")

    a = sp.add_parser("generer", help="produit le document Word")
    a.add_argument("contenu")
    a.add_argument("-o", "--sortie", required=True)
    a.add_argument("--strict", action="store_true", help="refuse un contenu non conforme")

    a = sp.add_parser("brouillon", help="rédige un premier contenu à partir de notes (IA)")
    a.add_argument("notes")
    a.add_argument("--type", choices=TYPES, required=True)
    a.add_argument("-o", "--sortie", default="brouillon.json")
    a.add_argument("--dry-run", action="store_true", help="affiche la requête sans l'envoyer")

    args = p.parse_args(argv)

    if args.cmd == "modele":
        contenu = squelette(args.type)
        if args.sortie == "-":
            print(json.dumps(contenu, ensure_ascii=False, indent=2))
        else:
            _ecrire_json(args.sortie, contenu)
        return 0

    if args.cmd in ("verifier", "generer"):
        contenu = _lire(args.contenu)
        modele = charger(contenu.get("type", ""))
        problemes = verifier(modele, contenu)
        for pb in problemes:
            print(f"- {pb}", file=sys.stderr)
        if args.cmd == "verifier":
            print("Conforme." if not problemes else f"{len(problemes)} problème(s).")
            return 1 if problemes else 0
        if problemes and args.strict:
            return 1
        print(rendre(modele, contenu, args.sortie))
        return 0

    if args.cmd == "brouillon":
        notes = Path(args.notes).read_text(encoding="utf-8")
        if args.dry_run:
            systeme, utilisateur = brouillon.construire_prompt(args.type, notes)
            print(f"[système]\n{systeme}\n\n[utilisateur]\n{utilisateur}")
            return 0
        contenu, problemes = brouillon.rediger(args.type, notes)
        _ecrire_json(args.sortie, contenu)
        print(f"Brouillon écrit : {args.sortie}")
        for pb in problemes:
            print(f"- à revoir : {pb}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
