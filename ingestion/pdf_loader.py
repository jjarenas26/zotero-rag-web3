from pypdf import PdfReader
from typing import Optional


def extract_text(pdf_path: str) -> str:
    """
    Extracts raw text from a scientific PDF.
    """
    reader = PdfReader(pdf_path)

    pages_text = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)

    return "\n".join(pages_text)


def extract_text_with_page_numbers(pdf_path: str):
    """
    Optional: returns [(page_number, text)]
    Useful for citations later.
    """
    reader = PdfReader(pdf_path)
    result = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            result.append({
                "page": i + 1,
                "text": text
            })

    return result
