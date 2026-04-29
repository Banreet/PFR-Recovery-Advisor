import json
from typing import List
from pathlib import Path


class KnowledgeBaseService:
    def __init__(self):
        self.documents = []
        self._load_documents()

    def _load_documents(self):
        kb_path = Path(__file__).parent.parent.parent / "knowledge_base"
        if not kb_path.exists():
            return
        for json_file in kb_path.rglob("*.json"):
            try:
                with open(json_file, "r") as f:
                    doc = json.load(f)
                    doc["_source_file"] = str(json_file.relative_to(kb_path))
                    self.documents.append(doc)
            except Exception:
                pass

    def search_relevant_docs(self, query: str) -> List[str]:
        query_lower = query.lower()
        keywords = query_lower.split()
        results = []
        for doc in self.documents:
            doc_text = json.dumps(doc).lower()
            score = sum(1 for kw in keywords if kw in doc_text)
            if score > 0:
                results.append((score, doc))
        results.sort(key=lambda x: x[0], reverse=True)
        excerpts = []
        for _, doc in results[:3]:
            source = doc.get("_source_file", "unknown")
            title = doc.get("title", doc.get("incident_id", source))
            excerpt = f"[Source: {source}] {title}\n"
            if "sections" in doc:
                for section in doc["sections"][:2]:
                    excerpt += f"  - {section.get('title', '')}: {str(section.get('content', ''))[:300]}\n"
            elif "resolution_steps" in doc:
                steps = doc["resolution_steps"][:3]
                excerpt += f"  Resolution: {json.dumps(steps)[:400]}\n"
            elif "services" in doc:
                services = list(doc["services"].keys())
                excerpt += f"  Services: {', '.join(services)}\n"
            excerpts.append(excerpt)
        return excerpts

    def get_service_dependencies(self) -> dict:
        for doc in self.documents:
            if "services" in doc and "_source_file" in doc:
                if "dependencies" in doc["_source_file"]:
                    return doc.get("services", {})
        return {}


knowledge_base_service = KnowledgeBaseService()
