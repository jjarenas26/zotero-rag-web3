from ingestion.zotero_client import ZoteroClient
import json
import os

client = ZoteroClient()

tree = client.get_collection_tree()

#TARGET_ROOT = "blockchain"
TARGET_ROOT = "blockchain_paper"

for collection_key in tree:
    path = client.resolve_collection_path(collection_key, tree)

    if not path.startswith(TARGET_ROOT):
        continue

    semantics = client.parse_collection_semantics(path)

    items = client.get_items_by_collection(collection_key)

    for item in items:
        metadata = client.extract_metadata(item)

        metadata.update(semantics)

        os.makedirs("data/raw/metadata", exist_ok=True)
        with open(
            f"data/raw/metadata/{metadata['zotero_key']}.json", "w"
        ) as f:
            json.dump(metadata, f, indent=2)

        attachments = client.get_pdf_attachments(metadata["zotero_key"])

        for a in attachments:
            client.download_pdf(
                a["key"],
                output_dir="data/raw/pdfs",
                filename=metadata["zotero_key"]
            )
