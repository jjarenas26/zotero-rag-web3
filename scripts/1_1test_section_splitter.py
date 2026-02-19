from ingestion.section_splitter import SectionSplitter
from ingestion.pdf_loader import extract_text

text = extract_text("data/raw/pdfs/2GBPQGCR.pdf")

splitter = SectionSplitter()
sections = splitter.split(text)

for s in sections:
    print("\n" + "="*40)
    print(s["section"])
    print("="*40)
    print(s["text"][:500])
