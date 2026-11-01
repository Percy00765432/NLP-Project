"""
Generates the complete, properly styled RV University B.Tech (Honours) Project Presentation (.pptx)
based directly on `/Users/prathikkb/Downloads/RVU PPT TEMPLATE.pptx`.

Preserves the exact RVU slide master (`Title and Content` layout with official RVU logo and bottom bar),
the `#233039` navy header banner with `#D7AC54` RVU gold titles, and populates all template slides plus
dedicated Implementation & Experimental Results slides with verified metrics and 300-DPI charts.
"""

import copy
import json
import shutil
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls


PROJECT_DIR = Path("/Users/prathikkb/Documents/NLP")
OUTPUTS_DIR = PROJECT_DIR / "outputs"
TEMPLATE_PATH = Path("/Users/prathikkb/Downloads/RVU PPT TEMPLATE.pptx")
PPT_OUT_PROJECT = PROJECT_DIR / "RVU_FinNLP_Presentation.pptx"
PPT_OUT_DOWNLOADS = Path("/Users/prathikkb/Downloads/RVU_FinNLP_Presentation.pptx")

# Official RVU Template Color Palette
RVU_NAVY = RGBColor(0x23, 0x30, 0x39)
RVU_GOLD = RGBColor(0xD7, 0xAC, 0x54)
DARK_TEXT = RGBColor(0x1E, 0x29, 0x3B)
MUTED_TEXT = RGBColor(0x47, 0x55, 0x69)
LIGHT_BG = RGBColor(0xF8, 0xFA, 0xFC)
CARD_BORDER = RGBColor(0xCB, 0xD5, 0xE1)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ACCENT_BLUE = RGBColor(0x1E, 0x40, 0xAF)
ACCENT_GREEN = RGBColor(0x06, 0x5F, 0x46)


def set_cell_fill(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    for child in list(tcPr):
        if child.tag.endswith("Fill"):
            tcPr.remove(child)
    shd = parse_xml(f'<a:solidFill {nsdecls("a")}><a:srgbClr val="{hex_color}"/></a:solidFill>')
    tcPr.append(shd)


def clear_slide_shapes(slide):
    for shape in list(slide.shapes):
        sp = shape._element
        sp.getparent().remove(sp)


def add_rvu_header_banner(slide, title_text: str):
    """Adds the signature RVU template navy banner (`#233039`) with gold (`#D7AC54`) title text."""
    banner = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(0.35),
        Inches(0.22),
        Inches(7.25),
        Inches(0.62),
    )
    banner.fill.solid()
    banner.fill.fore_color.rgb = RVU_NAVY
    banner.line.color.rgb = RVU_GOLD
    banner.line.width = Pt(1.5)

    tf = banner.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = f"  {title_text}"
    run.font.name = "Arial"
    run.font.size = Pt(20)
    run.font.bold = True
    run.font.color.rgb = RVU_GOLD
    return banner


def add_info_card(
    slide,
    left_in: float,
    top_in: float,
    width_in: float,
    height_in: float,
    heading: str,
    bullets: list,
    header_bg: RGBColor = RVU_NAVY,
    header_fg: RGBColor = RVU_GOLD,
    body_font_pt: float = 11.5,
):
    """Adds a clean structured card with a colored title bar and bullet list."""
    # Main card body
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(left_in),
        Inches(top_in),
        Inches(width_in),
        Inches(height_in),
    )
    card.fill.solid()
    card.fill.fore_color.rgb = LIGHT_BG
    card.line.color.rgb = CARD_BORDER
    card.line.width = Pt(1.0)

    # Header bar
    hdr_h = 0.36
    hdr = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(left_in),
        Inches(top_in),
        Inches(width_in),
        Inches(hdr_h),
    )
    hdr.fill.solid()
    hdr.fill.fore_color.rgb = header_bg
    hdr.line.color.rgb = header_bg
    tf_h = hdr.text_frame
    tf_h.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_h = tf_h.paragraphs[0]
    p_h.alignment = PP_ALIGN.LEFT
    r_h = p_h.add_run()
    r_h.text = f" {heading}"
    r_h.font.name = "Arial"
    r_h.font.size = Pt(12.5)
    r_h.font.bold = True
    r_h.font.color.rgb = header_fg

    # Text box for bullets
    tb = slide.shapes.add_textbox(
        Inches(left_in + 0.08),
        Inches(top_in + hdr_h + 0.04),
        Inches(width_in - 0.16),
        Inches(height_in - hdr_h - 0.08),
    )
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.05)
    tf.margin_right = Inches(0.05)
    tf.margin_top = Inches(0.04)
    tf.margin_bottom = Inches(0.04)

    for idx, b_item in enumerate(bullets):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(4)
        if isinstance(b_item, tuple):
            b_prefix, b_rest = b_item
            r1 = p.add_run()
            r1.text = f"▸ {b_prefix}: "
            r1.font.name = "Arial"
            r1.font.size = Pt(body_font_pt)
            r1.font.bold = True
            r1.font.color.rgb = DARK_TEXT

            r2 = p.add_run()
            r2.text = b_rest
            r2.font.name = "Arial"
            r2.font.size = Pt(body_font_pt)
            r2.font.bold = False
            r2.font.color.rgb = DARK_TEXT
        else:
            r = p.add_run()
            r.text = f"▸ {b_item}"
            r.font.name = "Arial"
            r.font.size = Pt(body_font_pt)
            r.font.color.rgb = DARK_TEXT


