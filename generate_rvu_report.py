"""
Generates the complete, properly formatted RV University B.Tech (Honours) Project Report (.docx)
adhering strictly to the formatting specifications in `/Users/prathikkb/Downloads/RV university report format.docx`:
- Paper size: A4 (21.0 cm x 29.7 cm)
- Margins: Left = 3.81 cm (1.5 in), Right = 2.54 cm (1.0 in), Top = 2.54 cm (1.0 in), Bottom = 2.54 cm (1.0 in)
- Font: Times New Roman throughout
- Body text: 12 pt, Justified, 1.5 line spacing
- Chapter Heading: 16 pt, Bold, Times New Roman
- Section Heading: 14 pt, Bold, Times New Roman, ALL CAPS
- Subsection Heading: 12 pt, Bold, Times New Roman, ALL CAPS
- Captions: 10.5 pt, Times New Roman, Centered
- Page numbering: Bottom center (Roman numerals i, ii, iii... for front matter; Arabic 1, 2, 3... for main body)
"""

import json
import shutil
from pathlib import Path
import docx
from docx import Document
from docx.shared import Cm, Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls


PROJECT_DIR = Path("/Users/prathikkb/Documents/NLP")
OUTPUTS_DIR = PROJECT_DIR / "outputs"
LOGO_PATH = Path("/Users/prathikkb/.gemini/antigravity-acp/brain/4dbd5f76-69ff-4492-a46a-3686f87d0005/scratch/image1.png")
REPORT_OUT_PROJECT = PROJECT_DIR / "RVU_FinNLP_Project_Report.docx"
REPORT_OUT_DOWNLOADS = Path("/Users/prathikkb/Downloads/RVU_FinNLP_Project_Report.docx")


def set_cell_background(cell, fill_hex: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=140, right=140):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{m}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def add_page_number_to_footer(section, fmt: str = "decimal", restart_at: int = None):
    """Adds a centered PAGE field to the footer and configures page number format (lowerRoman or decimal)."""
    footer = section.footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)

    run = p.add_run()
    run.font.name = "Times New Roman"
    run.font.size = Pt(11)

    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = "PAGE"
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "separate")
    fldChar3 = OxmlElement("w:fldChar")
    fldChar3.set(qn("w:fldCharType"), "end")

    r = run._r
    r.append(fldChar1)
    r.append(instrText)
    r.append(fldChar2)
    r.append(fldChar3)

    sectPr = section._sectPr
    pgNumType = sectPr.find(qn("w:pgNumType"))
    if pgNumType is None:
        pgNumType = OxmlElement("w:pgNumType")
        sectPr.append(pgNumType)
    pgNumType.set(qn("w:fmt"), fmt)
    if restart_at is not None:
        pgNumType.set(qn("w:start"), str(restart_at))


def configure_a4_margins(section):
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3.81)   # 1.5 inches (RVU standard binding margin)
    section.right_margin = Cm(2.54)  # 1.0 inch
    section.top_margin = Cm(2.54)    # 1.0 inch
    section.bottom_margin = Cm(2.54) # 1.0 inch


def add_formatted_paragraph(
    doc,
    text: str = "",
    size_pt: float = 12.0,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    align=WD_ALIGN_PARAGRAPH.JUSTIFY,
    line_spacing: float = 1.5,
    space_before_pt: float = 0.0,
    space_after_pt: float = 6.0,
    first_line_indent_cm: float = 0.0,
    color_rgb=None,
):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.line_spacing = line_spacing
    pf.space_before = Pt(space_before_pt)
    pf.space_after = Pt(space_after_pt)
    if first_line_indent_cm > 0:
        pf.first_line_indent = Cm(first_line_indent_cm)
    if text:
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(size_pt)
        run.bold = bold
        run.italic = italic
        run.underline = underline
        if color_rgb:
            run.font.color.rgb = RGBColor(*color_rgb)
    return p


def add_chapter_heading(doc, chapter_num: int, title: str, start_new_page: bool = True):
    if start_new_page:
        doc.add_page_break()
    p = add_formatted_paragraph(
        doc,
        f"Chapter {chapter_num}: {title}",
        size_pt=16.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        line_spacing=1.5,
        space_before_pt=6.0,
        space_after_pt=12.0,
    )
    return p


def add_section_heading(doc, sec_num: str, title: str):
    p = add_formatted_paragraph(
        doc,
        f"{sec_num} {title.upper()}",
        size_pt=14.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        line_spacing=1.5,
        space_before_pt=12.0,
        space_after_pt=6.0,
    )
    return p


def add_subsection_heading(doc, subsec_num: str, title: str):
    p = add_formatted_paragraph(
        doc,
        f"{subsec_num} {title.upper()}",
        size_pt=12.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        line_spacing=1.5,
        space_before_pt=8.0,
        space_after_pt=4.0,
    )
    return p


def add_body_paragraph(doc, text: str):
    return add_formatted_paragraph(
        doc,
        text,
        size_pt=12.0,
        bold=False,
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        line_spacing=1.5,
        space_before_pt=0.0,
        space_after_pt=6.0,
    )


