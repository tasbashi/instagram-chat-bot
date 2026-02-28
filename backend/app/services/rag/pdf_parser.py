"""PDF text + section extraction using PyMuPDF."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import fitz  # PyMuPDF

logger = logging.getLogger("rag.pdf_parser")


@dataclass
class PDFSection:
    title: str
    content: str
    page_number: int


@dataclass
class PDFResult:
    text: str
    page_count: int
    pages: list[str] = field(default_factory=list)
    sections: list[PDFSection] = field(default_factory=list)


def parse_pdf(file_path: str) -> PDFResult:
    """Extract text and detect sections from a PDF file.

    Sections are detected by font size changes — text rendered in a larger
    font than the body is treated as a heading.
    """
    doc = fitz.open(file_path)
    pages: list[str] = []
    all_text_parts: list[str] = []
    sections: list[PDFSection] = []

    current_section_title = "Introduction"
    current_section_content: list[str] = []
    current_section_page = 1

    for page_num, page in enumerate(doc, start=1):
        page_text = page.get_text("text")
        pages.append(page_text)
        all_text_parts.append(page_text)

        # Section detection via font-size analysis
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = ""
                max_font_size = 0.0
                for span in line["spans"]:
                    line_text += span["text"]
                    max_font_size = max(max_font_size, span["size"])

                line_text = line_text.strip()
                if not line_text:
                    continue

                # Heuristic: headings tend to be ≥ 14pt and short
                if max_font_size >= 14.0 and len(line_text) < 200:
                    # Save previous section
                    if current_section_content:
                        sections.append(PDFSection(
                            title=current_section_title,
                            content="\n".join(current_section_content),
                            page_number=current_section_page,
                        ))
                    current_section_title = line_text
                    current_section_content = []
                    current_section_page = page_num
                else:
                    current_section_content.append(line_text)

    # Final section
    if current_section_content:
        sections.append(PDFSection(
            title=current_section_title,
            content="\n".join(current_section_content),
            page_number=current_section_page,
        ))

    doc.close()

    full_text = "\n\n".join(all_text_parts)
    logger.info(
        "Parsed PDF: %d pages, %d sections, %d chars",
        len(pages), len(sections), len(full_text),
    )

    return PDFResult(
        text=full_text,
        page_count=len(pages),
        pages=pages,
        sections=sections,
    )
