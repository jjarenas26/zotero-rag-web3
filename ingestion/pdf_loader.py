from pypdf import PdfReader
import hashlib


import pdfplumber
import re

def extract_clean_text2(pdf_path: str) -> str:
    """
    Extrae el texto ignorando las franjas laterales de metadatos 
    y manejando las columnas de forma secuencial.
    """
    final_content = []
    seen_paragraphs = set()

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            width = float(page.width)
            height = float(page.height)

            # 1. Definimos las cajas para ignorar el ruido lateral 
            # MDPI suele tener los metadatos en el primer 20-25% de la izquierda en la pag 1
            # Pero el texto principal en el resto de las paginas es doble columna.
            
            # Margen de seguridad para saltar "Academic Editor", "Revised", etc.
            # Recortamos un 25% de la izquierda para la primera página o donde haya ruido
            
            left_col_bbox = (width * 0.05, height * 0.1, width * 0.49, height * 0.9)
            right_col_bbox = (width * 0.51, height * 0.1, width * 0.95, height * 0.9)

            # Extraemos por columnas
            left_text = page.within_bbox(left_col_bbox).extract_text()
            right_text = page.within_bbox(right_col_bbox).extract_text()
            
            combined_page = f"{left_text if left_text else ''}\n{right_text if right_text else ''}"

            # 2. Limpieza de líneas
            if combined_page.strip():
                lines = combined_page.split('\n')
                for line in lines:
                    # Filtro de seguridad para palabras pegadas o metadatos
                    if re.search(r"(AcademicEditor|Revised:|Accepted:|Published:)", line.replace(" ", "")):
                        continue
                    
                    clean_l = line.strip()
                    if len(clean_l) < 3: continue

                    # Deduplicación por hash para evitar el efecto "eco"
                    line_hash = hashlib.md5(clean_l.encode()).hexdigest()
                    if line_hash not in seen_paragraphs:
                        final_content.append(clean_l)
                        seen_paragraphs.add(line_hash)

    return "\n".join(final_content)

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