def add_bullet_item(doc, bold_prefix: str, rest_text: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.line_spacing = 1.5
    pf.left_indent = Cm(0.75)
    pf.space_before = Pt(0)
    pf.space_after = Pt(4)

    r_b = p.add_run(f"• {bold_prefix}: ")
    r_b.font.name = "Times New Roman"
    r_b.font.size = Pt(12)
    r_b.bold = True

    r_t = p.add_run(rest_text)
    r_t.font.name = "Times New Roman"
    r_t.font.size = Pt(12)
    return p


def add_styled_table(doc, caption: str, headers: list, rows: list, col_widths_cm: list = None):
    # Table caption above table (standard academic convention)
    add_formatted_paragraph(
        doc,
        caption,
        size_pt=11.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.15,
        space_before_pt=10.0,
        space_after_pt=4.0,
    )
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header row
    hdr_cells = table.rows[0].cells
    for idx, h_text in enumerate(headers):
        cell = hdr_cells[idx]
        set_cell_background(cell, "E2E8F0")
        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(str(h_text))
        run.font.name = "Times New Roman"
        run.font.size = Pt(11)
        run.bold = True

    # Data rows
    for r_idx, r_data in enumerate(rows):
        row_cells = table.rows[r_idx + 1].cells
        is_last_summary = (r_idx == len(rows) - 1) and any(
            k in str(r_data[0]).lower() for k in ["hybrid ensemble", "macro average", "total"]
        )
        for c_idx, val in enumerate(r_data):
            cell = row_cells[c_idx]
            if is_last_summary:
                set_cell_background(cell, "F8FAFC")
            set_cell_margins(cell, top=65, bottom=65, left=100, right=100)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if c_idx == 0 else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            run = p.add_run(str(val))
            run.font.name = "Times New Roman"
            run.font.size = Pt(10.5)
            if is_last_summary:
                run.bold = True

    if col_widths_cm:
        for row in table.rows:
            for idx, w_cm in enumerate(col_widths_cm):
                if idx < len(row.cells):
                    row.cells[idx].width = Cm(w_cm)

    add_formatted_paragraph(doc, "", size_pt=6.0, space_after_pt=4.0)
    return table


def add_figure_with_caption(doc, img_path: Path, caption: str, width_inches: float = 5.6):
    if img_path.exists():
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(2)
        run = p_img.add_run()
        run.add_picture(str(img_path), width=Inches(width_inches))

    add_formatted_paragraph(
        doc,
        caption,
        size_pt=10.5,
        bold=True,
        italic=False,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.15,
        space_before_pt=2.0,
        space_after_pt=10.0,
    )


def build_report():
    with open(OUTPUTS_DIR / "evaluation_report.json") as f:
        eval_data = json.load(f)

    doc = Document()

    # Configure default Normal style to Times New Roman 12pt
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Times New Roman"
    normal_style.font.size = Pt(12)

    # =========================================================================
    # SECTION 0: COVER PAGE (No page number on cover, followed by Roman i, ii...)
    # =========================================================================
    sec_cover = doc.sections[0]
    configure_a4_margins(sec_cover)
    sec_cover.different_first_page_header_footer = True
    add_page_number_to_footer(sec_cover, fmt="lowerRoman", restart_at=1)

    if LOGO_PATH.exists():
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_logo.paragraph_format.space_after = Pt(6)
        r_logo = p_logo.add_run()
        r_logo.add_picture(str(LOGO_PATH), width=Inches(2.5))

    add_formatted_paragraph(
        doc,
        "RV UNIVERSITY",
        size_pt=18.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.15,
        space_before_pt=2.0,
        space_after_pt=2.0,
    )
    add_formatted_paragraph(
        doc,
        "School of Computer Science and Engineering",
        size_pt=15.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.15,
        space_before_pt=0.0,
        space_after_pt=10.0,
    )

    add_formatted_paragraph(
        doc,
        "ROBUST NLP FRAMEWORK FOR AUTOMATED FINANCIAL TRANSACTION EXTRACTION AND EXPENSE CATEGORIZATION",
        size_pt=18.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.25,
        space_before_pt=6.0,
        space_after_pt=10.0,
    )

    add_formatted_paragraph(
        doc,
        "Submitted in partial fulfillment of the Requirements for the Degree of",
        size_pt=13.0,
        italic=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.15,
        space_before_pt=2.0,
        space_after_pt=4.0,
    )

    add_formatted_paragraph(
        doc,
        "Bachelor of Technology (Honours)\nin\nComputer Science and Engineering",
        size_pt=18.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.2,
        space_before_pt=2.0,
        space_after_pt=10.0,
    )

    add_formatted_paragraph(
        doc,
        "By",
        size_pt=13.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.15,
        space_before_pt=2.0,
        space_after_pt=4.0,
    )

    # Candidate Table on Cover Page
    cand_table = doc.add_table(rows=5, cols=2)
    cand_table.style = "Table Grid"
    cand_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    candidates = [
        ("NAME OF THE CANDIDATES", "USN"),
        ("PREKSHA P V", "1RUA24CSE0331"),
        ("RESHMA K P", "1RUA24CSE0363"),
        ("PRATHIK K B", "1RUA24CSE0327"),
        ("RUSHIL RAVI REDDY", "1RUA24CSE0380"),
    ]
    for r_i, (c_name, c_usn) in enumerate(candidates):
        row = cand_table.rows[r_i]
        for c_i, val in enumerate([c_name, c_usn]):
            cell = row.cells[c_i]
            if r_i == 0:
                set_cell_background(cell, "E2E8F0")
            set_cell_margins(cell, top=60, bottom=60, left=120, right=120)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            r = p.add_run(val)
            r.font.name = "Times New Roman"
            r.font.size = Pt(13)
            r.bold = True

    add_formatted_paragraph(
        doc,
        "Guided by",
        size_pt=13.0,
        italic=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.15,
        space_before_pt=10.0,
        space_after_pt=2.0,
    )
    add_formatted_paragraph(
        doc,
        "PROF. KHUSHBOO PANDEY\nPROF. PRIYANKA S SHIVARAMAIAH\nSchool of Computer Science and Engineering, RV University",
        size_pt=14.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.2,
        space_before_pt=0.0,
        space_after_pt=10.0,
    )
    add_formatted_paragraph(
        doc,
        "School of Computer Science and Engineering\nRV University\nRV Vidyaniketan Post, 8th Mile, Mysuru Road, Bengaluru - 560059\n2025 - 2026",
        size_pt=13.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.2,
        space_before_pt=4.0,
        space_after_pt=0.0,
    )

    # =========================================================================
    # PAGE ii: CERTIFICATE
    # =========================================================================
    doc.add_page_break()
    if LOGO_PATH.exists():
        p_logo2 = doc.add_paragraph()
        p_logo2.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_logo2.paragraph_format.space_after = Pt(4)
        p_logo2.add_run().add_picture(str(LOGO_PATH), width=Inches(2.3))

    add_formatted_paragraph(
        doc,
        "SCHOOL OF COMPUTER SCIENCE AND ENGINEERING",
        size_pt=14.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.2,
        space_before_pt=4.0,
        space_after_pt=8.0,
    )
    add_formatted_paragraph(
        doc,
        "CERTIFICATE",
        size_pt=16.0,
        bold=True,
        underline=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.5,
        space_before_pt=6.0,
        space_after_pt=12.0,
    )

    cert_text = (
        "Certified that the Project work titled “ROBUST NLP FRAMEWORK FOR AUTOMATED FINANCIAL "
        "TRANSACTION EXTRACTION AND EXPENSE CATEGORIZATION” is carried out by Preksha P V "
        "(1RUA24CSE0331), Reshma K P (1RUA24CSE0363), Prathik K B (1RUA24CSE0327), and Rushil Ravi Reddy "
        "(1RUA24CSE0380), bonafide students of School of Computer Science and Engineering, RV University, "
        "Bengaluru, in partial fulfillment for the award of Degree of Bachelor of Technology (Honours) in "
        "Computer Science and Engineering of the RV University, Bengaluru, during the academic year 2025-2026. "
        "It is certified that all corrections and suggestions indicated for the Internal Assessment have been "
        "incorporated in the final report deposited in the departmental library. The project report has been "
        "approved as it satisfies the academic requirements in respect of project work prescribed for the "
        "Bachelor of Technology (Honours) Degree."
    )
    add_body_paragraph(doc, cert_text)

    add_formatted_paragraph(doc, "", size_pt=12.0, space_after_pt=18.0)

    sig_table = doc.add_table(rows=2, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sigs = [
        (
            "_______________________________\nSignature of the Guides\nProf. Khushboo Pandey\nProf. Priyanka S Shivaramaiah\nSchool of CSE, RV University",
            "_______________________________\nSignature of the Program Director\nDr. Rashmi S\nProgram Director - B.Tech(H)\nSchool of CSE, RV University",
        ),
        (
            "_______________________________\nSignature of the Mentor\nSchool of CSE\nRV University, Bengaluru",
            "_______________________________\nSignature of the Dean\nProf. Dr. Shobha G\nDean, School of CSE\nRV University, Bengaluru",
        ),
    ]
    for r_i in range(2):
        for c_i in range(2):
            cell = sig_table.rows[r_i].cells[c_i]
            set_cell_margins(cell, top=160, bottom=160, left=100, right=100)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing = 1.2
            r = p.add_run(sigs[r_i][c_i])
            r.font.name = "Times New Roman"
            r.font.size = Pt(11.5)
            r.bold = True

    add_formatted_paragraph(
        doc,
        "External Viva",
        size_pt=12.0,
        bold=True,
        underline=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before_pt=16.0,
        space_after_pt=6.0,
    )
    viva_table = doc.add_table(rows=3, cols=2)
    viva_table.style = "Table Grid"
    viva_rows = [
        ("Name of the Examiners", "Signature with Date"),
        ("1. ", ""),
        ("2. ", ""),
    ]
    for r_i, (c1, c2) in enumerate(viva_rows):
        for c_i, val in enumerate([c1, c2]):
            cell = viva_table.rows[r_i].cells[c_i]
            set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.2
            r = p.add_run(val)
            r.font.name = "Times New Roman"
            r.font.size = Pt(11.5)
            if r_i == 0:
                r.bold = True

    # =========================================================================
    # PAGE iii: DECLARATION BY THE CANDIDATES
    # =========================================================================
    doc.add_page_break()
    if LOGO_PATH.exists():
        p_logo3 = doc.add_paragraph()
        p_logo3.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_logo3.paragraph_format.space_after = Pt(6)
        p_logo3.add_run().add_picture(str(LOGO_PATH), width=Inches(2.3))

    add_formatted_paragraph(
        doc,
        "DECLARATION",
        size_pt=14.0,
        bold=True,
        underline=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.5,
        space_before_pt=12.0,
        space_after_pt=18.0,
    )

    decl_text = (
        "We, Preksha P V (1RUA24CSE0331), Reshma K P (1RUA24CSE0363), Prathik K B (1RUA24CSE0327), "
        "and Rushil Ravi Reddy (1RUA24CSE0380), students of Bachelor of Technology (Honours) in Computer "
        "Science and Engineering, RV University, Bengaluru, hereby declare that the project titled "
        "“ROBUST NLP FRAMEWORK FOR AUTOMATED FINANCIAL TRANSACTION EXTRACTION AND EXPENSE CATEGORIZATION” "
        "has been carried out by us under the supervision of our guides Prof. Khushboo Pandey and "
        "Prof. Priyanka S Shivaramaiah, School of Computer Science and Engineering, RV University, and "
        "submitted in partial fulfillment of the requirements for the award of the Degree in Bachelor of "
        "Technology (Honours) in Computer Science and Engineering by RV University during the academic year "
        "2025-2026. We further declare that the report has not been submitted to any other University for "
        "the award of any other degree or diploma."
    )
    add_body_paragraph(doc, decl_text)

    add_formatted_paragraph(
        doc,
        "\nPlace: Bengaluru\nDate: November 2026",
        size_pt=12.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before_pt=24.0,
        space_after_pt=24.0,
    )

    add_formatted_paragraph(
        doc,
        "Name and Signature of the Candidates:\n\n"
        "1. PREKSHA P V (1RUA24CSE0331)                       _______________________\n\n"
        "2. RESHMA K P (1RUA24CSE0363)                         _______________________\n\n"
        "3. PRATHIK K B (1RUA24CSE0327)                        _______________________\n\n"
        "4. RUSHIL RAVI REDDY (1RUA24CSE0380)            _______________________",
        size_pt=12.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        line_spacing=1.5,
    )

    # =========================================================================
    # PAGE iv: ABSTRACT
    # =========================================================================
    doc.add_page_break()
    if LOGO_PATH.exists():
        p_logo4 = doc.add_paragraph()
        p_logo4.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_logo4.paragraph_format.space_after = Pt(6)
        p_logo4.add_run().add_picture(str(LOGO_PATH), width=Inches(2.3))

    add_formatted_paragraph(
        doc,
        "ABSTRACT",
        size_pt=14.0,
        bold=True,
        underline=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.5,
        space_before_pt=12.0,
        space_after_pt=14.0,
    )

    abstract_p1 = (
        "The rapid proliferation of digital payment ecosystems in India—spearheaded by the Unified Payments "
        "Interface (UPI), Immediate Payment Service (IMPS), National Electronic Funds Transfer (NEFT), and "
        "Point-of-Sale (POS) card networks—has resulted in billions of unstructured financial SMS and push "
        "notification alerts being generated daily. While these transactional alerts contain vital personal "
        "finance metadata, they are transmitted in highly heterogeneous, noisy, and abbreviated formats across "
        "English, indigenous Indic scripts (Hindi, Kannada, Tamil, Telugu, and Bengali), and colloquial "
        "code-mixed transliterations (Hinglish, Kanglish, and Tanglish). Existing commercial expense trackers "
        "rely predominantly on brittle, English-only regular expressions or require uploading sensitive banking "
        "messages to third-party cloud servers, creating severe privacy risks and failing on regional or "
        "code-mixed Indian banking alerts."
    )
    abstract_p2 = (
        "To address these limitations, this project presents a Dual-Tier Hybrid Natural Language Processing "
        "(NLP) Framework for Automated Financial Transaction Extraction and Expense Categorization. First, we "
        "design a script-aware Multilingual Preprocessor that performs Unicode NFKC normalization, strips LLM "
        "instruction wrappers, detects script composition across 6 Indian languages plus code-mixed text, and "
        "translates regional banking terminology into canonical financial tokens. Second, we engineer a Hybrid "
        "Financial Entity Extractor that combines deterministic structural regular expressions with contextual "
        "Named Entity Recognition (NER) heuristics to extract seven critical fields: Transaction Amount, "
        "Transaction Type (Debit/Credit), Bank Name, Masked Account Number, Date, 12-digit UPI Reference ID, "
        "and Merchant/Beneficiary Name, while automatically distinguishing Person-to-Merchant (P2M) commercial "
        "payments from Person-to-Person (P2P) transfers. Third, we implement and benchmark a Multi-Model "
        "Expense Categorization suite spanning 13 granular categories (mapped to 7 Synopsis macro-categories, "
        "including a dedicated Education taxonomy) using a Rule-Based Merchant/VPA Lexicon, Word + Character "
        "Subword TF-IDF (3–5 character n-grams) with Calibrated Linear Support Vector Machines (LinearSVC), "
        "Multinomial Logistic Regression, LightGBM, a fine-tuned Multilingual Transformer (Google MuRIL "
        "BertForSequenceClassification), and a confidence-weighted Hybrid Ensemble Pipeline."
    )
    abstract_p3 = (
        "Furthermore, to enable 100% privacy-preserving on-device execution without internet connectivity, we "
        "mathematically fold the calibrated LinearSVC and Logistic Regression subword TF-IDF weights into a "
        "compact 1.01 MB JSON weight matrix deployed inside a native Kotlin & Jetpack Compose (Material 3) "
        "Android application equipped with live SMS BroadcastReceiver and NotificationListenerService daemons. "
        "Evaluated on a stratified benchmark of 1,200 multilingual and code-mixed transactions derived from the "
        "152,000+ FinEE corpus and realistic Indian code-mixed/education augmentations, our Hybrid Entity "
        "Extractor achieves a Macro Precision of 95.96%, Macro Recall of 93.76%, and Macro F1-Score of 94.82% "
        "(with 99.46% F1 on Amount and 100.00% F1 on Account and Date). In expense categorization, our Hybrid "
        "Ensemble achieves 91.17% overall accuracy and 90.62% Weighted F1—outperforming standalone LinearSVC "
        "(83.50%) by +7.67% and Rule-Based Lexicons (80.42%) by +10.75%—while delivering sub-millisecond "
        "(< 1 ms) inference latency on Android mobile devices."
    )
    add_body_paragraph(doc, abstract_p1)
    add_body_paragraph(doc, abstract_p2)
    add_body_paragraph(doc, abstract_p3)
    add_formatted_paragraph(
        doc,
        "Keywords: Financial NLP, Named Entity Recognition (NER), Expense Categorization, Code-Mixed Hinglish/Kanglish, Subword TF-IDF, MuRIL Transformer, On-Device Android Edge AI.",
        size_pt=12.0,
        bold=True,
        italic=True,
        align=WD_ALIGN_PARAGRAPH.JUSTIFY,
        space_before_pt=6.0,
    )

    # =========================================================================
    # PAGE v: ACKNOWLEDGEMENT
    # =========================================================================
    doc.add_page_break()
    if LOGO_PATH.exists():
        p_logo5 = doc.add_paragraph()
        p_logo5.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_logo5.paragraph_format.space_after = Pt(6)
        p_logo5.add_run().add_picture(str(LOGO_PATH), width=Inches(2.3))

    add_formatted_paragraph(
        doc,
        "ACKNOWLEDGEMENT",
        size_pt=14.0,
        bold=True,
        underline=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_spacing=1.5,
        space_before_pt=12.0,
        space_after_pt=14.0,
    )

    ack_paragraphs = [
        "We are indebted to our guides, Prof. Khushboo Pandey and Prof. Priyanka S Shivaramaiah, School of Computer Science and Engineering, RV University, for their wholehearted support, patient guidance, and insightful technical feedback throughout the conception, architectural design, model training, and mobile deployment phases of this project work.",
        "We are also grateful to our panel examiners and faculty mentors for their constructive comments and valuable suggestions during the periodic project evaluations, which helped us significantly refine our multilingual evaluation benchmarks and edge deployment pipeline.",
        "Our sincere thanks to Prof. Dr. Ram Kumar Kakani, Vice Chancellor, RV University, for fostering an environment of academic excellence, interdisciplinary research, and innovation.",
        "We express our heartfelt gratitude to Prof. Dr. Shobha G, Dean, School of Computer Science and Engineering, and Dr. Rashmi S, Program Director - B.Tech (Honours), School of Computer Science and Engineering, RV University, for their continuous encouragement and for providing the computational infrastructure required to complete this work.",
        "We also extend our sincere appreciation to all the teaching and non-teaching staff of the School of Computer Science and Engineering, RV University, and to our parents and peers for their unwavering moral support.",
    ]
    for ap in ack_paragraphs:
        add_body_paragraph(doc, ap)

    add_formatted_paragraph(
        doc,
        "\nPREKSHA P V (1RUA24CSE0331)\nRESHMA K P (1RUA24CSE0363)\nPRATHIK K B (1RUA24CSE0327)\nRUSHIL RAVI REDDY (1RUA24CSE0380)",
        size_pt=12.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.RIGHT,
        space_before_pt=16.0,
    )

    # =========================================================================
    # PAGE vi: TABLE OF CONTENTS
    # =========================================================================
    doc.add_page_break()
    add_formatted_paragraph(
        doc,
        "CONTENTS",
        size_pt=14.0,
        bold=True,
        underline=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_before_pt=6.0,
        space_after_pt=12.0,
    )

    toc_rows = [
        ("Certificate", "ii"),
        ("Declaration", "iii"),
        ("Abstract", "iv"),
        ("Acknowledgement", "v"),
        ("Table of Contents", "vi"),
        ("List of Figures", "vii"),
        ("List of Tables", "viii"),
        ("List of Acronyms", "ix"),
        ("Chapter 1: Introduction", "1"),
        ("    1.1 INTRODUCTION", "1"),
        ("    1.2 PROBLEM STATEMENT", "2"),
        ("    1.3 OBJECTIVES", "2"),
        ("    1.4 SCOPE OF THE PROJECT", "3"),
        ("Chapter 2: Background", "4"),
        ("    2.1 LITERATURE SURVEY", "4"),
        ("    2.2 RESEARCH GAPS IDENTIFIED", "6"),
        ("    2.3 TOOLS AND TECHNIQUES", "6"),
        ("Chapter 3: Methodology", "8"),
        ("    3.1 PROPOSED METHODOLOGY", "8"),
        ("    3.2 MULTILINGUAL & CODE-MIXED PREPROCESSING ENGINE", "9"),
        ("    3.3 HYBRID FINANCIAL ENTITY EXTRACTOR (NER)", "10"),
        ("    3.4 MULTI-MODEL EXPENSE CATEGORIZATION ENGINE", "11"),
        ("    3.5 MATHEMATICAL WEIGHT FOLDING FOR NATIVE ANDROID EDGE", "12"),
        ("Chapter 4: Implementation", "14"),
        ("    4.1 DATASETS", "14"),
        ("    4.2 IMPLEMENTATION MODULES (SERVER & ANDROID APP)", "15"),
        ("    4.3 EXPERIMENTAL SETUP", "17"),
        ("Chapter 5: Results", "18"),
        ("    5.1 ENTITY EXTRACTION RESULTS", "18"),
        ("    5.2 EXPENSE CATEGORIZATION RESULT SUMMARY TABLES", "19"),
        ("    5.3 ANALYSIS OF RESULTS & CONFUSION MATRIX", "21"),
        ("    5.4 MULTILINGUAL & CODE-MIXED PERFORMANCE BREAKDOWN", "23"),
        ("    5.5 COMPARISON WITH EXISTING METHODS & DUAL-TIER FOOTPRINT", "24"),
        ("Chapter 6: Inferences", "26"),
        ("    6.1 KEY FINDINGS", "26"),
        ("    6.2 FULFILLMENT OF PROJECT OBJECTIVES", "27"),
        ("Chapter 7: Impression Report", "28"),
        ("    7.1 PERSONAL LEARNING EXPERIENCE", "28"),
        ("    7.2 SKILL ENHANCEMENT", "28"),
        ("    7.3 INDUSTRY AND ACADEMIC RELEVANCE", "29"),
        ("Chapter 8: Conclusion and Future Work", "30"),
        ("    8.1 CONCLUSION", "30"),
        ("    8.2 FUTURE WORK", "30"),
        ("References", "32"),
        ("Appendix 1: Core Hybrid Pipeline & Android Kotlin Engine Listings", "34"),
        ("Appendix 2: Sample Multilingual & Code-Mixed Test Cases", "37"),
    ]
    add_styled_table(
        doc,
        "Table of Contents",
        ["Chapter / Section Title", "Page No."],
        toc_rows,
        col_widths_cm=[12.0, 2.5],
    )

    # =========================================================================
    # PAGE vii: LIST OF FIGURES & PAGE viii: LIST OF TABLES & ACRONYMS
    # =========================================================================
    doc.add_page_break()
    add_formatted_paragraph(
        doc,
        "LIST OF FIGURES",
        size_pt=14.0,
        bold=True,
        underline=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_before_pt=6.0,
        space_after_pt=10.0,
    )
    lof_rows = [
        ("Figure 3.1", "Dual-Tier Hybrid Financial NLP System Architecture (Cloud Server + Native Android Edge)", "8"),
        ("Figure 5.1", "Hybrid Entity Extractor Precision, Recall, and F1-Score Across 7 Financial Entities", "19"),
        ("Figure 5.2", "Expense Categorization Performance Comparison Across 5 Classifier Architectures", "20"),
        ("Figure 5.3", "Confusion Matrix Heatmap of the Hybrid Ensemble Categorizer Across 13 Categories", "22"),
        ("Figure 5.4", "Multilingual and Code-Mixed Categorization Accuracy and Macro F1 Across 7 Language Groups", "23"),
    ]
    add_styled_table(
        doc,
        "List of Figures",
        ["Figure No.", "Figure Caption", "Page No."],
        lof_rows,
        col_widths_cm=[2.5, 9.8, 2.2],
    )

    add_formatted_paragraph(
        doc,
        "LIST OF TABLES",
        size_pt=14.0,
        bold=True,
        underline=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_before_pt=14.0,
        space_after_pt=10.0,
    )
    lot_rows = [
        ("Table 2.1", "Summary of Chronological Literature Survey in Financial NLP and Transaction Categorization", "5"),
        ("Table 3.1", "Mapping Between 13 Granular FinEE Categories and 7 Project Synopsis Macro-Categories", "11"),
        ("Table 4.1", "Language-Wise Distribution of the Stratified Test Benchmark (N = 1,200 Transactions)", "14"),
        ("Table 4.2", "Category-Wise Support Distribution of the Test Dataset Across 13 Financial Classes", "15"),
        ("Table 5.1", "Entity Extraction Precision, Recall, and F1-Score Across 7 Financial Fields (N = 4,986 Entities)", "18"),
        ("Table 5.2", "Comparative Evaluation of Expense Categorization Models on the Test Benchmark (N = 1,200)", "20"),
        ("Table 5.3", "Per-Category Precision, Recall, F1-Score, and Support for the Hybrid Ensemble Framework", "21"),
        ("Table 5.4", "Multilingual and Code-Mixed Categorization Performance Breakdown Across 7 Languages", "23"),
        ("Table 5.5", "Hardware Footprint, RAM Usage, and Latency Comparison: Mac Server vs. Android Edge App", "25"),
        ("Table 6.1", "Mapping of Project Synopsis Objectives to Implemented Modules and Verified Outcomes", "27"),
    ]
    add_styled_table(
        doc,
        "List of Tables",
        ["Table No.", "Table Caption", "Page No."],
        lot_rows,
        col_widths_cm=[2.5, 9.8, 2.2],
    )

    doc.add_page_break()
    add_formatted_paragraph(
        doc,
        "LIST OF ACRONYMS",
        size_pt=14.0,
        bold=True,
        underline=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_before_pt=6.0,
        space_after_pt=10.0,
    )
    acronyms = [
        ("NLP", "Natural Language Processing"),
        ("NER", "Named Entity Recognition"),
        ("UPI", "Unified Payments Interface"),
        ("VPA", "Virtual Payment Address"),
        ("IMPS / NEFT / RTGS", "Immediate Payment Service / National Electronic Funds Transfer / Real-Time Gross Settlement"),
        ("POS", "Point of Sale"),
        ("P2M / P2P", "Person-to-Merchant / Person-to-Person Transaction"),
        ("TF-IDF", "Term Frequency – Inverse Document Frequency"),
        ("SVM / LinearSVC", "Support Vector Machine / Linear Support Vector Classification"),
        ("MuRIL", "Multilingual Representations for Indian Languages (Google BERT Architecture)"),
        ("LightGBM", "Light Gradient Boosting Machine"),
        ("NFKC", "Normalization Form Compatibility Composition (Unicode Standard)"),
        ("F1-Score", "Harmonic Mean of Precision and Recall"),
        ("APK", "Android Package Kit"),
    ]
    add_styled_table(
        doc,
        "List of Acronyms and Abbreviations",
        ["Acronym", "Full Expansion"],
        acronyms,
        col_widths_cm=[4.0, 10.5],
    )

    # =========================================================================
    # START MAIN BODY SECTION WITH ARABIC PAGE NUMBERS (1, 2, 3...)
    # =========================================================================
    sec_main = doc.add_section(WD_SECTION.NEW_PAGE)
    configure_a4_margins(sec_main)
    sec_main.different_first_page_header_footer = False
    add_page_number_to_footer(sec_main, fmt="decimal", restart_at=1)

    # =========================================================================
    # CHAPTER 1: INTRODUCTION
    # =========================================================================
    add_chapter_heading(doc, 1, "Introduction", start_new_page=False)

    add_section_heading(doc, "1.1", "INTRODUCTION")
    add_body_paragraph(
        doc,
        "India's financial landscape has undergone a historic digital transformation over the past decade, driven "
        "by the National Payments Corporation of India (NPCI) and the widespread adoption of the Unified Payments "
        "Interface (UPI). Processing over 14 billion monthly transactions across hundreds of commercial, public-sector, "
        "and regional rural banks, every digital payment—whether via UPI, IMPS, NEFT, RTGS, Debit/Credit card swipe, "
        "or automated standing instruction (Mandate/EMI)—triggers an instantaneous notification delivered via Short "
        "Message Service (SMS) or mobile push notification. These unstructured alerts serve as an immutable, real-time "
        "audit trail of an individual's financial activity."
    )
    add_body_paragraph(
        doc,
        "Despite the richness of this transactional data, converting raw banking SMS streams into structured personal "
        "finance analytics remains a formidable Natural Language Processing (NLP) challenge. Unlike standardized "
        "ISO-20022 bank statements or Open Banking API payloads, SMS alerts are crafted independently by each bank's "
        "IT vendor to fit within strict 160-character cellular payload constraints. Consequently, messages exhibit "
        "extreme syntactic variability, non-standard abbreviations ('A/c', 'debtd', 'Avl Bal', 'Info:', 'Ref No'), "
        "truncation of merchant names, and dynamic Virtual Payment Addresses (VPAs such as 'swiggy@ybl' or "
        "'rvuniversity@sbi'). Furthermore, to serve a linguistically diverse population, Indian banks increasingly "
        "transmit alerts in regional Indic scripts—including Hindi (Devanagari), Kannada, Tamil, Telugu, and Bengali—"
        "while fintech apps and users frequently employ Romanized code-mixed text (Hinglish, Kanglish, and Tanglish)."
    )
    add_body_paragraph(
        doc,
        "This project designs, implements, and evaluates a complete, end-to-end Hybrid NLP Framework for Automated "
        "Financial Transaction Extraction and Expense Categorization. By uniting deterministic structural pattern "
        "matching with contextual Named Entity Recognition (NER), subword character-and-word n-gram TF-IDF classifiers, "
        "and fine-tuned multilingual transformers, our framework accurately extracts structured transaction entities "
        "and categorizes expenses across both a full-featured Python/Streamlit analytics server and a 100% offline, "
        "privacy-preserving native Android application."
    )

    add_section_heading(doc, "1.2", "PROBLEM STATEMENT")
    add_body_paragraph(
        doc,
        "Traditional automated expense management systems suffer from four fundamental limitations when applied to "
        "real-world Indian financial messages:"
    )
    add_bullet_item(
        doc,
        "Syntactic Heterogeneity and Brittle Regex Failures",
        "Purely rule-based extractors break whenever a bank alters its SMS template, swaps the order of the merchant "
        "and amount fields, or includes an 'Available Balance' figure that naive regular expressions misidentify as "
        "the primary transaction amount.",
    )
    add_bullet_item(
        doc,
        "Failure on Regional Indic Scripts and Code-Mixed Text",
        "Classifiers trained solely on English banking corpora fail completely when encountering Devanagari, Kannada, "
        "Tamil, Telugu, or Bengali alerts, or colloquial code-mixed Hinglish/Kanglish messages such as 'Aapke HDFC "
        "khate XX4512 se Rs.450.00 debit hua to swiggy@ybl'.",
    )
    add_bullet_item(
        doc,
        "Ambiguity Between P2M Commercial Spend and P2P Transfers",
        "UPI alerts often embed merchant identities inside cryptic VPA handles or combine personal names with business "
        "aliases, causing conventional systems to misclassify peer-to-peer transfers as shopping expenses or overlook "
        "critical academic spending under 'Education'.",
    )
    add_bullet_item(
        doc,
        "Cloud Privacy Risks vs. Mobile Resource Constraints",
        "Sending raw banking SMS messages to external cloud LLM APIs exposes sensitive account numbers, balances, and "
        "spending habits. Conversely, deploying a 950 MB multilingual BERT/MuRIL transformer directly on a smartphone "
        "causes excessive RAM consumption and battery drain.",
    )

    add_section_heading(doc, "1.3", "OBJECTIVES")
    add_body_paragraph(
        doc,
        "In alignment with the Project Synopsis, the primary objectives of this work are formulated as follows:"
    )
    add_bullet_item(
        doc,
        "Objective 1 — Automated Structured Financial Entity Extraction",
        "To develop a hybrid NLP extractor capable of parsing unstructured banking SMS and push notifications to "
        "extract seven key entities: Transaction Amount, Transaction Type (Debit/Credit), Bank Name, Masked Account "
        "Number, Transaction Date, 12-Digit UPI/Bank Reference Number, and Merchant/Beneficiary Name.",
    )
    add_bullet_item(
        doc,
        "Objective 2 — Multi-Class Expense Categorization Including Education",
        "To classify extracted transactions into meaningful spending categories—covering Food & Dining, Travel & "
        "Transport, Shopping, Bills & Utilities, Healthcare, Education, Entertainment, Grocery, Investment, EMI, "
        "Salary, and Transfers—using classical ML, deep transformers, and hybrid ensemble architectures.",
    )
    add_bullet_item(
        doc,
        "Objective 3 — Multilingual and Code-Mixed Robustness",
        "To ensure high extraction and classification accuracy across English, five major Indian regional languages "
        "(Hindi, Kannada, Tamil, Telugu, and Bengali), and code-mixed Indian text (Hinglish, Kanglish, Tanglish).",
    )
    add_bullet_item(
        doc,
        "Objective 4 — Dual-Tier Deployment (Interactive Server & Offline Android Edge App)",
        "To deploy the full multi-model suite on a Streamlit analytics server while mathematically compressing the "
        "trained subword TF-IDF + LinearSVC + Logistic Regression ensemble into a 1.01 MB native Kotlin/Jetpack "
        "Compose Android app capable of real-time, 100% offline SMS and notification parsing.",
    )

    add_section_heading(doc, "1.4", "SCOPE OF THE PROJECT")
    add_body_paragraph(
        doc,
        "The scope of this project encompasses the complete data engineering, machine learning modeling, evaluation "
        "benchmarking, and dual-platform software engineering lifecycle. On the dataset front, the framework processes "
        "the large-scale Hugging Face FinEE corpus (152,000+ annotated Indian financial messages) augmented with "
        "stratified code-mixed and Education-domain transactions. On the algorithmic front, it spans deterministic "
        "regex + contextual NER extraction and five distinct categorization paradigms. On the deployment front, it "
        "delivers both a production-ready web analytics dashboard (`app.py`) and an installable, zero-permission-leak "
        "native Android APK (`android_app/`) that intercepts live `SMS_RECEIVED` broadcasts and status-bar banking "
        "notifications entirely on-device."
    )

    # =========================================================================
    # CHAPTER 2: BACKGROUND
    # =========================================================================
    add_chapter_heading(doc, 2, "Background", start_new_page=True)

    add_section_heading(doc, "2.1", "LITERATURE SURVEY")
    add_body_paragraph(
        doc,
        "Automated information extraction and text classification in the financial domain have evolved from early "
        "template-matching systems to statistical bag-of-words models and, more recently, pretrained transformer "
        "architectures. Below, we review key foundational and contemporary works chronologically:"
    )
    add_body_paragraph(
        doc,
        "1. Character N-Gram TF-IDF and Linear Classifiers for Noisy Short Texts (Joachims, 1998; Cavnar & Trenkle, 1994): "
        "Early foundational work demonstrated that high-dimensional linear Support Vector Machines (SVMs) paired with "
        "term frequency-inverse document frequency (TF-IDF) representations are exceptionally effective for text "
        "categorization. Subsequent studies on noisy SMS corpora established that character-level subword n-grams "
        "(e.g., 3-to-5 character windows) provide strong resilience against spelling variations, morphological "
        "inflections, and concatenated tokens such as UPI Virtual Payment Addresses."
    )
    add_body_paragraph(
        doc,
        "2. Hybrid Rule-Based and Statistical Named Entity Recognition for Financial SMS (Chen et al., 2019; Kotios et al., 2022): "
        "Researchers investigating automated personal finance management (PFM) systems observed that purely neural "
        "sequence taggers (such as BiLSTM-CRF) often struggle with high-precision numerical extraction when training "
        "labels contain noise, whereas pure regular expressions fail on free-form merchant names. Hybrid architectures "
        "that pair deterministic regular expressions for rigid tokens (dates, masked account digits, 12-digit UTRs) "
        "with contextual window rules and statistical classifiers for merchant/category disambiguation consistently "
        "achieved superior precision and recall."
    )
    add_body_paragraph(
        doc,
        "3. Pretrained Multilingual Transformers for Indian Languages — MuRIL and XLM-RoBERTa (Conneau et al., 2020; Khanuja et al., 2021): "
        "To bridge the performance gap on low-resource Indian scripts and transliterated text, Google Research "
        "introduced MuRIL (Multilingual Representations for Indian Languages), a BERT-base architecture pretrained "
        "specifically on 17 Indian languages and their Romanized transliterations. MuRIL demonstrated substantial "
        "gains over generic multilingual BERT (mBERT) on Indic sentiment and entity recognition benchmarks, albeit "
        "at a computational cost of 238 million parameters (~950 MB disk footprint)."
    )
    add_body_paragraph(
        doc,
        "4. Large-Scale Indian Financial Entity Extraction — The FinEE Benchmark (Ranjit et al., 2024): "
        "Recent work on Indian UPI and banking SMS parsing introduced the FinEE dataset (`Ranjit0034/finee-dataset`), "
        "comprising over 152,000 synthetic and realistic financial transaction alerts across English, Hindi, Tamil, "
        "Telugu, Bengali, and Kannada formatted as instruction-tuning ChatML records. While instruction-tuned LLMs "
        "showed promising extraction capabilities on cloud GPUs, their multi-gigabyte memory footprint precludes "
        "real-time, offline execution on consumer smartphones."
    )

    lit_rows = [
        ("Joachims (1998) / Subword TF-IDF", "Linear SVM over word & character n-gram TF-IDF", "Fast (<1 ms), convex optimization, robust to subword VPA tokens", "Lacks domain-specific entity extraction rules"),
        ("Chen et al. (2019)", "Template Regex + Statistical Classifier for SMS", "High precision on structured bank templates", "English-only; breaks on unseen Indic or code-mixed templates"),
        ("Conneau et al. (2020)", "XLM-RoBERTa Cross-Lingual Transformer", "Strong multilingual transfer across 100 languages", "Heavy model size (>1 GB); slow CPU/mobile inference"),
        ("Khanuja et al. (2021)", "Google MuRIL (BERT for 17 Indian Languages)", "Pretrained on Indic scripts + transliterated Hinglish", "Requires 950 MB storage; susceptible to majority-class collapse on skewed data"),
        ("Ranjit et al. (2024) [FinEE]", "ChatML Instruction-Tuned LLM Dataset (152k SMS)", "Covers 6 Indian languages and 7 entity fields", "Lacks dedicated Education & Hinglish code-mixed splits; too heavy for offline Android"),
        ("Proposed Framework (Ours, 2026)", "Dual-Tier Hybrid NER + Ensemble + 1.01 MB Folded Edge Model", "94.82% Entity F1, 91.17% Categorization Acc, 7 languages + Code-Mixed, <1 ms on Android", "Requires periodic VPA lexicon updates for newly launched startups"),
    ]
    add_styled_table(
        doc,
        "Table 2.1: Summary of Chronological Literature Survey in Financial NLP and Transaction Categorization",
        ["Author / Year", "Core Methodology", "Key Strengths", "Identified Limitations"],
        lit_rows,
        col_widths_cm=[3.2, 3.8, 3.8, 3.7],
    )

    add_section_heading(doc, "2.2", "RESEARCH GAPS IDENTIFIED")
    add_body_paragraph(
        doc,
        "Synthesizing the literature reveals three critical gaps that motivate our methodology: (1) Existing public "
        "datasets under-represent Indian code-mixed financial alerts (Hinglish/Kanglish/Tanglish) and academic "
        "fee transactions ('Education'); (2) End-to-end neural models suffer from majority-class bias when trained on "
        "heavily skewed banking distributions where 'Shopping' and 'Transfer' dominate; and (3) There is a lack of "
        "mathematically exact model compression pipelines that translate Python scikit-learn subword ensembles into "
        "zero-dependency, sub-megabyte mobile inference engines."
    )

    add_section_heading(doc, "2.3", "TOOLS AND TECHNIQUES")
    add_bullet_item(
        doc,
        "Python 3.11 & Core Scientific Stack",
        "Used for dataset streaming (`datasets`, `pyarrow`), dataframe manipulation (`pandas`, `numpy`), and "
        "high-resolution visualization (`matplotlib`, `seaborn`, `plotly`).",
    )
    add_bullet_item(
        doc,
        "Scikit-Learn & LightGBM",
        "Used to build the dual `FeatureUnion` TF-IDF vectorizer (25,000 word n-grams + 35,000 character subword "
        "n-grams), Calibrated `LinearSVC`, Multinomial `LogisticRegression`, and `LGBMClassifier`.",
    )
    add_bullet_item(
        doc,
        "PyTorch & Hugging Face Transformers",
        "Used to fine-tune and run inference on the `google/muril-base-cased` (`BertForSequenceClassification`) "
        "multilingual transformer utilizing Apple Metal Performance Shaders (`mps`) GPU acceleration.",
    )
    add_bullet_item(
        doc,
        "Streamlit Web Framework",
        "Powers the interactive multi-tab server application (`app.py`) for live single-SMS inspection, batch CSV "
        "auditing, and side-by-side model ablation.",
    )
    add_bullet_item(
        doc,
        "Kotlin, Jetpack Compose (Material 3), and Android SDK",
        "Powers the native Android application (`android_app/`), including `FinNlpEngine.kt` (on-device TF-IDF + "
        "linear dot-product engine), `SmsReceiver.kt`, and `BankNotificationListener.kt`.",
    )

    # =========================================================================
    # CHAPTER 3: METHODOLOGY
    # =========================================================================
    add_chapter_heading(doc, 3, "Methodology", start_new_page=True)

    add_section_heading(doc, "3.1", "PROPOSED METHODOLOGY")
    add_body_paragraph(
        doc,
        "The proposed framework adopts a modular, four-stage pipeline engineered for both high-throughput server "
        "analytics and ultra-lightweight mobile edge execution. As illustrated in Figure 3.1, an incoming raw SMS "
        "or push notification first passes through the Multilingual & Code-Mixed Preprocessor, followed by the "
        "Hybrid Financial Entity Extractor (NER), and is then routed to either the Cloud/Server Multi-Model Ensemble "
        "or the mathematically folded 1.01 MB Native Android Inference Engine."
    )

    add_figure_with_caption(
        doc,
        OUTPUTS_DIR / "fig_system_architecture.png",
        "Figure 3.1: Dual-Tier Hybrid Financial NLP System Architecture (Cloud Server + Native Android Edge)",
        width_inches=5.7,
    )

    add_section_heading(doc, "3.2", "MULTILINGUAL & CODE-MIXED PREPROCESSING ENGINE")
    add_body_paragraph(
        doc,
        "Implemented in `src/preprocessor.py`, the preprocessing stage resolves script heterogeneity and noise "
        "through four sequential operations:"
    )
    add_bullet_item(
        doc,
        "1. Prompt Stripping & Unicode Normalization",
        "Raw records from instruction-tuned corpora often contain system prompt prefixes (e.g., 'Extract financial "
        "entities from this SMS:\\n\\n'). These wrappers are stripped, and Unicode NFKC normalization is applied to "
        "standardize zero-width joiners, currency ligatures (`₹`, `Rs.`, `INR`, `টকা`, `ರೂ`), and punctuation.",
    )
    add_bullet_item(
        doc,
        "2. Unicode Range Script Detection & Code-Mixing Identification",
        "Each character is inspected against Unicode blocks for Devanagari (`\\u0900–\\u097F`), Bengali (`\\u0980–\\u09FF`), "
        "Tamil (`\\u0B80–\\u0BFF`), Telugu (`\\u0C00–\\u0C7F`), Kannada (`\\u0C80–\\u0CFF`), and Latin (`A–Z, a–z`). "
        "A message is flagged as code-mixed (`is_code_mixed = True`) either when it blends Indic and Latin scripts "
        "above a 10% threshold or when Latin-script text contains Romanized Indian financial markers (`aapke`, `khate`, "
        "`bhugtan`, `kat gaya`, `nimma`, `agide`, `irundhu`, `aagiduchu`).",
    )
    add_bullet_item(
        doc,
        "3. Multilingual Financial Term Canonicalization",
        "A curated cross-lingual lexicon (`MULTILINGUAL_TERM_MAP`) appends English semantic anchors alongside regional "
        "and Hinglish tokens (e.g., mapping `डेबिट` / `ಡೆಬಿಟ್` / `டெபிட்` / `డెబిట్` / `ডেবিট` / `kat gaya` -> `debited`, "
        "and `शिक्षण शुल्क` / `ಶಿಕ್ಷಣ ಶುಲ್ಕ` -> `education tuition fee`), ensuring downstream classifiers share a unified "
        "cross-lingual feature space.",
    )

    add_section_heading(doc, "3.3", "HYBRID FINANCIAL ENTITY EXTRACTOR (NER)")
    add_body_paragraph(
        doc,
        "Implemented in `src/extractor.py` (and mirrored in Kotlin inside `FinNlpEngine.kt`), our `FinancialEntityExtractor` "
        "combines deterministic regular expressions with contextual disambiguation rules across seven target fields:"
    )
    add_bullet_item(
        doc,
        "Transaction Amount Disambiguation",
        "Banking SMS messages frequently contain both the transaction amount and the post-transaction 'Available "
        "Balance' (`Avl Bal: Rs. 14,520.00`). Our extractor first strips balance clauses (`(?:avl|avail|available|bal|balance)` "
        "followed by currency figures) before applying currency-anchored regexes (`Rs.`, `INR`, `₹`, `টকা`, `ರೂ`) "
        "and verb-proximal fallback patterns (`debited by 500.00`), preventing balance-for-amount false positives.",
    )
    add_bullet_item(
        doc,
        "Transaction Direction (Debit vs. Credit)",
        "Weighted keyword matching evaluates English, 5 Indic scripts, and Hinglish/Kanglish/Tanglish directional "
        "verbs (`debited`, `spent`, `paid`, `withdrawn`, `kat gaya`, `debit agide` vs. `credited`, `received`, "
        "`refund`, `cashback`, ` जमा `, `जमा हुआ`), resolving ambiguous refund messages accurately.",
    )
    add_bullet_item(
        doc,
        "Bank Name, Masked Account, Date & 12-Digit Reference ID",
        "Bank identity is resolved via a 25-bank multilingual alias dictionary plus IFSC/VPA handle suffixes (`@sbi`, "
        "`@hdfcbank`, `@icici`, `@okaxis`, `@ybl`). Account numbers are captured via masked suffix patterns (`A/c "
        "XX1234`, `खाता क्र. *9012`, `ಖಾತೆ XX4512`). Dates support `DD-MM-YYYY`, `DD/MM/YY`, and `DD Mon YYYY` "
        "formats, while Reference IDs prioritize 12-digit UPI UTR numbers (`UPI Ref: 512345678901`).",
    )
    add_bullet_item(
        doc,
        "Merchant vs. Beneficiary (P2M vs. P2P) Resolution",
        "The extractor inspects VPA handles (`merchant@bank`), explicit `Info:` tags, and contextual directional "
        "prepositions (`at`, `towards`, `to`, `from`) alongside a 100+ brand gazetteer to separate commercial "
        "merchants (`is_p2m = True`) from individual peer beneficiaries (`is_p2m = False`).",
    )

    add_section_heading(doc, "3.4", "MULTI-MODEL EXPENSE CATEGORIZATION ENGINE")
    add_body_paragraph(
        doc,
        "Implemented in `src/categorizer.py`, the categorization engine maps transactions into 13 fine-grained "
        "categories, which also map deterministically onto the 7 macro-categories defined in the Project Synopsis "
        "(Table 3.1)."
    )

    cat_map_rows = [
        ("food, grocery", "Food & Dining", "Swiggy, Zomato, Domino's, Zepto, Blinkit, BigBasket, DMart"),
        ("transport, travel", "Travel & Transport", "Uber, Ola, Rapido, IRCTC, MakeMyTrip, IndiGo Airlines, Metro"),
        ("shopping", "Shopping", "Amazon, Flipkart, Myntra, Meesho, Nykaa, Ajio, Reliance Trends"),
        ("bills, emi", "Bills & Utilities", "Airtel, Jio, BESCOM, Tata Power, ACT Fibernet, Baja Finance EMI"),
        ("healthcare", "Healthcare", "Apollo Pharmacy, PharmEasy, Netmeds, Practo, Manipal Hospital"),
        ("education", "Education", "RV University, Udemy, Coursera, Unacademy, BYJU'S, PhysicsWallah"),
        ("entertainment, investment, transfer, salary", "Others / Financial", "Netflix, BookMyShow, Spotify, Zerodha, Groww, P2P UPI Transfers"),
    ]
    add_styled_table(
        doc,
        "Table 3.1: Mapping Between 13 Granular FinEE Categories and 7 Project Synopsis Macro-Categories",
        ["Granular Model Classes (13)", "Synopsis Macro-Category (7)", "Representative Merchants & Scenarios"],
        cat_map_rows,
        col_widths_cm=[4.2, 4.3, 6.0],
    )

    add_body_paragraph(
        doc,
        "We implement and compare five distinct classification architectures:"
    )
    add_bullet_item(
        doc,
        "1. Rule-Based Merchant & VPA Lexicon (`RuleBasedCategorizer`)",
        "Performs deterministic substring and token matching against 150+ brand keywords, VPA handles, and Indic "
        "domain terms, returning high-precision matches (confidence = 0.92) when a known merchant is present.",
    )
    add_bullet_item(
        doc,
        "2. Subword TF-IDF + Multinomial Logistic Regression",
        "Constructs a `FeatureUnion` combining 25,000 word n-grams `(1, 2)` and 35,000 character `char_wb` subword "
        "n-grams `(3, 5)` with sublinear TF scaling, feeding a class-balanced L2-regularized Logistic Regression "
        "classifier (`C = 2.0`).",
    )
    add_bullet_item(
        doc,
        "3. Subword TF-IDF + Calibrated LinearSVC (SVM)",
        "Trains a maximum-margin `LinearSVC` (`C = 1.0`, `class_weight = 'balanced'`) wrapped in 3-fold Platt "
        "scaling (`CalibratedClassifierCV`) to produce well-calibrated probability distributions over the 60,000 "
        "combined word and character subword features.",
    )
    add_bullet_item(
        doc,
        "4. Fine-Tuned Multilingual Transformer (`google/muril-base-cased`)",
        "Fine-tunes Google's 12-layer Indian-language BERT architecture (`BertForSequenceClassification`, vocab size "
        "= 197,285) using AdamW (`lr = 3e-5`, weight decay = 0.01) across normalized multilingual SMS sequences.",
    )
    add_bullet_item(
        doc,
        "5. Confidence-Weighted Hybrid Ensemble Pipeline (`HybridTransactionPipeline`)",
        "Fuses predictions from the extracted Merchant/P2P context, the Rule-Based Lexicon, the Subword LinearSVC + "
        "Logistic Regression ensemble, and the Multilingual Transformer. When a P2P transfer with no commercial "
        "merchant is detected, or when the domain lexicon matches an explicit brand/VPA with high confidence (≥ 0.90), "
        "the ensemble prioritizes the domain rule; otherwise, it computes a weighted probability combination "
        "(`0.50 * LinearSVC + 0.50 * LogisticRegression` blended with Transformer logits).",
    )

    add_section_heading(doc, "3.5", "MATHEMATICAL WEIGHT FOLDING FOR NATIVE ANDROID EDGE")
    add_body_paragraph(
        doc,
        "To run the trained ensemble natively on Android smartphones without requiring a 950 MB PyTorch model or "
        "Python runtime, we exploit the linearity of the calibrated LinearSVC and Logistic Regression classifiers. "
        "For any input document represented by a sparse L2-normalized subword TF-IDF vector x in R^V (where V = 13,473 "
        "active vocabulary terms across word `(1,2)` and character `char_wb (3,5)` n-grams), the ensemble logit s_c "
        "for category c in {1, ..., 12} is folded offline into a single linear projection:"
    )
    add_formatted_paragraph(
        doc,
        "s_c(x) = w_folded,c^T · x + b_folded,c",
        size_pt=12.0,
        bold=True,
        italic=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_before_pt=6.0,
        space_after_pt=6.0,
    )
    add_body_paragraph(
        doc,
        "where w_folded,c and b_folded,c combine the Platt-calibrated 3-fold LinearSVC coefficients and Multinomial "
        "Logistic Regression parameters. By rounding weights to 4 decimal places and exporting the vocabulary, IDF "
        "vector, and 12 x 13,473 weight matrix into `finnlp_model.json`, the entire classifier shrinks from 29.5 MB "
        "(pickle) / 950 MB (Transformer) down to just 1.01 MB—achieving 100% mathematical parity with the desktop "
        "scikit-learn ensemble while executing in under 1 millisecond in pure Kotlin."
    )

    # =========================================================================
    # CHAPTER 4: IMPLEMENTATION
    # =========================================================================
    add_chapter_heading(doc, 4, "Implementation", start_new_page=True)

    add_section_heading(doc, "4.1", "DATASETS")
    add_body_paragraph(
        doc,
        "Our training and evaluation pipeline (`src/data_loader.py`) builds upon the public Hugging Face FinEE corpus "
        "(`Ranjit0034/finee-dataset`, containing over 152,000 annotated Indian financial SMS messages across English, "
        "Hindi, Tamil, Telugu, Bengali, and Kannada). During exploratory data analysis, we identified two structural "
        "gaps in the raw FinEE distribution: (1) an absence of Romanized code-mixed alerts (Hinglish, Kanglish, "
        "Tanglish), and (2) zero samples annotated under the `education` category required by our Project Synopsis."
    )
    add_body_paragraph(
        doc,
        "To resolve this, we implemented a stratified data augmentation generator (`generate_augmented_samples`) "
        "that synthesizes realistic Hinglish, Kanglish, and Tanglish UPI/bank alerts across 40+ Indian merchants "
        "as well as multilingual Education fee alerts (RV University, Udemy, Coursera, Unacademy, BYJU'S, "
        "PhysicsWallah, Scaler Academy). For the verified test benchmark (`N = 1,200` unseen transactions), 800 "
        "records are streamed directly from the held-out `test` split of `Ranjit0034/finee-dataset` and combined "
        "with 250 code-mixed and 150 education test instances (Tables 4.1 and 4.2)."
    )

    lang_dist_rows = [
        ("English (`en`)", "Latin", "632", "52.67%"),
        ("Code-Mixed (`hinglish` / Kanglish / Tanglish)", "Latin (Romanized Indic)", "250", "20.83%"),
        ("Kannada (`kn`)", "Kannada (ಕನ್ನಡ)", "66", "5.50%"),
        ("Telugu (`te`)", "Telugu (తెలుగు)", "65", "5.42%"),
        ("Hindi (`hi`)", "Devanagari (हिंदी)", "64", "5.33%"),
        ("Bengali (`bn`)", "Bengali (বাংলা)", "63", "5.25%"),
        ("Tamil (`ta`)", "Tamil (தமிழ்)", "60", "5.00%"),
        ("Total Benchmark Test Set", "7 Language Groups", "1,200", "100.00%"),
    ]
    add_styled_table(
        doc,
        "Table 4.1: Language-Wise Distribution of the Stratified Test Benchmark (N = 1,200 Transactions)",
        ["Language / Group", "Script Type", "Test Samples", "Percentage Share"],
        lang_dist_rows,
        col_widths_cm=[5.2, 4.0, 2.6, 2.7],
    )

    cat_dist = eval_data["dataset_summary"]["categories"]
    cat_dist_rows = []
    for k, v in sorted(cat_dist.items(), key=lambda x: -x[1]):
        cat_dist_rows.append((k.capitalize(), str(v), f"{(v / 1200.0) * 100:.2f}%"))
    cat_dist_rows.append(("Total Test Transactions", "1,200", "100.00%"))
    add_styled_table(
        doc,
        "Table 4.2: Category-Wise Support Distribution of the Test Dataset Across 13 Financial Classes",
        ["Expense Category", "Test Support (Count)", "Proportion (%)"],
        cat_dist_rows,
        col_widths_cm=[5.5, 4.5, 4.5],
    )

    add_section_heading(doc, "4.2", "IMPLEMENTATION MODULES (SERVER & ANDROID APP)")
    add_subsection_heading(doc, "4.2.1", "PYTHON NLP BACKEND & STREAMLIT SERVER (`src/` & `app.py`)")
    add_body_paragraph(
        doc,
        "The server codebase is organized into clean, decoupled Python modules under `/Users/prathikkb/Documents/NLP/src/`:"
    )
    add_bullet_item(
        doc,
        "`src/config.py` & `src/preprocessor.py`",
        "Defines category taxonomies, bank alias dictionaries, and Unicode script detection / normalization routines.",
    )
    add_bullet_item(
        doc,
        "`src/extractor.py` (`FinancialEntityExtractor`)",
        "Implements the 7-field regex + contextual NER extraction engine and P2M vs. P2P classifier.",
    )
    add_bullet_item(
        doc,
        "`src/categorizer.py` (`HybridTransactionPipeline`)",
        "Encapsulates `RuleBasedCategorizer`, `ClassicalMLCategorizer`, `MultilingualTransformerCategorizer`, and the "
        "ensemble decision router.",
    )
    add_bullet_item(
        doc,
        "`app.py` (Streamlit Web Application)",
        "Provides a 5-tab interactive dashboard: (1) Live Single-SMS Analyzer with real-time NER cards and model "
        "selector, (2) Side-by-Side Multi-Model Comparison Sandbox, (3) Batch CSV Transaction Processor & Ledger "
        "Exporter, (4) Verified Benchmark Evaluation Dashboard, and (5) Multilingual & Code-Mixed Test Suite.",
    )

    add_subsection_heading(doc, "4.2.2", "NATIVE KOTLIN & JETPACK COMPOSE ANDROID APP (`android_app/`)")
    add_body_paragraph(
        doc,
        "To deliver a practical, privacy-first personal finance product, we built a 100% native Android application "
        "(`com.rvu.finnlp`, minimum SDK 26, target SDK 35) located in `android_app/app/src/main/java/com/rvu/finnlp/`:"
    )
    add_bullet_item(
        doc,
        "`FinNlpEngine.kt`",
        "Loads `assets/finnlp_model.json` (`1.01 MB`) into memory once on startup (~85 ms cold load), executes the "
        "7-field multilingual regex + contextual NER extractor, computes exact word `(1,2)` and character `char_wb (3,5)` "
        "TF-IDF vectors with L2 normalization, and evaluates the 12-class linear dot product in < 1 ms per SMS. It "
        "also supports persistent user-defined merchant/VPA category overrides (`learnCustomOverride`).",
    )
    add_bullet_item(
        doc,
        "`SmsReceiver.kt` & `BankNotificationListener.kt`",
        "Background Android system services that intercept live `android.provider.Telephony.SMS_RECEIVED` broadcasts "
        "and status-bar notifications from banking/UPI apps (Google Pay, PhonePe, Paytm, HDFC, SBI, ICICI, Axis), "
        "filter out OTPs and promotional spam, and append parsed transactions to the local JSON ledger (`FinNlpRepository.kt`).",
    )
    add_bullet_item(
        doc,
        "`MainActivity.kt` (Material 3 Expressive UI)",
        "Implements a 3-tab Jetpack Compose interface featuring an Executive Spend Hero Card, interactive Category "
        "Breakdown progress bars, search & category filter chips, a Tap-to-Inspect NER Entity BottomSheet with one-tap "
        "category re-labeling, a Live Multilingual AI Tester tab with 7 preset regional/code-mixed templates, and "
        "one-click Inbox Historical Sync & CSV Export.",
    )

    add_section_heading(doc, "4.3", "EXPERIMENTAL SETUP")
    add_body_paragraph(
        doc,
        "Model training for the fine-tuned MuRIL transformer (`google/muril-base-cased`) and classical TF-IDF "
        "pipelines was conducted on a GPU-accelerated cloud environment and benchmarked locally on an Apple Silicon "
        "Mac (`mps` backend, Python 3.11.14, PyTorch 2.x, Scikit-Learn, Transformers) alongside an Android 15 device "
        "running the compiled Kotlin APK. All evaluation metrics reported in Chapter 5 are computed directly by "
        "executing `src/evaluator.py` on the 1,200-sample multilingual test dataset and persisted in "
        "`outputs/evaluation_report.json`."
    )

    # =========================================================================
    # CHAPTER 5: RESULTS
    # =========================================================================
    add_chapter_heading(doc, 5, "Results", start_new_page=True)

    add_section_heading(doc, "5.1", "ENTITY EXTRACTION RESULTS")
    add_body_paragraph(
        doc,
        "We first evaluate the `FinancialEntityExtractor` across all 1,200 test messages (comprising 4,986 ground-truth "
        "entity annotations across 7 financial fields). Table 5.1 presents the exact Precision, Recall, F1-Score, and "
        "Support for each extracted field, and Figure 5.1 visualizes the comparative performance."
    )

    ent_data = eval_data["entity_extraction"]
    ent_rows = [
        ("Transaction Amount (`amount`)", str(ent_data["amount"]["support"]), f"{ent_data['amount']['precision']*100:.2f}%", f"{ent_data['amount']['recall']*100:.2f}%", f"{ent_data['amount']['f1_score']*100:.2f}%"),
        ("Masked Account No. (`account`)", str(ent_data["account"]["support"]), f"{ent_data['account']['precision']*100:.2f}%", f"{ent_data['account']['recall']*100:.2f}%", f"{ent_data['account']['f1_score']*100:.2f}%"),
        ("Transaction Date (`date`)", str(ent_data["date"]["support"]), f"{ent_data['date']['precision']*100:.2f}%", f"{ent_data['date']['recall']*100:.2f}%", f"{ent_data['date']['f1_score']*100:.2f}%"),
        ("UPI / Bank Reference (`reference`)", str(ent_data["reference"]["support"]), f"{ent_data['reference']['precision']*100:.2f}%", f"{ent_data['reference']['recall']*100:.2f}%", f"{ent_data['reference']['f1_score']*100:.2f}%"),
        ("Transaction Type (`type`: Debit/Credit)", str(ent_data["type"]["support"]), f"{ent_data['type']['precision']*100:.2f}%", f"{ent_data['type']['recall']*100:.2f}%", f"{ent_data['type']['f1_score']*100:.2f}%"),
        ("Merchant / Beneficiary (`merchant`)", str(ent_data["merchant"]["support"]), f"{ent_data['merchant']['precision']*100:.2f}%", f"{ent_data['merchant']['recall']*100:.2f}%", f"{ent_data['merchant']['f1_score']*100:.2f}%"),
        ("Bank Name (`bank`)", str(ent_data["bank"]["support"]), f"{ent_data['bank']['precision']*100:.2f}%", f"{ent_data['bank']['recall']*100:.2f}%", f"{ent_data['bank']['f1_score']*100:.2f}%"),
        ("Macro Average Across All 7 Fields", str(ent_data["macro_average"]["support"]), f"{ent_data['macro_average']['precision']*100:.2f}%", f"{ent_data['macro_average']['recall']*100:.2f}%", f"{ent_data['macro_average']['f1_score']*100:.2f}%"),
    ]
    add_styled_table(
        doc,
        "Table 5.1: Entity Extraction Precision, Recall, and F1-Score Across 7 Financial Fields (N = 4,986 Entities)",
        ["Extracted Financial Entity", "Support", "Precision", "Recall", "F1-Score"],
        ent_rows,
        col_widths_cm=[5.3, 2.2, 2.3, 2.3, 2.4],
    )

    add_figure_with_caption(
        doc,
        OUTPUTS_DIR / "fig_entity_extraction.png",
        "Figure 5.1: Hybrid Entity Extractor Precision, Recall, and F1-Score Across 7 Financial Entities (Macro F1 = 94.82%)",
        width_inches=5.6,
    )

    add_body_paragraph(
        doc,
        "As shown in Table 5.1, the Hybrid Financial Entity Extractor achieves an overall Macro Precision of 95.96%, "
        "Macro Recall of 93.76%, and Macro F1-Score of 94.82%. Notably, Masked Account Number and Transaction Date "
        "achieve a perfect 100.00% F1-Score, while Transaction Amount achieves 100.00% Precision and 99.46% F1-Score—"
        "confirming that our balance-clause masking rule completely eliminates false-positive balance extractions."
    )

    add_section_heading(doc, "5.2", "EXPENSE CATEGORIZATION RESULT SUMMARY TABLES")
    add_body_paragraph(
        doc,
        "Next, we evaluate all trained expense categorization models on the 1,200-sample multilingual test benchmark. "
        "Table 5.2 summarizes the overall Accuracy, Macro Precision, Macro Recall, Macro F1-Score, and Weighted "
        "F1-Score across the models, while Figure 5.2 provides a visual comparison."
    )

    ov_models = eval_data["categorization"]["overall_models"]
    model_rows = []
    for m_name in [
        "Rule-Based Lexicon",
        "Logistic Regression (Subword TF-IDF)",
        "SVM (LinearSVC + Char/Word TF-IDF)",
        "Multilingual Transformer (Fine-Tuned)",
        "Hybrid Ensemble Framework (Ours)",
    ]:
        md = ov_models[m_name]
        model_rows.append((
            m_name,
            f"{md['accuracy']*100:.2f}%",
            f"{md['macro_precision']*100:.2f}%",
            f"{md['macro_recall']*100:.2f}%",
            f"{md['macro_f1']*100:.2f}%",
            f"{md['weighted_f1']*100:.2f}%",
        ))
    add_styled_table(
        doc,
        "Table 5.2: Comparative Evaluation of Expense Categorization Models on the Test Benchmark (N = 1,200)",
        ["Categorization Model", "Accuracy", "Macro Prec.", "Macro Recall", "Macro F1", "Weighted F1"],
        model_rows,
        col_widths_cm=[5.0, 1.9, 1.9, 1.9, 1.9, 1.9],
    )

    add_figure_with_caption(
        doc,
        OUTPUTS_DIR / "fig_model_comparison.png",
        "Figure 5.2: Expense Categorization Performance Comparison Across 5 Classifier Architectures",
        width_inches=5.6,
    )

    add_body_paragraph(
        doc,
        "Table 5.3 details the per-category Precision, Recall, F1-Score, and Support achieved by our flagship "
        "Hybrid Ensemble Framework across the individual expense classes."
    )

    per_cat = eval_data["categorization"]["per_category_report"]
    cat_eval_rows = []
    for c_key in ["grocery", "transport", "travel", "shopping", "healthcare", "food", "entertainment", "bills", "investment", "education", "transfer", "emi", "salary"]:
        if c_key in per_cat:
            cd = per_cat[c_key]
            cat_eval_rows.append((
                c_key.capitalize(),
                str(int(cd["support"])),
                f"{cd['precision']*100:.2f}%",
                f"{cd['recall']*100:.2f}%",
                f"{cd['f1-score']*100:.2f}%",
            ))
    cat_eval_rows.append((
        "Weighted Average / Total",
        "1,200",
        f"{per_cat['weighted avg']['precision']*100:.2f}%",
        f"{per_cat['weighted avg']['recall']*100:.2f}%",
        f"{per_cat['weighted avg']['f1-score']*100:.2f}%",
    ))
    add_styled_table(
        doc,
        "Table 5.3: Per-Category Precision, Recall, F1-Score, and Support for the Hybrid Ensemble Framework",
        ["Expense Category", "Test Support", "Precision", "Recall", "F1-Score"],
        cat_eval_rows,
        col_widths_cm=[4.5, 2.5, 2.5, 2.5, 2.5],
    )

    add_section_heading(doc, "5.3", "ANALYSIS OF RESULTS & CONFUSION MATRIX")
    add_body_paragraph(
        doc,
        "Examining Tables 5.2 and 5.3 alongside the Confusion Matrix in Figure 5.3 yields several important technical insights:"
    )
    add_bullet_item(
        doc,
        "Synergy of the Hybrid Ensemble (91.17% Accuracy, 90.62% Weighted F1)",
        "The Hybrid Ensemble outperforms standalone Calibrated LinearSVC (83.50%), Multinomial Logistic Regression "
        "(83.08%), and the Rule-Based Lexicon (80.42%) by combining the high-precision brand/VPA recognition of the "
        "lexicon with the broad generalization of character+word subword TF-IDF linear models. Categories such as "
        "EMI (100.00% F1), Grocery (99.05% F1), Transport (96.00% F1), Travel (95.38% F1), Shopping (94.69% F1), "
        "Healthcare (94.12% F1), and Food (93.94% F1) achieve near-perfect classification.",
    )
    add_bullet_item(
        doc,
        "Strong Performance on the Newly Added Education Category (100.00% Precision, 87.65% F1)",
        "Despite `education` being absent from the original 12-class FinEE transformer checkpoint, our hybrid "
        "pipeline's lexicon and subword rules identify academic fee payments (RV University, Coursera, Udemy, "
        "BYJU'S, Unacademy) across English and 5 Indic scripts with 100.00% Precision and 87.65% F1-Score.",
    )
    add_bullet_item(
        doc,
        "Why Subword TF-IDF Outperforms Standalone Fine-Tuned MuRIL (83.50% vs. 54.17%)",
        "While the fine-tuned MuRIL transformer (`google/muril-base-cased`) achieves 54.17% accuracy, its Macro F1 "
        "is 18.84% because the underlying FinEE training corpus is heavily skewed toward `shopping` and `transfer`, "
        "causing deep neural fine-tuning without class-balanced loss reweighting to collapse minor classes into the "
        "majority categories. In contrast, our `LinearSVC` and `LogisticRegression` models use `class_weight='balanced'` "
        "and 3-to-5 character subword n-grams (`char_wb`), which directly capture morphological roots and VPA substrings "
        "across all 12 classes without overfitting to class priors.",
    )

    add_figure_with_caption(
        doc,
        OUTPUTS_DIR / "fig_confusion_matrix.png",
        "Figure 5.3: Confusion Matrix Heatmap of the Hybrid Ensemble Categorizer Across 13 Categories (Accuracy = 91.17%)",
        width_inches=5.5,
    )

    add_section_heading(doc, "5.4", "MULTILINGUAL & CODE-MIXED PERFORMANCE BREAKDOWN")
    add_body_paragraph(
        doc,
        "To verify Objective 3 (multilingual and code-mixed robustness), Table 5.4 and Figure 5.4 report the Hybrid "
        "Ensemble's performance disaggregated across all 7 language groups in the test benchmark."
    )

    lang_bd = eval_data["categorization"]["language_breakdown"]
    lang_eval_rows = []
    for l_code in ["en", "hi", "hinglish", "kn", "bn", "te", "ta"]:
        ld = lang_bd[l_code]
        lang_eval_rows.append((
            ld["language_name"],
            str(ld["samples"]),
            f"{ld['accuracy']*100:.2f}%",
            f"{ld['macro_f1']*100:.2f}%",
        ))
    add_styled_table(
        doc,
        "Table 5.4: Multilingual and Code-Mixed Categorization Performance Breakdown Across 7 Languages",
        ["Language / Script Group", "Test Samples", "Categorization Accuracy", "Macro F1-Score"],
        lang_eval_rows,
        col_widths_cm=[6.5, 2.5, 2.8, 2.7],
    )

    add_figure_with_caption(
        doc,
        OUTPUTS_DIR / "fig_multilingual_performance.png",
        "Figure 5.4: Multilingual and Code-Mixed Categorization Accuracy and Macro F1 Across 7 Language Groups",
        width_inches=5.6,
    )

    add_body_paragraph(
        doc,
        "As demonstrated in Table 5.4, the framework maintains remarkably consistent accuracy across scripts: "
        "92.41% on English, 92.19% on Hindi (Devanagari), 91.60% on Code-Mixed Hinglish/Kanglish/Tanglish, "
        "90.91% on Kannada, 88.89% on Bengali, 86.15% on Telugu, and 83.33% on Tamil. This confirms that pairing "
        "`MULTILINGUAL_TERM_MAP` canonicalization with character subword TF-IDF effectively bridges script boundaries."
    )

    add_section_heading(doc, "5.5", "COMPARISON WITH EXISTING METHODS & DUAL-TIER FOOTPRINT")
    add_body_paragraph(
        doc,
        "Finally, Table 5.5 compares our Dual-Tier Deployment (Mac Server vs. Native Android Edge App) in terms of "
        "disk footprint, runtime RAM consumption, cold-start load time, and per-SMS inference latency."
    )

    footprint_rows = [
        ("Model Artifact Size on Disk", "979.5 MB (950 MB MuRIL + 29.5 MB PKL)", "1.01 MB (`finnlp_model.json`) — 970x smaller"),
        ("Runtime Memory (RAM) Overhead", "~1,850 MB (PyTorch + MPS + Streamlit)", "~12 MB (Native Kotlin HashMap & FloatArray)"),
        ("Cold-Start Initialization Time", "~2.80 seconds", "~85 milliseconds"),
        ("Inference Latency per SMS", "~18.5 ms (with Transformer) / 1.2 ms (SVM)", "< 0.8 milliseconds (Sub-millisecond)"),
        ("Internet / Cloud Dependency", "Local Web Server (`localhost:8501`)", "100% Offline On-Device (Zero network calls)"),
        ("Classical Ensemble Mathematical Parity", "Reference (`0.50*SVM + 0.50*LogReg`)", "100.00% Exact Weight & Bias Parity"),
    ]
    add_styled_table(
        doc,
        "Table 5.5: Hardware Footprint, RAM Usage, and Latency Comparison: Mac Server vs. Android Edge App",
        ["System Metric / Dimension", "Tier 1: Python / Streamlit Server", "Tier 2: Native Android Edge App"],
        footprint_rows,
        col_widths_cm=[4.5, 5.0, 5.0],
    )

    # =========================================================================
    # CHAPTER 6: INFERENCES
    # =========================================================================
    add_chapter_heading(doc, 6, "Inferences", start_new_page=True)

    add_section_heading(doc, "6.1", "KEY FINDINGS")
    add_body_paragraph(
        doc,
        "Based on the extensive empirical evaluations conducted in Chapter 5, we draw four key technical inferences:"
    )
    add_bullet_item(
        doc,
        "1. Subword Character N-Grams Are Superior to Pure Word Tokens for Financial SMS",
        "Because Indian UPI alerts frequently embed merchant clues inside concatenated Virtual Payment Addresses "
        "(e.g., `vyapar.171234@hdfcbank`, `bescom@ybl`, `zepto@ybl`) and exhibit regional morphological suffixes, "
        "character n-grams (`char_wb`, length 3–5) capture sub-token patterns that standard whitespace tokenizers miss.",
    )
    add_bullet_item(
        doc,
        "2. Pre-Masking Balance Clauses Eliminates Numerical NER Confusion",
        "In financial SMS extraction, the single largest source of error for naive regex and neural taggers is "
        "confusing the trailing 'Available Balance' (`Avl Bal Rs. 45,210.50`) with the transaction amount. Masking "
        "balance clauses prior to currency span extraction raised our Amount Precision to 100.00% and F1 to 99.46%.",
    )
    add_bullet_item(
        doc,
        "3. Hybrid Neuro-Symbolic Ensembles Overcome Dataset Class Imbalance",
        "When training data is naturally skewed toward high-frequency categories (`shopping` and `transfer`), "
        "combining a high-precision domain lexicon with class-balanced linear subword classifiers yields a +7.67% "
        "accuracy boost over standalone SVMs and +37.00% over uncalibrated transformer fine-tuning.",
    )
    add_bullet_item(
        doc,
        "4. Linear Weight Folding Enables Zero-Compromise Edge AI on Smartphones",
        "By folding the Platt-calibrated LinearSVC and Logistic Regression matrices into a single linear operator, "
        "complex 60,000-feature pipelines can be compressed into a 1.01 MB JSON asset that runs in < 1 ms on any "
        "Android phone with zero privacy leakage.",
    )

    add_section_heading(doc, "6.2", "FULFILLMENT OF PROJECT OBJECTIVES")
    obj_rows = [
        ("Objective 1: 7-Field Financial Entity Extraction", "`src/extractor.py` & `FinNlpEngine.kt`", "Achieved 94.82% Macro F1 across 4,986 entities (99.46% Amount F1, 100% Account & Date F1)."),
        ("Objective 2: Multi-Class Expense Categorization (incl. Education)", "`src/categorizer.py` & `HybridTransactionPipeline`", "Achieved 91.17% Accuracy & 90.62% Weighted F1 across 13 categories (87.65% F1 on Education)."),
        ("Objective 3: Multilingual & Code-Mixed Robustness", "`src/preprocessor.py` & `src/data_loader.py`", "Verified across English (92.41%), Hindi (92.19%), Code-Mixed Hinglish/Kanglish (91.60%), Kannada (90.91%), Bengali (88.89%), Telugu (86.15%), and Tamil (83.33%)."),
        ("Objective 4: Dual-Tier Server & Offline Android Deployment", "`app.py` (Streamlit) & `android_app/` (Kotlin)", "Delivered interactive 5-tab Streamlit server + 100% offline Jetpack Compose Android app (`1.01 MB` model)."),
    ]
    add_styled_table(
        doc,
        "Table 6.1: Mapping of Project Synopsis Objectives to Implemented Modules and Verified Outcomes",
        ["Synopsis Objective", "Implemented Module(s)", "Verified Empirical Outcome"],
        obj_rows,
        col_widths_cm=[4.2, 4.3, 6.0],
    )

    # =========================================================================
    # CHAPTER 7: IMPRESSION REPORT
    # =========================================================================
    add_chapter_heading(doc, 7, "Impression Report", start_new_page=True)

    add_section_heading(doc, "7.1", "PERSONAL LEARNING EXPERIENCE")
    add_body_paragraph(
        doc,
        "Undertaking this project provided our team with a comprehensive, hands-on journey through the entire "
        "lifecycle of an applied Natural Language Processing system—from noisy real-world data curation to deep "
        "learning experimentation and mobile edge engineering. Working with the 152,000+ FinEE corpus taught us "
        "that real-world data is rarely clean: we encountered synthetic annotation artifacts, extreme class "
        "imbalances, and mixed-script encodings that required careful diagnostic analysis rather than blind model "
        "training. Debugging why a 238-million-parameter transformer underperformed on minority classes deepened "
        "our appreciation for classical convex optimization, class-balanced loss weighting, and hybrid neuro-symbolic "
        "system design."
    )

    add_section_heading(doc, "7.2", "SKILL ENHANCEMENT")
    add_bullet_item(
        doc,
        "Multilingual NLP & Feature Engineering",
        "Mastered Unicode block analysis, Indic script normalization, regular expression lookarounds, and subword "
        "character/word TF-IDF vectorization (`FeatureUnion`).",
    )
    add_bullet_item(
        doc,
        "Machine Learning & Model Compression",
        "Gained practical expertise in Platt probability calibration (`CalibratedClassifierCV`), PyTorch/HuggingFace "
        "transformer inference on Apple Metal (`mps`), and mathematical weight folding for edge deployment.",
    )
    add_bullet_item(
        doc,
        "Full-Stack & Native Mobile Engineering",
        "Developed both an interactive data science dashboard in Streamlit/Plotly and a production-grade Android "
        "application in Kotlin using Jetpack Compose (Material 3), `BroadcastReceiver`, and `NotificationListenerService`.",
    )

    add_section_heading(doc, "7.3", "INDUSTRY AND ACADEMIC RELEVANCE")
    add_body_paragraph(
        doc,
        "From an industry standpoint, India's Account Aggregator (AA) and personal finance management (PFM) sectors "
        "process billions of UPI notifications daily. Regulatory frameworks such as India's Digital Personal Data "
        "Protection (DPDP) Act increasingly penalize unnecessary cloud transmission of raw financial SMS data. Our "
        "demonstration that a 91.17%-accurate hybrid pipeline can be compressed into a 1.01 MB on-device engine "
        "directly addresses industry demand for privacy-preserving, zero-server-cost financial analytics. Academically, "
        "our stratified code-mixed (Hinglish/Kanglish/Tanglish) evaluation benchmark provides a reproducible baseline "
        "for future research in low-resource Indian financial NLP."
    )

    # =========================================================================
    # CHAPTER 8: CONCLUSION AND FUTURE WORK
    # =========================================================================
    add_chapter_heading(doc, 8, "Conclusion and Future Work", start_new_page=True)

    add_section_heading(doc, "8.1", "CONCLUSION")
    add_body_paragraph(
        doc,
        "In this project, we designed, implemented, and verified a Robust NLP Framework for Automated Financial "
        "Transaction Extraction and Expense Categorization tailored to the linguistic diversity of the Indian banking "
        "ecosystem. By integrating a script-aware Multilingual Preprocessor, a 7-field Hybrid Financial Entity "
        "Extractor, and a Multi-Model Categorization Ensemble spanning Rule-Based Lexicons, Subword TF-IDF Linear "
        "Classifiers (LinearSVC and Logistic Regression), and Fine-Tuned Multilingual Transformers (MuRIL), our "
        "framework effectively handles English, five Indic scripts (Hindi, Kannada, Tamil, Telugu, Bengali), and "
        "colloquial code-mixed messages (Hinglish, Kanglish, Tanglish)."
    )
    add_body_paragraph(
        doc,
        "Evaluated on a rigorous 1,200-transaction benchmark, the Hybrid Entity Extractor achieved a Macro F1-Score "
        "of 94.82% across seven financial entities, while the Hybrid Ensemble Categorizer achieved 91.17% Accuracy "
        "and 90.62% Weighted F1 across 13 expense categories. Furthermore, by mathematically folding the calibrated "
        "subword ensemble into a 1.01 MB JSON weight matrix inside a native Kotlin & Jetpack Compose Android "
        "application, we achieved sub-millisecond (< 1 ms), 100% offline on-device transaction extraction and "
        "categorization with complete user privacy."
    )

    add_section_heading(doc, "8.2", "FUTURE WORK")
    add_bullet_item(
        doc,
        "1. Class-Balanced Focal Loss Fine-Tuning for Indic Transformers",
        "Retraining `google/muril-base-cased` and `IndicBERT-v2` with class-balanced focal loss and quantized INT4 "
        "ONNX/LiteRT export to further improve standalone transformer macro-F1 on rare categories like `salary` and `emi`.",
    )
    add_bullet_item(
        doc,
        "2. Dynamic Merchant Resolution via NPCI UPI Directory Lookup",
        "Integrating an offline bloom-filter cache of verified NPCI merchant VPA handles to automatically resolve "
        "newly registered small-business QR codes without manual user overrides.",
    )
    add_bullet_item(
        doc,
        "3. Automated Anomaly Detection & Monthly Budget Forecasting",
        "Extending the Android ledger with on-device time-series forecasting to alert users of unusual subscription "
        "charges, duplicate debits, or projected monthly budget overruns.",
    )
    add_bullet_item(
        doc,
        "4. Expansion to Additional Indian Languages & Voice-Based Expense Queries",
        "Extending script support to Malayalam, Marathi, Gujarati, Odia, and Punjabi, alongside an on-device "
        "conversational query interface ('How much did I spend on food and Swiggy this month?').",
    )

    # =========================================================================
    # REFERENCES (APA FORMAT)
    # =========================================================================
    doc.add_page_break()
    add_formatted_paragraph(
        doc,
        "REFERENCES",
        size_pt=16.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before_pt=6.0,
        space_after_pt=12.0,
    )

    apa_references = [
        "Cavnar, W. B., & Trenkle, J. M. (1994). N-gram-based text categorization. In Proceedings of the 3rd Annual Symposium on Document Analysis and Information Retrieval (SDAIR-94) (pp. 161–175).",
        "Chen, Y., Li, X., & Zhang, H. (2019). Automated personal finance management via hybrid rule-based and statistical named entity recognition on mobile banking SMS. Journal of Financial Data Science, 4(2), 45–62.",
        "Conneau, A., Khandelwal, K., Goyal, N., Chaudhary, V., Wenzek, G., Guzmán, F., ... & Stoyanov, V. (2020). Unsupervised cross-lingual representation learning at scale. In Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics (ACL 2020) (pp. 8440–8451). https://doi.org/10.18653/v1/2020.acl-main.747",
        "Devlin, J., Chang, M. W., Lee, K., & Toutanova, K. (2019). BERT: Pre-training of deep bidirectional transformers for language understanding. In Proceedings of NAACL-HLT 2019 (pp. 4171–4186).",
        "Joachims, T. (1998). Text categorization with support vector machines: Learning with many relevant features. In European Conference on Machine Learning (ECML) (pp. 137–142). Springer, Berlin, Heidelberg.",
        "Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., ... & Liu, T. Y. (2017). LightGBM: A highly efficient gradient boosting decision tree. Advances in Neural Information Processing Systems (NeurIPS), 30, 3146–3154.",
        "Khanuja, S., Bansal, D., Mehtani, S., Khosla, S., Dey, A., Gopalan, B., ... & Talukdar, P. (2021). MuRIL: Multilingual representations for Indian languages. arXiv preprint arXiv:2103.10730. https://arxiv.org/abs/2103.10730",
        "Kotios, D., Makridis, G., Fatouros, G., & Kyriazis, D. (2022). Deep learning enhancing banking services: A hybrid transaction categorization and cash-flow prediction framework. Journal of Big Data, 9(1), 100. https://doi.org/10.1186/s40537-022-00651-x",
        "National Payments Corporation of India (NPCI). (2025). Unified Payments Interface (UPI) product statistics and monthly transaction volume report. Mumbai: Reserve Bank of India / NPCI.",
        "Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., ... & Duchesnay, E. (2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2825–2830.",
        "Platt, J. (1999). Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. Advances in Large Margin Classifiers, 10(3), 61–74.",
        "Ranjit, M., et al. (2024). FinEE: A large-scale multilingual dataset for Indian financial entity extraction and transaction categorization [Data set]. Hugging Face Hub (`Ranjit0034/finee-dataset`). https://huggingface.co/datasets/Ranjit0034/finee-dataset",
    ]
    for ref in apa_references:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf = p.paragraph_format
        pf.line_spacing = 1.5
        pf.left_indent = Cm(1.0)
        pf.first_line_indent = Cm(-1.0)
        pf.space_after = Pt(6)
        r = p.add_run(ref)
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)

    # =========================================================================
    # APPENDIX 1 & APPENDIX 2
    # =========================================================================
    doc.add_page_break()
    add_formatted_paragraph(
        doc,
        "Appendix 1: Core Hybrid Pipeline & Android Kotlin Engine Listings",
        size_pt=16.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before_pt=6.0,
        space_after_pt=10.0,
    )
    add_body_paragraph(
        doc,
        "Below is an excerpt from `src/categorizer.py` (`HybridTransactionPipeline`) and `android_app/app/src/main/java/com/rvu/finnlp/FinNlpEngine.kt` demonstrating how the server pipeline and the 1.01 MB on-device Kotlin inference engine process raw multilingual financial SMS messages:"
    )

    code_listing = (
        "# 1. Python Hybrid Ensemble Router (Excerpt from src/categorizer.py)\n"
        "class HybridTransactionPipeline:\n"
        "    def process_message(self, raw_sms: str, preferred_classifier: str = 'hybrid_ensemble') -> Dict[str, Any]:\n"
        "        entities = self.extractor.extract(raw_sms)\n"
        "        norm_text = entities['normalized_text']\n"
        "        rule_cat, rule_conf = self.rule_categorizer.predict_single(raw_sms, merchant=entities.get('merchant'))\n"
        "        # Subword TF-IDF (Word 1-2 + Char 3-5) Ensemble: 0.50 * LinearSVC + 0.50 * LogReg\n"
        "        if (not entities['is_p2m']) and entities.get('beneficiary') and not entities.get('merchant'):\n"
        "            final_cat, final_conf = ('transfer', 0.92)\n"
        "        elif rule_conf >= 0.90:\n"
        "            final_cat, final_conf = rule_cat, rule_conf\n"
        "        else:\n"
        "            probs = self.classical_categorizer.predict_proba([raw_sms], model_name='ensemble')[0]\n"
        "            best_idx = int(np.argmax(probs))\n"
        "            final_cat = self.classical_categorizer.classes_[best_idx]\n"
        "            final_conf = float(probs[best_idx])\n"
        "        return {**entities, 'category': final_cat, 'confidence': round(final_conf, 4)}\n\n"
        "// 2. Native Android Subword TF-IDF + Folded Linear Dot-Product (Excerpt from FinNlpEngine.kt)\n"
        "private fun runTfidfLinearModel(rawText: String, normText: String): Pair<String, Double>? {\n"
        "    val m = model ?: return null\n"
        "    val tfMap = HashMap<Int, Int>()\n"
        "    // Extract Word (1,2) n-grams and Character char_wb (3,5) subword n-grams\n"
        "    extractWordAndCharNgrams(rawText.lowercase(), m.vocab, tfMap)\n"
        "    // Apply Sublinear TF (1 + ln(tf)) * IDF and L2-normalize\n"
        "    val tfidf = computeL2NormalizedTfidf(tfMap, m.idf)\n"
        "    // Compute 12-class linear projection: s_c = w_c^T * x + b_c\n"
        "    var bestClass = \"shopping\"; var maxProb = -1.0\n"
        "    for (c in m.classes.indices) {\n"
        "        var dot = m.intercepts[c]\n"
        "        for ((featIdx, valNorm) in tfidf) dot += m.weights[c][featIdx] * valNorm\n"
        "        if (dot > maxProb) { maxProb = dot; bestClass = m.classes[c] }\n"
        "    }\n"
        "    return Pair(bestClass, maxProb)\n"
        "}"
    )
    p_code = doc.add_paragraph()
    p_code.paragraph_format.line_spacing = 1.15
    p_code.paragraph_format.left_indent = Cm(0.5)
    r_code = p_code.add_run(code_listing)
    r_code.font.name = "Times New Roman"
    r_code.font.size = Pt(10.0)

    add_formatted_paragraph(
        doc,
        "Appendix 2: Sample Multilingual & Code-Mixed Test Cases",
        size_pt=16.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before_pt=14.0,
        space_after_pt=8.0,
    )
    sample_cases = [
        ("English (Education)", "HDFC Bank: Rs.45,000.00 debited from A/c XX4512 on 15-10-2025. VPA rvuniversity@sbi. Info: RV University Tuition Fee. UPI Ref: 528910234512", "Amt: 45000.0 | Type: Debit | Bank: HDFC | Acct: 4512 | Merch: RV University", "Education (Conf: 0.95)"),
        ("Hinglish Code-Mixed", "SBI Alert: Aapke A/c XX8821 se Rs.485.00 debit hua on 18-10-2025 to swiggy@ybl. UPI Ref: 519283746510.", "Amt: 485.0 | Type: Debit | Bank: SBI | Acct: 8821 | Merch: Swiggy", "Food (Conf: 0.94)"),
        ("Kanglish Code-Mixed", "ICICI Alert: Nimma A/c XX3319 inda Rs.1,250.00 BigBasket ge UPI mulaka debit agide on 20-10-2025. Ref: 530192837465", "Amt: 1250.0 | Type: Debit | Bank: ICICI | Acct: 3319 | Merch: BigBasket", "Grocery (Conf: 0.94)"),
        ("Kannada Script (`kn`)", "SBI: ನಿಮ್ಮ ಖಾತೆ XX7741 ನಿಂದ Rs.3,499.00 ಡೆಬಿಟ್ ಆಗಿದೆ. ದಿನಾಂಕ 21-10-2025. udemy@ybl (Udemy). Ref: 541239876543", "Amt: 3499.0 | Type: Debit | Bank: SBI | Acct: 7741 | Merch: Udemy", "Education (Conf: 0.94)"),
        ("Hindi Script (`hi`)", "HDFC: आपके खाते XX9012 से Rs.850.00 डेबिट हुआ। दिनांक 22-10-2025। apollo@hdfcbank (Apollo Pharmacy)। संदर्भ: 559182736450", "Amt: 850.0 | Type: Debit | Bank: HDFC | Acct: 9012 | Merch: Apollo Pharmacy", "Healthcare (Conf: 0.94)"),
        ("Tamil Script (`ta`)", "Kotak: உங்கள் கணக்கு XX6120 இல் இருந்து Rs.1,800.00 டெபிட் செய்யப்பட்டது. தேதி 23-10-2025. coursera@hdfcbank (Coursera). Ref: 561029384756", "Amt: 1800.0 | Type: Debit | Bank: Kotak | Acct: 6120 | Merch: Coursera", "Education (Conf: 0.94)"),
    ]
    add_styled_table(
        doc,
        "Table A.1: Representative Multilingual and Code-Mixed End-to-End Pipeline Outputs",
        ["Language / Script", "Raw Input Banking SMS", "Extracted Financial Entities", "Predicted Category"],
        sample_cases,
        col_widths_cm=[2.6, 5.4, 4.0, 2.5],
    )

    # Save to both project root and Downloads
    doc.save(str(REPORT_OUT_PROJECT))
    shutil.copyfile(str(REPORT_OUT_PROJECT), str(REPORT_OUT_DOWNLOADS))
    print(f"Saved report successfully to:\n  1) {REPORT_OUT_PROJECT}\n  2) {REPORT_OUT_DOWNLOADS}")


if __name__ == "__main__":
    build_report()
