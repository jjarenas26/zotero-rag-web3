import json
import os

from ingestion.pdf_loader import extract_text
from ingestion.section_splitter import SectionSplitter
from ingestion.chunker import AcademicChunker


class IngestPipeline:

    def __init__(self):
        self.splitter = SectionSplitter()
        self.chunker = AcademicChunker()

    def ingest_paper(self, pdf_path: str, metadata_path: str) -> list:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        text = extract_text(pdf_path)
        sections = self.splitter.split(text)

        base_metadata = {
            "title": metadata.get("title"),
            "authors": metadata.get("authors"),
            "year": metadata.get("year"),
            "journal": metadata.get("journal"),
            "zotero_key": metadata.get("zotero_key"),
            "root_collection": metadata.get("root_collection"),
            "research_question": metadata.get("research_question"),
            "collection_path": metadata.get("collection_path"),
        }

        all_chunks = []

        for s in sections:
            if s["section"].lower() == "references":
                continue

            chunks = self.chunker.chunk_section(
                text=s["text"],
                base_metadata=base_metadata,
                section=s["section"]
            )

            all_chunks.extend(chunks)

        return all_chunks