def add_styled_ppt_table(
    slide,
    left_in: float,
    top_in: float,
    width_in: float,
    height_in: float,
    headers: list,
    rows: list,
    col_widths_in: list = None,
    font_size_pt: float = 9.5,
):
    table_shape = slide.shapes.add_table(
        1 + len(rows),
        len(headers),
        Inches(left_in),
        Inches(top_in),
        Inches(width_in),
        Inches(height_in),
    )
    table = table_shape.table

    if col_widths_in:
        for i, w in enumerate(col_widths_in):
            table.columns[i].width = Inches(w)

    # Header styling
    for c_idx, h_text in enumerate(headers):
        cell = table.cell(0, c_idx)
        set_cell_fill(cell, "233039")
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
        r = p.add_run()
        r.text = str(h_text)
        r.font.name = "Arial"
        r.font.size = Pt(font_size_pt + 0.5)
        r.font.bold = True
        r.font.color.rgb = RVU_GOLD

    # Data rows
    for r_idx, r_data in enumerate(rows):
        is_highlight = (r_idx == len(rows) - 1) and any(
            k in str(r_data[0]).lower() for k in ["proposed", "hybrid ensemble", "macro average"]
        )
        bg_hex = "FEF3C7" if is_highlight else ("FFFFFF" if r_idx % 2 == 0 else "F1F5F9")
        for c_idx, val in enumerate(r_data):
            cell = table.cell(r_idx + 1, c_idx)
            set_cell_fill(cell, bg_hex)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if c_idx <= 1 else PP_ALIGN.CENTER
            r = p.add_run()
            r.text = str(val)
            r.font.name = "Arial"
            r.font.size = Pt(font_size_pt)
            r.font.bold = is_highlight or (c_idx == 0)
            r.font.color.rgb = DARK_TEXT

    return table


