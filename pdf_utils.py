"""PDF text extraction and heading-aware chunking."""
import os
import re

from paths import load_env

load_env()


def _extract_pymupdf(file_path: str) -> str:
    import fitz

    parts = []
    with fitz.open(file_path) as doc:
        for page in doc:
            text = page.get_text("text")
            if text and text.strip():
                parts.append(text.strip())
    return "\n\n".join(parts)


def _extract_pypdf2(file_path: str) -> str:
    import PyPDF2

    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        parts = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted and extracted.strip():
                parts.append(extracted.strip())
    return "\n\n".join(parts)


def _extract_ocr(file_path: str) -> str:
    """OCR fallback for scanned PDFs. Requires pytesseract + Tesseract installed."""
    try:
        import pytesseract
    except ImportError as e:
        raise ImportError(
            "OCR requires pytesseract. Install with: pip install -r requirements-ocr.txt"
        ) from e

    import fitz
    from PIL import Image

    parts = []
    with fitz.open(file_path) as doc:
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img)
            if text and text.strip():
                parts.append(text.strip())
    return "\n\n".join(parts)


def _ocr_enabled() -> bool:
    return os.getenv("RAG_OCR_ENABLED", "false").lower() in ("1", "true", "yes")


def extract_pdf_text(file_path: str) -> tuple[str, str]:
    """
    Extract text from a PDF. Tries PyMuPDF, then PyPDF2, then optional OCR.
    Returns (text, method_label).
    """
    text = ""
    method = "none"

    try:
        text = _extract_pymupdf(file_path)
        if text.strip():
            method = "pymupdf"
    except Exception as e:
        print(f"PyMuPDF extraction failed: {e}")

    if not text.strip():
        try:
            text = _extract_pypdf2(file_path)
            if text.strip():
                method = "pypdf2"
        except Exception as e:
            print(f"PyPDF2 extraction failed: {e}")

    # Very little text often means scanned pages — try OCR if enabled
    if _ocr_enabled() and len(text.strip()) < 200:
        try:
            ocr_text = _extract_ocr(file_path)
            if len(ocr_text.strip()) > len(text.strip()):
                text = ocr_text
                method = "ocr"
        except ImportError:
            print("OCR skipped: install pytesseract (pip install -r requirements-ocr.txt)")
        except Exception as e:
            print(f"OCR extraction skipped/failed: {e}")

    return text, method


def _is_heading(line: str) -> bool:
    if not line or len(line) > 120:
        return False
    if re.match(r"^(\d+\.)+\s+\S", line):
        return True
    if re.match(r"^\d+\.\s+[A-Z]", line):
        return True
    if line.isupper() and 2 <= len(line.split()) <= 14:
        return True
    if line.endswith(":") and len(line.split()) <= 12:
        return True
    return False


def _split_sections(text: str) -> list[str]:
    """Split text into sections at heading-like lines."""
    lines = text.replace("\r\n", "\n").split("\n")
    sections: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        if _is_heading(stripped) and current:
            block = "\n".join(current).strip()
            if block:
                sections.append(block)
            current = [line]
        else:
            current.append(line)

    if current:
        block = "\n".join(current).strip()
        if block:
            sections.append(block)

    if not sections:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        return paragraphs if paragraphs else ([text.strip()] if text.strip() else [])

    return sections


def chunk_text(text: str) -> list[str]:
    """
    Split document text into chunks respecting section boundaries.
    """
    try:
        chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "2000"))
    except ValueError:
        chunk_size = 2000
    try:
        overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "250"))
    except ValueError:
        overlap = 250

    text = text.strip()
    if not text:
        return []

    sections = _split_sections(text)
    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    def flush():
        nonlocal current_parts, current_len
        if not current_parts:
            return
        chunk = "\n\n".join(current_parts).strip()
        if len(chunk) > 50:
            chunks.append(chunk)
        current_parts = []
        current_len = 0

    def carry_overlap():
        nonlocal current_parts, current_len
        if not current_parts or overlap <= 0:
            current_parts = []
            current_len = 0
            return
        joined = "\n\n".join(current_parts)
        if len(joined) <= overlap:
            return
        tail = joined[-overlap:].lstrip()
        if "\n\n" in tail:
            tail = tail.split("\n\n", 1)[-1]
        current_parts = [tail] if tail else []
        current_len = len(tail)

    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) > chunk_size:
            flush()
            for i in range(0, len(section), chunk_size - overlap):
                piece = section[i : i + chunk_size].strip()
                if len(piece) > 50:
                    chunks.append(piece)
            current_parts = []
            current_len = 0
            continue

        if current_len + len(section) + 2 > chunk_size and current_parts:
            flush()
            carry_overlap()

        current_parts.append(section)
        current_len += len(section) + 2

    flush()
    return chunks
