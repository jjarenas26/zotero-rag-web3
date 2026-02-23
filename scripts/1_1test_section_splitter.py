from ingestion.section_splitter import SectionSplitter
from ingestion.pdf_loader import extract_clean_text2
from ingestion.academic_refine import AcademicRefiner

text = extract_clean_text2("data/raw/pdfs/WWQ4WEMC.pdf")
refine = AcademicRefiner()
raw_text = refine.refine_section("introduction",text)
print(raw_text[:20000])

# splitter = SectionSplitter()

# sections = splitter.split(text)

# for s in sections:
#     print("\n" + "="*40)
#     print(s["section"])
#     print("="*40)
#     print(s["text"][:500])


