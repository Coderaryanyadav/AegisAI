import io
import difflib
from typing import Optional
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

class DocxExportService:
    """Enterprise-grade Word .docx generator for Indian Court Pleadings and Contract Redlining."""

    @staticmethod
    def create_court_pleading_docx(
        draft_text: str,
        title: str = "Legal Draft",
        court_header: str = "high_court"
    ) -> io.BytesIO:
        doc = Document()

        # Set standard Indian Court Pleading Margins:
        # Left margin 1.75 inches (for binding/stitching), Right 1.0 inch, Top 1.5 inch, Bottom 1.25 inch
        for section in doc.sections:
            section.top_margin = Inches(1.5)
            section.bottom_margin = Inches(1.25)
            section.left_margin = Inches(1.75)
            section.right_margin = Inches(1.0)
            section.page_width = Inches(8.5)
            section.page_height = Inches(14.0)  # Legal paper size standard for Indian courts

        # Base Normal Style
        style = doc.styles["Normal"]
        font = style.font
        font.name = "Times New Roman"
        font.size = Pt(13)
        font.color.rgb = RGBColor(20, 20, 20)

        # Header Title
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_title = p_title.add_run(title.upper())
        run_title.bold = True
        run_title.font.size = Pt(14)

        # Body Paragraphs
        lines = draft_text.splitlines()
        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue
            
            p = doc.add_paragraph()
            p.paragraph_format.line_spacing = 1.5
            p.paragraph_format.space_after = Pt(6)

            if trimmed.startswith("IN THE ") or trimmed.startswith("BEFORE THE ") or "JURISDICTION" in trimmed:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run(trimmed)
                run.bold = True
            elif trimmed.startswith("PETITIONER") or trimmed.startswith("RESPONDENT") or trimmed.startswith("VERSUS"):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run(trimmed)
                run.bold = True
            elif trimmed.startswith("PRAYER") or trimmed.startswith("VERIFICATION"):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run(trimmed)
                run.bold = True
                run.underline = True
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.first_line_indent = Inches(0.5)
                p.add_run(trimmed)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def create_redline_docx(
        original_text: str,
        modified_text: str,
        title: str = "Contract Redline Audit"
    ) -> io.BytesIO:
        """
        Generates a Word document with visible redline track changes:
        - Deletions in Red Strikethrough
        - Insertions in Green Underline
        - Retained text in Normal font
        """
        doc = Document()
        for section in doc.sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.0)
            section.right_margin = Inches(1.0)

        # Title
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_title = p_title.add_run(title)
        r_title.bold = True
        r_title.font.size = Pt(16)
        r_title.font.color.rgb = RGBColor(30, 41, 59)

        # Subtitle / Legend
        p_legend = doc.add_paragraph()
        p_legend.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_legend = p_legend.add_run("LEGEND: ")
        r_legend.bold = True
        r_legend.font.size = Pt(10)
        
        r_del = p_legend.add_run("[Redline Deletion] ")
        r_del.font.color.rgb = RGBColor(190, 18, 60)
        r_del.font.strike = True
        r_del.font.size = Pt(10)

        r_ins = p_legend.add_run(" [Proposed Addition] ")
        r_ins.font.color.rgb = RGBColor(16, 149, 90)
        r_ins.font.underline = True
        r_ins.font.size = Pt(10)

        doc.add_paragraph().paragraph_format.space_after = Pt(12)

        # Word-level diff
        orig_words = original_text.split()
        mod_words = modified_text.split()

        matcher = difflib.SequenceMatcher(None, orig_words, mod_words)
        p_body = doc.add_paragraph()
        p_body.paragraph_format.line_spacing = 1.3
        p_body.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                chunk = " ".join(orig_words[i1:i2]) + " "
                p_body.add_run(chunk)
            elif tag == "delete":
                chunk = " ".join(orig_words[i1:i2]) + " "
                run = p_body.add_run(chunk)
                run.font.strike = True
                run.font.color.rgb = RGBColor(190, 18, 60)
                run.bold = True
            elif tag == "insert":
                chunk = " ".join(mod_words[j1:j2]) + " "
                run = p_body.add_run(chunk)
                run.font.underline = True
                run.font.color.rgb = RGBColor(16, 149, 90)
                run.bold = True
            elif tag == "replace":
                del_chunk = " ".join(orig_words[i1:i2]) + " "
                r_del = p_body.add_run(del_chunk)
                r_del.font.strike = True
                r_del.font.color.rgb = RGBColor(190, 18, 60)
                
                ins_chunk = " ".join(mod_words[j1:j2]) + " "
                r_ins = p_body.add_run(ins_chunk)
                r_ins.font.underline = True
                r_ins.font.color.rgb = RGBColor(16, 149, 90)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