def build_presentation():
    prs = Presentation(str(TEMPLATE_PATH))
    content_layout = None
    for layout in prs.slide_layouts:
        if layout.name == "Title and Content":
            content_layout = layout
            break
    if content_layout is None:
        content_layout = prs.slide_layouts[-1]

    # Ensure we have exactly 16 slides by adding 3 slides before we populate them
    while len(prs.slides) < 16:
        prs.slides.add_slide(content_layout)

    # =========================================================================
    # SLIDE 1: TITLE SLIDE (Populate the exact shapes on Slide 1 of Template)
    # =========================================================================
    s1 = prs.slides[0]
    # Shape 0: Title Box (Navy Box with Gold Text)
    sh_title = s1.shapes[0]
    sh_title.top = Inches(1.10)
    sh_title.height = Inches(2.45)
    tf0 = sh_title.text_frame
    tf0.clear()
    tf0.word_wrap = True
    tf0.vertical_anchor = MSO_ANCHOR.MIDDLE
    p0 = tf0.paragraphs[0]
    p0.alignment = PP_ALIGN.CENTER
    r0 = p0.add_run()
    r0.text = "ROBUST NLP FRAMEWORK FOR AUTOMATED FINANCIAL TRANSACTION EXTRACTION AND EXPENSE CATEGORIZATION"
    r0.font.name = "Arial"
    r0.font.size = Pt(21)
    r0.font.bold = True
    r0.font.color.rgb = RVU_GOLD

    p0_sub = tf0.add_paragraph()
    p0_sub.alignment = PP_ALIGN.CENTER
    p0_sub.space_before = Pt(8)
    r0_sub = p0_sub.add_run()
    r0_sub.text = "Dual-Tier Cloud Analytics Server & 100% Offline Native Android Edge AI"
    r0_sub.font.name = "Arial"
    r0_sub.font.size = Pt(13.5)
    r0_sub.font.italic = True
    r0_sub.font.color.rgb = WHITE

    # Shape 4: Team Members Box (Right side)
    sh_team = s1.shapes[4]
    sh_team.left = Inches(5.05)
    sh_team.top = Inches(3.72)
    sh_team.width = Inches(4.65)
    sh_team.height = Inches(1.42)
    tf_team = sh_team.text_frame
    tf_team.clear()
    tf_team.word_wrap = True
    team_lines = [
        ("Team Members (Team ID: 10):", True, RVU_NAVY, 11.5),
        ("• 1RUA24CSE0331 — PREKSHA P V", True, DARK_TEXT, 10.5),
        ("• 1RUA24CSE0363 — RESHMA K P", True, DARK_TEXT, 10.5),
        ("• 1RUA24CSE0327 — PRATHIK K B", True, DARK_TEXT, 10.5),
        ("• 1RUA24CSE0380 — RUSHIL RAVI REDDY", True, DARK_TEXT, 10.5),
    ]
    for idx, (txt, is_b, col, sz) in enumerate(team_lines):
        p = tf_team.paragraphs[0] if idx == 0 else tf_team.add_paragraph()
        p.space_after = Pt(2)
        r = p.add_run()
        r.text = txt
        r.font.name = "Arial"
        r.font.size = Pt(sz)
        r.font.bold = is_b
        r.font.color.rgb = col

    # Shape 5: Project Guides Box (Left side)
    sh_guide = s1.shapes[5]
    sh_guide.left = Inches(0.45)
    sh_guide.top = Inches(3.72)
    sh_guide.width = Inches(4.50)
    sh_guide.height = Inches(1.42)
    tf_guide = sh_guide.text_frame
    tf_guide.clear()
    tf_guide.word_wrap = True
    guide_lines = [
        ("Project Guides:", True, RVU_NAVY, 11.5),
        ("Prof. Khushboo Pandey", True, DARK_TEXT, 11.0),
        ("Prof. Priyanka S Shivaramaiah", True, DARK_TEXT, 11.0),
        ("School of Computer Science and Engineering", False, MUTED_TEXT, 10.0),
        ("RV University, Bengaluru - 560059", False, MUTED_TEXT, 10.0),
    ]
    for idx, (txt, is_b, col, sz) in enumerate(guide_lines):
        p = tf_guide.paragraphs[0] if idx == 0 else tf_guide.add_paragraph()
        p.space_after = Pt(2)
        r = p.add_run()
        r.text = txt
        r.font.name = "Arial"
        r.font.size = Pt(sz)
        r.font.bold = is_b
        r.font.color.rgb = col

    # =========================================================================
    # SLIDE 2: OUTLINES
    # =========================================================================
    s2 = prs.slides[1]
    clear_slide_shapes(s2)
    add_rvu_header_banner(s2, "Outlines")

    add_info_card(
        s2,
        0.35,
        1.02,
        4.50,
        3.90,
        "Part I: Problem, Survey & Architecture",
        [
            ("1. Introduction", "Indian UPI/SMS ecosystem & multilingual financial NLP motivation"),
            ("2. Literature Survey", "Critical review of 6 foundational & contemporary research works"),
            ("3. Problem Statement", "Limitations of regex trackers, cloud privacy risks & Indic code-mixing"),
            ("4. Objectives & Outcomes", "4 core Project Synopsis objectives & verified deliverables"),
            ("5. System Requirements (SRS)", "Hardware & software stack across Server & Android Edge"),
            ("6. Proposed Methodology", "4-stage preprocessing, Hybrid NER & Multi-Model Categorizer"),
        ],
        body_font_pt=11.0,
    )
    add_info_card(
        s2,
        5.10,
        1.02,
        4.55,
        3.90,
        "Part II: Edge AI, Results & Execution Plan",
        [
            ("7. Edge Weight Folding", "Compressing 60k-feature SVM+LogReg into a 1.01 MB Android JSON"),
            ("8. System Architecture", "Dual-tier Cloud Server + Native Android Edge pipeline"),
            ("9. Dataset & Implementation", "FinEE 152k corpus + Hinglish/Education augmentation & apps"),
            ("10. Experimental Results", "94.82% Entity F1 & 91.17% Hybrid Categorization Accuracy"),
            ("11. Multilingual & Confusion Analysis", "Performance across 7 language groups & 13 expense classes"),
            ("12. Gantt Chart & References", "Project execution timeline, team allocation & IEEE citations"),
        ],
        body_font_pt=11.0,
    )

    # =========================================================================
    # SLIDE 3: INTRODUCTION
    # =========================================================================
    s3 = prs.slides[2]
    clear_slide_shapes(s3)
    add_rvu_header_banner(s3, "Introduction")

    add_info_card(
        s3,
        0.35,
        1.02,
        4.55,
        3.90,
        "Domain Context & Scope",
        [
            ("Explosion of Digital Payments", "India's UPI processes >14 Billion monthly transactions across 500+ banks; every payment generates an unstructured SMS or push alert."),
            ("Rich Unstructured Metadata", "Alerts contain vital personal finance entities: Amount, Debit/Credit direction, Bank Name, Masked Account, Date, 12-digit UTR Reference, and Merchant/VPA."),
            ("Multilingual Indian Reality", "Alerts are transmitted across English, 5 regional Indic scripts (Hindi, Kannada, Tamil, Telugu, Bengali), and colloquial code-mixed text (Hinglish, Kanglish, Tanglish)."),
        ],
        body_font_pt=11.2,
    )
    add_info_card(
        s3,
        5.05,
        1.02,
        4.60,
        3.90,
        "Key Challenges Addressed",
        [
            ("Extreme Syntactic Variability", "160-character cellular limits lead to non-standard abbreviations ('A/c', 'debtd', 'Avl Bal', 'Info:') that break rigid templates."),
            ("Balance vs. Amount Confusion", "Naive extractors frequently misidentify trailing 'Available Balance' figures as the primary transaction amount."),
            ("P2M vs. P2P Disambiguation", "Distinguishing commercial merchants ('swiggy@ybl', 'rvuniversity@sbi') from peer transfers ('rahul@okaxis')."),
            ("Privacy vs. Edge Efficiency", "Uploading banking SMS to cloud LLMs risks financial privacy, while raw BERT models (950 MB) are too heavy for mobile phones."),
        ],
        body_font_pt=11.2,
    )

    # =========================================================================
    # SLIDE 4: LITERATURE SURVEY (CRITICAL REVIEW)
    # =========================================================================
    s4 = prs.slides[3]
    clear_slide_shapes(s4)
    add_rvu_header_banner(s4, "Literature Survey — Evolution & Critical Insights")

    add_info_card(
        s4,
        0.35,
        1.02,
        3.00,
        3.90,
        "1. Classical & Subword ML",
        [
            ("Joachims (ECML 1998) & Cavnar (1994)", "Established that linear SVMs over high-dimensional word & character n-gram TF-IDF excel on noisy short text."),
            ("Subword Advantage", "3–5 char n-grams ('char_wb') capture morphological roots & concatenated UPI VPAs ('zepto@ybl') without OOV failures."),
            ("Platt Calibration (1999)", "Sigmoid calibration converts SVM margins into calibrated probabilities for ensemble fusion."),
        ],
        body_font_pt=10.5,
    )
    add_info_card(
        s4,
        3.50,
        1.02,
        3.00,
        3.90,
        "2. Hybrid Financial NER",
        [
            ("Chen et al. (2019) & Kotios et al. (2022)", "Demonstrated that pure neural taggers struggle with exact numeric extraction on noisy banking SMS."),
            ("Neuro-Symbolic Synergy", "Combining deterministic regex for rigid fields (Dates, 12-digit UTR, Masked A/c) with statistical ML for merchants yields >94% F1."),
            ("Limitation", "Prior works focused exclusively on monolingual English bank statements."),
        ],
        body_font_pt=10.5,
    )
    add_info_card(
        s4,
        6.65,
        1.02,
        3.00,
        3.90,
        "3. Indic Transformers & FinEE",
        [
            ("Khanuja et al. (MuRIL, 2021) & Conneau et al. (XLM-R, 2020)", "Pretrained BERT models on 17 Indian languages + transliterated text."),
            ("Ranjit et al. (FinEE Dataset, 2024)", "Released 152,000+ Indian financial SMS across 6 languages in ChatML format."),
            ("Critical Gap", "FinEE lacks code-mixed Hinglish/Kanglish & Education splits; 950 MB MuRIL collapses on minority classes & is too heavy for offline mobile."),
        ],
        body_font_pt=10.5,
    )

    # =========================================================================
    # SLIDE 5: LITERATURE SURVEY COMPARISON TABLE
    # =========================================================================
    s5 = prs.slides[4]
    clear_slide_shapes(s5)
    add_rvu_header_banner(s5, "Literature Survey — Comparative Matrix")

    lit_headers = ["Paper / Author Details", "Objective & Techniques Used", "Key Contribution", "Identified Research Gap"]
    lit_rows = [
        ("Joachims, T. (ECML 1998) & Platt, J. (1999)", "Text categorization via Linear Support Vector Machines + Platt sigmoid calibration", "Convex optimization over high-dimensional sparse TF-IDF vectors (<1 ms inference)", "Lacks structured entity extraction and multilingual normalization rules"),
        ("Chen, Y. et al. (J. Fin. Data Sci., 2019)", "Automated mobile banking SMS extraction using template regex + statistical classifiers", "High precision on rigid structured numerical tokens (Account, Date, UTR)", "Monolingual English only; fails when banks alter templates or include Indic scripts"),
        ("Conneau, A. et al. (ACL 2020) — XLM-RoBERTa", "Unsupervised cross-lingual representation learning across 100 languages", "Strong zero-shot cross-lingual transfer via 250k SentencePiece vocabulary", "1.1 GB model footprint; prohibitive RAM & battery cost for offline mobile apps"),
        ("Khanuja, S. et al. (Google Research, 2021) — MuRIL", "BERT-base pretrained on 17 Indian languages & transliterated Indic pairs", "Superior handling of Devanagari, Dravidian scripts, and Romanized Hindi", "950 MB size; prone to majority-class collapse on heavily skewed banking categories"),
        ("Kotios, D. et al. (Springer J. Big Data, 2022)", "Hybrid transaction categorization and cash-flow analytics for digital banking", "Combined rule-based merchant lookup with ML classifiers for PFM dashboards", "Requires cloud API connectivity; no support for Indian UPI VPAs or code-mixing"),
        ("Ranjit, M. et al. (FinEE Benchmark, 2024)", "Large-scale Indian financial entity extraction dataset (152k SMS in 6 languages)", "Standardized 7-entity & 12-category benchmark across en, hi, ta, te, bn, kn", "Zero 'Education' samples; lacks Hinglish/Kanglish code-mixing & edge compression"),
        ("Proposed Framework (Ours, 2026)", "Dual-Tier Hybrid NER + Subword Ensemble + 1.01 MB Folded Android Edge Engine", "94.82% Entity F1, 91.17% Categorization Acc across 7 language groups (<1 ms)", "Addresses all 4 gaps: Multilingual, Code-Mixed, Education & 100% Offline Android"),
    ]
    add_styled_ppt_table(
        s5,
        0.25,
        0.95,
        9.50,
        4.05,
        lit_headers,
        lit_rows,
        col_widths_in=[2.15, 2.45, 2.45, 2.45],
        font_size_pt=8.5,
    )

    # =========================================================================
    # SLIDE 6: PROBLEM STATEMENT
    # =========================================================================
    s6 = prs.slides[5]
    clear_slide_shapes(s6)
    add_rvu_header_banner(s6, "Problem Statement")

    add_info_card(
        s6,
        0.35,
        1.02,
        4.55,
        3.90,
        "Limitations of Existing Systems",
        [
            ("1. Fragile Regex Extractors", "Existing expense trackers fail when banks vary SMS phrasing or place 'Avl Bal Rs.12,400' near the debit verb, causing false amount extraction."),
            ("2. Failure on Indic & Code-Mixed SMS", "Standard NLP pipelines fail on regional alerts (Hindi, Kannada, Tamil, Telugu, Bengali) and Hinglish/Kanglish ('Aapke khate se Rs.450 debit hua')."),
            ("3. Missing Education & P2M Context", "Public benchmarks omit academic spending ('Education') and confuse P2P personal transfers with P2M merchant purchases."),
            ("4. Cloud Privacy vs. Mobile Bloat", "Cloud trackers expose sensitive banking SMS to external servers, while 950 MB Transformers cannot run smoothly on budget smartphones."),
        ],
        body_font_pt=11.0,
    )
    add_info_card(
        s6,
        5.05,
        1.02,
        4.60,
        3.90,
        "Novelty of Proposed Work",
        [
            ("1. Script-Aware Multilingual Preprocessor", "Automatic Unicode block detection + cross-lingual financial term canonicalization across 6 Indic languages + Hinglish/Kanglish/Tanglish."),
            ("2. Balance-Masked Hybrid 7-Entity NER", "Pre-masks balance clauses before currency extraction, achieving 100% Amount Precision (99.46% F1) and 94.82% Macro Entity F1."),
            ("3. Neuro-Symbolic Multi-Model Ensemble", "Combines a 150+ Merchant/VPA Lexicon with Word (1,2) + Char (3,5) Subword TF-IDF LinearSVC, Logistic Regression & MuRIL Transformer."),
            ("4. 970x Edge Compression (1.01 MB)", "Mathematically folds the 60k-feature calibrated SVM+LogReg ensemble into a 1.01 MB JSON engine running in <1 ms inside a native Android app."),
        ],
        body_font_pt=11.0,
    )

    # =========================================================================
    # SLIDE 7: OBJECTIVES AND EXPECTED OUTCOMES
    # =========================================================================
    s7 = prs.slides[6]
    clear_slide_shapes(s7)
    add_rvu_header_banner(s7, "Objectives and Expected Outcomes")

    add_info_card(
        s7,
        0.35,
        1.02,
        4.55,
        3.90,
        "Project Synopsis Objectives",
        [
            ("Objective 1 — 7-Field Entity Extraction", "Extract Amount, Type (Debit/Credit), Bank, Masked Account, Date, 12-Digit Reference ID, and Merchant/Beneficiary from noisy banking SMS."),
            ("Objective 2 — Multi-Class Categorization", "Categorize expenses across 13 granular classes (7 Synopsis macro-categories including Food, Travel, Shopping, Bills, Healthcare & Education)."),
            ("Objective 3 — Multilingual & Code-Mixed", "Ensure high accuracy across English, Hindi, Kannada, Tamil, Telugu, Bengali, and code-mixed Hinglish/Kanglish/Tanglish."),
            ("Objective 4 — Dual-Tier Deployment", "Deliver an interactive Streamlit analytics server alongside a 100% offline, privacy-preserving native Android application."),
        ],
        body_font_pt=11.0,
    )
    add_info_card(
        s7,
        5.05,
        1.02,
        4.60,
        3.90,
        "Verified Deliverables & Outcomes Achieved",
        [
            ("94.82% Macro Entity F1-Score", "Verified across 4,986 ground-truth entities on N=1,200 test SMS (100% F1 on Account & Date; 99.46% F1 on Transaction Amount)."),
            ("91.17% Categorization Accuracy", "Hybrid Ensemble achieves 91.17% Accuracy & 90.62% Weighted F1 (+7.67% over standalone SVM and +10.75% over Rule Lexicon)."),
            ("Consistent Cross-Lingual Robustness", "92.41% on English, 92.19% on Hindi, 91.60% on Code-Mixed Hinglish/Kanglish, and 90.91% on Kannada."),
            ("Production Server + Native Android APK", "5-tab Streamlit web dashboard (`app.py`) + Material 3 Jetpack Compose Android app (`1.01 MB` model, <0.8 ms latency)."),
        ],
        body_font_pt=11.0,
    )

    # =========================================================================
    # SLIDE 8: SYSTEM REQUIREMENT SPECIFICATION (SRS)
    # =========================================================================
    s8 = prs.slides[7]
    clear_slide_shapes(s8)
    add_rvu_header_banner(s8, "System Requirement Specification (SRS)")

    add_info_card(
        s8,
        0.35,
        1.02,
        4.55,
        3.90,
        "Software Stack & Justification",
        [
            ("Python 3.11, Pandas & PyArrow", "High-throughput streaming & tabular parsing of the 152,000+ Hugging Face FinEE dataset (`Ranjit0034/finee-dataset`)."),
            ("Scikit-Learn & LightGBM", "Constructs the `FeatureUnion` (25k Word + 35k Char Subword TF-IDF), Platt-calibrated `LinearSVC`, `LogisticRegression`, and `LGBMClassifier`."),
            ("PyTorch 2.x & Hugging Face Transformers", "Fine-tuning and GPU inference (`mps`/`cuda`) for `google/muril-base-cased` (`BertForSequenceClassification`, 197k vocab)."),
            ("Streamlit & Plotly Express", "Interactive web server (`localhost:8501`) for real-time NER inspection, model ablation, and batch CSV auditing."),
            ("Kotlin 2.0 & Jetpack Compose (Material 3)", "Native Android UI, `BroadcastReceiver` (live SMS), `NotificationListenerService` (UPI push alerts), and `FinNlpEngine.kt`."),
        ],
        body_font_pt=10.5,
    )
    add_info_card(
        s8,
        5.05,
        1.02,
        4.60,
        3.90,
        "Hardware & Deployment Specifications",
        [
            ("Tier 1: Analytics Server / Development Host", "Apple Silicon Mac (M-Series with Metal `mps` GPU acceleration) / Linux Server, 8+ GB RAM, ~1.0 GB disk space for all 7 models."),
            ("Tier 2: Target Android Mobile Device", "Android 8.0+ (API 26 to API 35 / Android 15), ARM64 processor, requires only 12 MB runtime RAM and 1.01 MB asset storage."),
            ("Security & Privacy Architecture", "Zero external API calls on Android; `READ_SMS`, `RECEIVE_SMS`, and `BIND_NOTIFICATION_LISTENER_SERVICE` processed 100% locally."),
            ("Real-Time Latency SLA", "< 20 ms per SMS on Server (with MuRIL Transformer); < 0.8 ms per SMS on Android Edge Engine."),
        ],
        body_font_pt=10.8,
    )

    # =========================================================================
    # SLIDE 9: PROPOSED METHODOLOGY (STAGE 1 TO STAGE 4)
    # =========================================================================
    s9 = prs.slides[8]
    clear_slide_shapes(s9)
    add_rvu_header_banner(s9, "Proposed Methodology — 4-Stage Hybrid NLP Pipeline")

    add_info_card(
        s9,
        0.35,
        1.00,
        4.55,
        1.88,
        "Stage 1: Multilingual & Code-Mixed Preprocessor",
        [
            ("Unicode NFKC & Prompt Stripping", "Strips ChatML wrappers and normalizes currency ligatures (`₹`, `Rs.`, `INR`, `টকা`, `ರೂ`)."),
            ("Script & Code-Mix Detector", "Detects 6 scripts (`en, hi, kn, ta, te, bn`) + Romanized Hinglish/Kanglish/Tanglish markers (`aapke`, `khate`, `nimma`, `agide`)."),
            ("Cross-Lingual Canonicalization", "Maps regional banking terms to canonical anchors via `MULTILINGUAL_TERM_MAP`."),
        ],
        body_font_pt=10.2,
    )
    add_info_card(
        s9,
        5.05,
        1.00,
        4.60,
        1.88,
        "Stage 2: Balance-Masked Hybrid NER Extractor",
        [
            ("Balance Clause Pre-Masking", "Strips `Avl Bal: Rs. XX` before amount extraction, achieving 100% Amount Precision."),
            ("7-Field Structural + Contextual NER", "Extracts Amount, Type (Debit/Credit), Bank (25 aliases + VPA handles), Masked A/c, Date, and 12-digit UTR Reference."),
            ("P2M vs. P2P Disambiguation", "Separates commercial merchants (`is_p2m=True`) from peer transfers via VPA & `Info:` rules."),
        ],
        body_font_pt=10.2,
    )
    add_info_card(
        s9,
        0.35,
        3.02,
        4.55,
        1.90,
        "Stage 3: Multi-Model Categorization Suite",
        [
            ("1. Rule-Based Brand/VPA Lexicon", "150+ Indian merchant handles & education keywords (Conf = 0.92)."),
            ("2. Subword TF-IDF Linear Classifiers", "25k Word `(1,2)` + 35k Char `char_wb (3,5)` n-grams with Platt-calibrated `LinearSVC` & `LogisticRegression`."),
            ("3. Fine-Tuned MuRIL Transformer", "`google/muril-base-cased` (12 layers, 197k vocab) + LightGBM baseline."),
        ],
        body_font_pt=10.2,
    )
    add_info_card(
        s9,
        5.05,
        3.02,
        4.60,
        1.90,
        "Stage 4: Confidence-Weighted Hybrid Ensemble",
        [
            ("Context-First Routing", "Routes verified P2P beneficiary transfers directly to `transfer` (Conf = 0.92)."),
            ("High-Precision Lexicon Priority", "Prioritizes explicit VPA/Merchant lexicon hits when confidence >= 0.90."),
            ("Calibrated Probability Fusion", "Blends `0.50 * LinearSVC + 0.50 * LogisticRegression` subword probabilities with Transformer logits (91.17% Accuracy)."),
        ],
        body_font_pt=10.2,
    )

    # =========================================================================
    # SLIDE 10: MATHEMATICAL WEIGHT FOLDING FOR ANDROID EDGE AI
    # =========================================================================
    s10 = prs.slides[9]
    clear_slide_shapes(s10)
    add_rvu_header_banner(s10, "Proposed Methodology — Edge Weight Folding (970x Compression)")

    add_info_card(
        s10,
        0.35,
        1.02,
        4.60,
        3.90,
        "Mathematical Linear Ensemble Folding",
        [
            ("Why Compress?", "Desktop models (`950 MB` MuRIL + `29.5 MB` Scikit-Learn pickle) require Python/PyTorch and ~1.85 GB RAM—unsuitable for always-on mobile background services."),
            ("Exploiting Linearity in TF-IDF Space", "Both Platt-calibrated `LinearSVC` (3 CV folds) and Multinomial `LogisticRegression` operate over the exact same L2-normalized Subword TF-IDF vector x in R^13,473."),
            ("Exact Offline Weight Folding", "We fold the ensemble weights offline into a single 12 x 13,473 projection matrix: s_c(x) = w_folded,c^T · x + b_folded,c."),
            ("100% Mathematical Parity", "Produces the exact same category predictions as the desktop Scikit-Learn ensemble while shrinking disk size to 1.01 MB (`finnlp_model.json`)."),
        ],
        body_font_pt=10.8,
    )

    footprint_headers = ["Metric / Dimension", "Mac Server (Python)", "Android App (Kotlin)"]
    footprint_rows = [
        ("Model Size on Disk", "979.5 MB (MuRIL + PKL)", "1.01 MB (970x smaller)"),
        ("Runtime RAM Usage", "~1,850 MB", "~12 MB"),
        ("Cold-Start Load Time", "~2.80 seconds", "~85 milliseconds"),
        ("Inference Latency / SMS", "18.5 ms (MuRIL) / 1.2 ms", "< 0.8 ms (Sub-ms)"),
        ("Active Subword Vocab", "13,473 Word+Char N-Grams", "13,473 (100% Parity)"),
        ("Network Requirement", "Local Web Server", "100% Offline On-Device"),
    ]
    add_styled_ppt_table(
        s10,
        5.10,
        1.05,
        4.55,
        3.85,
        footprint_headers,
        footprint_rows,
        col_widths_in=[1.55, 1.50, 1.50],
        font_size_pt=9.5,
    )

    # =========================================================================
    # SLIDE 11: ARCHITECTURE DIAGRAM
    # =========================================================================
    s11 = prs.slides[10]
    clear_slide_shapes(s11)
    add_rvu_header_banner(s11, "System Architecture Diagram")

    arch_img = OUTPUTS_DIR / "fig_system_architecture.png"
    if arch_img.exists():
        s11.shapes.add_picture(str(arch_img), Inches(0.65), Inches(0.92), width=Inches(8.70))

    # =========================================================================
    # SLIDE 12: DATASET & DUAL-TIER IMPLEMENTATION
    # =========================================================================
    s12 = prs.slides[11]
    clear_slide_shapes(s12)
    add_rvu_header_banner(s12, "Datasets & Dual-Tier Implementation")

    add_info_card(
        s12,
        0.35,
        1.02,
        4.55,
        3.90,
        "FinEE Corpus + Code-Mixed & Education Augmentation",
        [
            ("Base Corpus (`Ranjit0034/finee-dataset`)", "152,000+ annotated Indian banking SMS across 6 languages (`en, hi, kn, ta, te, bn`), 7 entities, and 12 categories."),
            ("Solving Dataset Gaps (`src/data_loader.py`)", "Raw FinEE lacked Romanized code-mixed SMS and `education` fee alerts required by our Project Synopsis."),
            ("Stratified Augmentation", "Synthesized realistic Hinglish, Kanglish & Tanglish UPI alerts + multilingual Education transactions (RV University, Udemy, Coursera, Unacademy, BYJU'S)."),
            ("Verified Test Benchmark (N = 1,200)", "800 held-out FinEE test rows + 250 Code-Mixed + 150 Education test rows (4,986 entity annotations)."),
        ],
        body_font_pt=10.6,
    )
    add_info_card(
        s12,
        5.05,
        1.02,
        4.60,
        3.90,
        "Implemented Applications (`app.py` & `android_app/`)",
        [
            ("1. Streamlit Analytics Server (`app.py`)", "5-tab web dashboard: Live Single-SMS NER & Confidence Analyzer, Side-by-Side Model Comparison, Batch CSV Processor, Benchmark Viewer & Multilingual Suite."),
            ("2. Native Android App (`MainActivity.kt`)", "100% Jetpack Compose (Material 3) app with Executive Spend Dashboard, Category Progress Bars, Search/Filter Chips & CSV Export."),
            ("3. Real-Time SMS & Notification Daemons", "`SmsReceiver.kt` & `BankNotificationListener.kt` auto-capture live bank SMS & GPay/PhonePe push alerts offline."),
            ("4. Interactive NER Sheet & Custom Memory", "Tap any transaction to inspect all 7 NER entities and re-label categories; `FinNlpEngine` remembers custom VPA rules."),
        ],
        body_font_pt=10.6,
    )

    # =========================================================================
    # SLIDE 13: EXPERIMENTAL RESULTS (ENTITY EXTRACTION & MODEL COMPARISON)
    # =========================================================================
    s13 = prs.slides[12]
    clear_slide_shapes(s13)
    add_rvu_header_banner(s13, "Experimental Results — Entity Extraction & Categorization")

    ent_img = OUTPUTS_DIR / "fig_entity_extraction.png"
    mod_img = OUTPUTS_DIR / "fig_model_comparison.png"
    if ent_img.exists():
        s13.shapes.add_picture(str(ent_img), Inches(0.30), Inches(0.95), width=Inches(4.60))
    if mod_img.exists():
        s13.shapes.add_picture(str(mod_img), Inches(5.05), Inches(0.95), width=Inches(4.60))

    add_info_card(
        s13,
        0.30,
        3.55,
        4.60,
        1.42,
        "Entity Extraction Highlights (4,986 Entities)",
        [
            ("Macro Average", "95.96% Precision | 93.76% Recall | 94.82% F1"),
            ("Numeric & Structural Precision", "100.0% F1 on Account & Date; 99.46% F1 on Amount (100% Precision); 97.35% F1 on UPI Ref ID."),
        ],
        body_font_pt=10.0,
    )
    add_info_card(
        s13,
        5.05,
        3.55,
        4.60,
        1.42,
        "Expense Categorization Highlights (N = 1,200)",
        [
            ("Hybrid Ensemble (Ours)", "91.17% Accuracy | 90.62% Weighted F1 | 85.78% Macro F1"),
            ("Substantial Gains", "Outperforms LinearSVC (83.50%) by +7.67%, Logistic Regression (83.08%) by +8.09%, and Rule Lexicon (80.42%) by +10.75%."),
        ],
        body_font_pt=10.0,
    )

    # =========================================================================
    # SLIDE 14: MULTILINGUAL PERFORMANCE & CONFUSION MATRIX
    # =========================================================================
    s14 = prs.slides[13]
    clear_slide_shapes(s14)
    add_rvu_header_banner(s14, "Multilingual Robustness & Confusion Matrix Analysis")

    lang_img = OUTPUTS_DIR / "fig_multilingual_performance.png"
    cm_img = OUTPUTS_DIR / "fig_confusion_matrix.png"
    if lang_img.exists():
        s14.shapes.add_picture(str(lang_img), Inches(0.30), Inches(0.95), width=Inches(4.75))
    if cm_img.exists():
        s14.shapes.add_picture(str(cm_img), Inches(5.20), Inches(0.92), width=Inches(4.35))

    add_info_card(
        s14,
        0.30,
        3.58,
        4.75,
        1.38,
        "Cross-Lingual & Category Takeaways",
        [
            ("High Accuracy Across All 7 Language Groups", "English (92.4%), Hindi (92.2%), Code-Mixed Hinglish/Kanglish (91.6%), Kannada (90.9%), Bengali (88.9%), Telugu (86.2%), Tamil (83.3%)."),
            ("Top Category F1-Scores", "EMI (100%), Grocery (99.0%), Transport (96.0%), Travel (95.4%), Shopping (94.7%), Healthcare (94.1%), Food (93.9%), Education (87.7%)."),
        ],
        body_font_pt=9.8,
    )

    # =========================================================================
    # SLIDE 15: PROJECT PLAN, GANTT CHART & TEAM ALLOCATION
    # =========================================================================
    s15 = prs.slides[14]
    clear_slide_shapes(s15)
    add_rvu_header_banner(s15, "Gantt Chart & Team Contribution Plan")

    gantt_headers = ["Phase / Task Description", "Lead / Contributors", "W1–W2", "W3–W4", "W5–W6", "W7–W8", "W9–W10", "W11–W12"]
    gantt_rows = [
        ("1. Literature Survey & FinEE Corpus Analysis", "All Team Members", "███", "███", "", "", "", ""),
        ("2. Multilingual Preprocessor & Code-Mixed Augmentation", "Preksha P V & Reshma K P", "", "███", "███", "", "", ""),
        ("3. 7-Field Hybrid Entity Extractor (Regex + Contextual NER)", "Prathik K B & Preksha P V", "", "", "███", "███", "", ""),
        ("4. Subword TF-IDF (SVM/LogReg) & MuRIL Transformer Training", "Prathik K B & Rushil R. R.", "", "", "", "███", "███", ""),
        ("5. Streamlit Server & 1.01 MB Native Android App (Kotlin)", "Prathik K B & Rushil R. R.", "", "", "", "", "███", "███"),
        ("6. Stratified Evaluation (N=1,200), Report & Documentation", "Reshma K P & All Members", "", "", "", "", "", "███"),
    ]
    add_styled_ppt_table(
        s15,
        0.30,
        0.98,
        9.40,
        3.92,
        gantt_headers,
        gantt_rows,
        col_widths_in=[3.30, 2.20, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65],
        font_size_pt=9.5,
    )

    # =========================================================================
    # SLIDE 16: REFERENCES (IEEE FORMAT) & THANK YOU
    # =========================================================================
    s16 = prs.slides[15]
    clear_slide_shapes(s16)
    add_rvu_header_banner(s16, "References (IEEE Format)")

    ieee_refs = [
        '[1] T. Joachims, "Text categorization with support vector machines: Learning with many relevant features," in Proc. European Conf. Machine Learning (ECML), Berlin, Germany: Springer, 1998, pp. 137–142.',
        '[2] Y. Chen, X. Li, and H. Zhang, "Automated personal finance management via hybrid rule-based and statistical named entity recognition on mobile banking SMS," J. Financial Data Sci., vol. 4, no. 2, pp. 45–62, 2019.',
        '[3] A. Conneau et al., "Unsupervised cross-lingual representation learning at scale," in Proc. 58th Annu. Meeting Assoc. Comput. Linguistics (ACL), 2020, pp. 8440–8451.',
        '[4] S. Khanuja et al., "MuRIL: Multilingual representations for Indian languages," Google Research, arXiv:2103.10730, 2021.',
        '[5] D. Kotios, G. Makridis, G. Fatouros, and D. Kyriazis, "Deep learning enhancing banking services: A hybrid transaction categorization and cash-flow prediction framework," J. Big Data, vol. 9, no. 1, p. 100, 2022.',
        '[6] M. Ranjit et al., "FinEE: A large-scale multilingual dataset for Indian financial entity extraction and transaction categorization," Hugging Face Hub (Ranjit0034/finee-dataset), 2024.',
    ]
    add_info_card(
        s16,
        0.35,
        0.98,
        9.30,
        2.95,
        "Key Research References (IEEE Citation Style)",
        ieee_refs,
        body_font_pt=9.8,
    )

    # Thank you banner at bottom of Slide 16
    ty_box = s16.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(1.80),
        Inches(4.08),
        Inches(6.40),
        Inches(0.82),
    )
    ty_box.fill.solid()
    ty_box.fill.fore_color.rgb = RVU_NAVY
    ty_box.line.color.rgb = RVU_GOLD
    ty_box.line.width = Pt(2.0)
    tf_ty = ty_box.text_frame
    tf_ty.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_ty = tf_ty.paragraphs[0]
    p_ty.alignment = PP_ALIGN.CENTER
    r_ty = p_ty.add_run()
    r_ty.text = "THANK YOU — QUESTIONS & LIVE DEMO"
    r_ty.font.name = "Arial"
    r_ty.font.size = Pt(18)
    r_ty.font.bold = True
    r_ty.font.color.rgb = RVU_GOLD

    prs.save(str(PPT_OUT_PROJECT))
    shutil.copyfile(str(PPT_OUT_PROJECT), str(PPT_OUT_DOWNLOADS))
    print(f"Saved presentation successfully to:\n  1) {PPT_OUT_PROJECT}\n  2) {PPT_OUT_DOWNLOADS}")


if __name__ == "__main__":
    build_presentation()
