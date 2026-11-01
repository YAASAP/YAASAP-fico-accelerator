"""Rendu Word (.docx) d'un contenu de spécification, mise en forme neutre."""

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from .modeles import est_vide

GRIS = RGBColor(0x6B, 0x72, 0x80)
BLEU = RGBColor(0x1F, 0x3A, 0x5F)


def _ombrage(cellule, couleur):
    pr = cellule._tc.get_or_add_tcPr()
    ombre = OxmlElement("w:shd")
    ombre.set(qn("w:val"), "clear")
    ombre.set(qn("w:color"), "auto")
    ombre.set(qn("w:fill"), couleur)
    pr.append(ombre)


def _champ_page(paragraphe):
    """Insère le numéro de page courant."""
    run = paragraphe.add_run()
    for type_, texte in (("begin", None), (None, "PAGE"), ("end", None)):
        if type_:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), type_)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = texte
        run._r.append(el)


def _a_completer(doc, aide):
    p = doc.add_paragraph()
    r = p.add_run("À compléter" + (f" — {aide}" if aide else ""))
    r.italic = True
    r.font.color.rgb = GRIS


def _tableau(doc, colonnes, lignes):
    t = doc.add_table(rows=1, cols=len(colonnes))
    t.style = "Table Grid"
    for i, nom in enumerate(colonnes):
        cellule = t.rows[0].cells[i]
        cellule.text = ""
        run = cellule.paragraphs[0].add_run(nom)
        run.bold = True
        _ombrage(cellule, "E5E9F0")
    for ligne in lignes:
        if est_vide(ligne):
            continue
        cellules = t.add_row().cells
        for i in range(len(colonnes)):
            cellules[i].text = str(ligne[i]) if i < len(ligne) else ""
    doc.add_paragraph()


def _section(doc, s, valeur):
    if est_vide(valeur):
        _a_completer(doc, s.get("aide"))
    elif s["type"] == "texte":
        paragraphes = valeur if isinstance(valeur, list) else str(valeur).split("\n\n")
        for texte in paragraphes:
            if str(texte).strip():
                doc.add_paragraph(str(texte).strip())
    elif s["type"] == "liste":
        for item in valeur:
            if str(item).strip():
                doc.add_paragraph(str(item).strip(), style="List Bullet")
    elif s["type"] == "tableau":
        _tableau(doc, s["colonnes"], valeur)


def rendre(modele, contenu, chemin):
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10.5)
    meta = contenu.get("metadonnees", {})

    titre = doc.add_heading(meta.get("Titre") or modele["titre"], 0)
    titre.alignment = WD_ALIGN_PARAGRAPH.LEFT
    t = doc.add_table(rows=0, cols=2)
    t.style = "Table Grid"
    for cle in modele["metadonnees"]:
        cellules = t.add_row().cells
        cellules[0].text = cle
        cellules[0].paragraphs[0].runs[0].bold = True
        _ombrage(cellules[0], "E5E9F0")
        cellules[1].text = str(meta.get(cle) or "—")
    doc.add_paragraph()

    for i, s in enumerate(modele["sections"], 1):
        h = doc.add_heading(f"{i}. {s['titre']}", 1)
        for r in h.runs:
            r.font.color.rgb = BLEU
        _section(doc, s, contenu.get("sections", {}).get(s["id"]))

    pied = doc.sections[0].footer.paragraphs[0]
    pied.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pied.add_run(f"{meta.get('Référence') or modele['titre']} — page ")
    _champ_page(pied)
    doc.save(chemin)
    return chemin
