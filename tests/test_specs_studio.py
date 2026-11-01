import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from docx import Document

from specs_studio import brouillon
from specs_studio.cli import main
from specs_studio.modeles import TYPES, charger, squelette, verifier
from specs_studio.rendu import rendre

EXEMPLE = Path(__file__).parent.parent / "examples" / "exemple_sf.json"


def texte_docx(chemin):
    d = Document(chemin)
    morceaux = [p.text for p in d.paragraphs]
    for t in d.tables:
        for ligne in t.rows:
            morceaux.extend(c.text for c in ligne.cells)
    return "\n".join(morceaux)


@pytest.mark.parametrize("type_doc", TYPES)
def test_gabarits_coherents(type_doc):
    m = charger(type_doc)
    ids = [s["id"] for s in m["sections"]]
    assert len(ids) == len(set(ids)), "identifiants de section uniques"
    for s in m["sections"]:
        assert s["type"] in ("texte", "liste", "tableau")
        assert s["type"] != "tableau" or s["colonnes"]
    assert any(s.get("obligatoire") for s in m["sections"])


def test_squelette_vide_signale_les_sections_obligatoires():
    pbs = verifier(charger("sf"), squelette("sf"))
    assert any("Objectif du document" in p for p in pbs)
    assert any("Scénarios de test" in p for p in pbs)


def test_exemple_conforme():
    contenu = json.loads(EXEMPLE.read_text(encoding="utf-8"))
    assert verifier(charger("sf"), contenu) == []


def test_verifier_signale_colonnes_et_section_inconnue():
    contenu = json.loads(EXEMPLE.read_text(encoding="utf-8"))
    contenu["sections"]["regles"].append(["R4", "trop court"])
    contenu["sections"]["intrus"] = "x"
    pbs = verifier(charger("sf"), contenu)
    assert any("3 colonnes attendues" in p for p in pbs)
    assert any("Section inconnue : intrus" in p for p in pbs)


def test_rendu_docx_contient_titres_tableaux_et_a_completer(tmp_path):
    contenu = json.loads(EXEMPLE.read_text(encoding="utf-8"))
    del contenu["sections"]["donnees"]
    sortie = tmp_path / "sf.docx"
    rendre(charger("sf"), contenu, sortie)
    texte = texte_docx(sortie)
    assert "1. Objectif du document" in texte
    assert "11. Points ouverts" in texte
    assert "Une facture sans référence de commande est bloquée" in texte
    assert "DEMO-SF-001" in texte
    assert "À compléter" in texte, "une section vide est signalée"
    assert len(Document(sortie).tables) >= 5


@pytest.mark.parametrize("type_doc", ("st", "sp"))
def test_rendu_des_squelettes_st_sp(tmp_path, type_doc):
    sortie = tmp_path / f"{type_doc}.docx"
    rendre(charger(type_doc), squelette(type_doc), sortie)
    assert "À compléter" in texte_docx(sortie)


def test_cli_generer_strict_refuse_un_contenu_incomplet(tmp_path, capsys):
    c = tmp_path / "vide.json"
    c.write_text(json.dumps(squelette("sp")), encoding="utf-8")
    assert main(["generer", str(c), "-o", str(tmp_path / "x.docx"), "--strict"]) == 1
    assert not (tmp_path / "x.docx").exists()
    assert main(["generer", str(c), "-o", str(tmp_path / "y.docx")]) == 0
    assert (tmp_path / "y.docx").exists()


def test_cli_modele_et_verifier(tmp_path):
    c = tmp_path / "m.json"
    assert main(["modele", "st", "-o", str(c)]) == 0
    assert main(["verifier", str(c)]) == 1
    assert main(["verifier", str(EXEMPLE)]) == 0


def test_extraire_json_tolere_les_balises():
    assert brouillon.extraire_json('Voici :\n```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ValueError):
        brouillon.extraire_json("pas de json")


def test_prompt_contient_notes_et_structure():
    systeme, utilisateur = brouillon.construire_prompt("sp", "NOTES-XYZ")
    assert "ne rien inventer" in systeme
    assert "NOTES-XYZ" in utilisateur
    assert '"parametrage"' in utilisateur and '"Valeur"' in utilisateur


def test_rediger_avec_faux_client_remet_les_lignes_en_listes():
    reponse_json = json.dumps(
        {
            "metadonnees": {"Projet": "P"},
            "sections": {
                "objectif": "Paramétrer X.",
                "parametrage": [
                    {"Étape": "1", "Chemin ou transaction": "T", "Paramètre": "p", "Valeur": "v", "Commentaire": ""}
                ],
                "tests": [["T1", "essai", "ok"]],
            },
        }
    )
    appels = []

    class Faux:
        class messages:
            @staticmethod
            def create(**kw):
                appels.append(kw)
                return SimpleNamespace(content=[SimpleNamespace(type="text", text="```json\n" + reponse_json + "\n```")])

    contenu, problemes = brouillon.rediger("sp", "notes", client=Faux)
    assert contenu["type"] == "sp"
    assert contenu["sections"]["parametrage"] == [["1", "T", "p", "v", ""]]
    assert problemes == []
    assert appels[0]["model"] and "notes" in appels[0]["messages"][0]["content"]
