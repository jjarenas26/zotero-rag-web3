from pypdf import PdfReader
import hashlib


import pdfplumber
import re


def extract_clean_text(pdf_path: str) -> str:
    """
    Extrae texto manejando formatos de doble columna y eliminando capas duplicadas.
    """
    reader = PdfReader(pdf_path)
    final_content = []
    seen_paragraphs = set()

    for page in reader.pages:
        # Intentamos extraer texto preservando el diseño de columnas
        # 'layout' ayuda a que pypdf mantenga la separación visual
        page_text = page.extract_text(extraction_mode="layout") 
        
        if not page_text:
            continue

        # Limpieza de párrafos con el filtro de duplicidad que ya teníamos
        paragraphs = page_text.split('\n')
        
        for p in paragraphs:
            # Eliminamos espacios extra que el modo layout suele introducir
            clean_p = " ".join(p.split()).strip()
            
            if len(clean_p) < 5:
                continue
                
            # Huella digital para evitar el "eco" de capas ocultas
            p_hash = hashlib.md5(clean_p.replace(" ", "").encode('utf-8')).hexdigest()
            
            if p_hash not in seen_paragraphs:
                final_content.append(clean_p)
                seen_paragraphs.add(p_hash)

    return "\n".join(final_content)