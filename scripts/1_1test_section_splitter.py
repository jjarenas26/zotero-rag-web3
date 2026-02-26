from ingestion.section_splitter import SectionSplitter
from ingestion.pdf_loader import extract_clean_text
from ingestion.academic_refine import AcademicRefiner
from ingestion.academic_extractor import AcademicIntelligenceExtractor

text = extract_clean_text("data/raw/pdfs/WWQ4WEMC.pdf")
#print(len(text))
#print(text[:20000])
refine = AcademicRefiner()
intel_extractor = AcademicIntelligenceExtractor()
# raw_text = refine.refine_section(text)
# print(raw_text[:2000])

splitter = SectionSplitter()

sections = splitter.split(text)

for s in sections:
    print("\n" + "="*40)
    #raw_text = refine.refine_section(s["section"],s["text"])
    raw_text = s["text"]
    if s["section"] in ["Methodology", "results", "introduction"]:
        intel_json = intel_extractor.extract_intelligence(s["section"], raw_text)
        metadata = {
            "trl": intel_json.get("trl_analysis", {}).get("level"),
            "entities": str(intel_json.get("entities", [])),
            #"source": doc_id
        }
        print(metadata)
    print(s["section"])
    print("="*40)
    print(raw_text)


