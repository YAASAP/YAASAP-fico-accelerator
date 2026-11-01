# FICO Accelerator — Specs Studio

Génère des spécifications SAP FI/CO au format Word (.docx) à partir de gabarits **génériques** :

- **SF** — spécification fonctionnelle
- **ST** — spécification technique
- **SP** — spécification de paramétrage

Un brouillon peut être rédigé par IA à partir de notes brutes, puis relu et complété.

## Installation

```
pip install -e ".[ia,test]"
```

## Utilisation

```
python -m specs_studio modele sf -o sf.json          # squelette à remplir
python -m specs_studio verifier sf.json              # contrôle (sections obligatoires, colonnes)
python -m specs_studio generer sf.json -o sf.docx    # --strict refuse un contenu incomplet
python -m specs_studio brouillon notes.txt --type sp -o sp.json   # brouillon IA (ANTHROPIC_API_KEY requis)
python -m specs_studio brouillon notes.txt --type sp --dry-run    # affiche le prompt sans appel
```

Un exemple fictif est fourni : `examples/exemple_sf.json` → `examples/exemple_sf.docx`.
Le modèle IA se règle avec la variable `SPECS_STUDIO_MODELE`.

## Règles du projet

- Gabarits génériques uniquement. Ne jamais importer de gabarit, de document ou de donnée d'un client ou d'un ancien employeur.
- Aucune donnée client dans le dépôt (`sorties/` est ignoré par git). Aucun secret ni clé commités.
- Le brouillon IA ne doit rien inventer : les informations manquantes restent « À compléter ».
- Pour un usage commercial : hébergement UE, pas d'entraînement sur les données clients, à préciser dans les CGU.

## Tests

```
python -m pytest
```
