import os
import requests
import yaml
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()


class ZoteroClient:
    BASE_URL = "https://api.zotero.org"

    def __init__(self, config_path: str = "config/zotero.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.api_key = (
            os.getenv("ZOTERO_API_KEY") or self.config["api_key"]
        )

        self.user_id = self.config["user_id"]
        self.library_type = self.config.get("library_type", "user")
        self.group_id = self.config.get("group_id")

        self.headers = {
            "Zotero-API-Key": self.api_key
        }

    # -----------------------------
    # Internal helpers
    # -----------------------------

    def _library_path(self) -> str:
        if self.library_type == "group":
            return f"/groups/{self.group_id}"
        return f"/users/{self.user_id}"

    def _get(self, endpoint: str, params: Dict = None):
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    # -----------------------------
    # Public API
    # -----------------------------

    def get_items_by_collection(
        self,
        collection_key: str,
        limit: int = 100
    ) -> List[Dict]:
        endpoint = (
            f"{self._library_path()}"
            f"/collections/{collection_key}/items"
        )

        params = {
            "limit": limit,
            "itemType": "-attachment"
        }

        return self._get(endpoint, params)

    def extract_metadata(self, item: Dict) -> Dict:
        data = item["data"]

        return {
            "zotero_key": item["key"],
            "title": data.get("title"),
            "authors": self._format_creators(data.get("creators", [])),
            "year": data.get("date", "")[:4],
            "journal": data.get("publicationTitle"),
            "doi": data.get("DOI"),
            "abstract": data.get("abstractNote"),
            "tags": [t["tag"] for t in data.get("tags", [])],
        }

    def _format_creators(self, creators: List[Dict]) -> str:
        names = []
        for c in creators:
            if "lastName" in c:
                names.append(c["lastName"])
        return ", ".join(names)

    def get_pdf_attachments(self, parent_key: str) -> List[Dict]:
        endpoint = f"{self._library_path()}/items/{parent_key}/children"
        items = self._get(endpoint)

        return [
            i for i in items
            if i["data"]["itemType"] == "attachment"
            and i["data"].get("contentType") == "application/pdf"
        ]

    # -----------------------------
    # FIXED: explicit filename
    # -----------------------------

    def download_pdf(
        self,
        item_key: str,
        output_dir: str,
        filename: str
    ) -> str:
        endpoint = f"{self._library_path()}/items/{item_key}/file"
        url = f"{self.BASE_URL}{endpoint}"

        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{filename}.pdf")

        r = requests.get(url, headers=self.headers, stream=True)
        r.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_path

    # -----------------------------
    # Collections helpers
    # -----------------------------

    def get_collection_tree(self) -> dict:
        endpoint = f"{self._library_path()}/collections"
        data = self._get(endpoint)

        tree = {}
        for c in data:
            tree[c["key"]] = {
                "name": c["data"]["name"].strip(),
                "parent": c["data"].get("parentCollection")
            }
        return tree

    def resolve_collection_path(self, collection_key: str, tree: dict) -> str:
        path = []
        current = collection_key

        while current:
            node = tree.get(current)
            if not node:
                break
            path.append(node["name"])
            current = node["parent"]

        return "/".join(p.lower() for p in reversed(path))

    def parse_collection_semantics(self, path: str) -> dict:
        parts = path.split("/")

        return {
            "root_collection": parts[0] if parts else None,
            "research_question": parts[-1] if len(parts) > 1 else parts[0],
            "collection_path": path
        }
