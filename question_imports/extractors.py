from io import BytesIO
from pathlib import Path

import pymupdf
from docx import Document


class ExtractionError(ValueError):
    pass


def extract_text(upload):
    extension = Path(upload.name).suffix.lower()
    raw = upload.read()
    if len(raw) > 5 * 1024 * 1024:
        raise ExtractionError("File must be 5 MB or smaller.")
    try:
        if extension in {".txt", ".md"}:
            return raw.decode("utf-8-sig")
        if extension == ".docx":
            document = Document(BytesIO(raw))
            return chr(10).join(paragraph.text for paragraph in document.paragraphs)
        if extension == ".pdf":
            document = pymupdf.open(stream=raw, filetype="pdf")
            if document.needs_pass:
                raise ExtractionError("Encrypted PDF files are not supported.")
            text = chr(10).join(page.get_text() for page in document)
            if not text.strip():
                raise ExtractionError(
                    "No selectable text was found in the PDF; scanned PDFs require OCR."
                )
            return text
    except ExtractionError:
        raise
    except Exception as error:
        raise ExtractionError(f"Could not read {extension or 'the'} file.") from error
    raise ExtractionError("Unsupported file type. Use TXT, MD, DOCX, or PDF.")
