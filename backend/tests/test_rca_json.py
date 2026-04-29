"""
test_rca_json.py
----------------
Validates the generated RCA JSON files against the Canonical Schema and checks
that required fields are populated correctly.
"""
import importlib.util
import json
from pathlib import Path
import pytest

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

KB_ROOT = Path(__file__).parent.parent / "knowledge_base"
RCAS_DIR = KB_ROOT / "rcas"
SCHEMA_PATH = KB_ROOT / "Canonical Schema"

# IDs of the three generated RCA JSON files (last 3 months, scoped outages)
GENERATED_IDS = [
    "rca-pfvm-powerdown-scoped-drill-2026-04",
    "rca-pfvm-fc-softdelete-drill-2026-05",  # "05" = May 2026 planned drill date; last_validated_date reflects document creation (April 2026)
    "rca-dm-dataloss-drill-2026-04",
]

REQUIRED_FIELDS = [
    "id", "title", "doc_type", "priority", "source",
    "service", "fault_type", "environment", "vector_tags",
    "confidence_level", "last_validated_date", "content",
]

VALID_DOC_TYPES = {
    "Recovery_TSG", "Platform_TSG", "Drill_Report", "Drill_Master_ICM",
    "RCA", "Dependency_Document", "KPI_Document", "Automation_Document",
    "Meeting_Transcript", "Work_Item", "Design_Context",
}
VALID_PRIORITIES = {"P0", "P1", "P2"}
VALID_SERVICES = {"DM", "SEC", "PFVM", "Titan", "ZK", "Platform", "Multi"}
VALID_FAULT_TYPES = {
    "data_loss", "power_down", "zone_down", "dependency_loss",
    "hardware_failure", "unknown",
}
VALID_ENVIRONMENTS = {"prod", "canary", "stage", "euap"}
VALID_CONFIDENCE = {"high", "medium", "low"}
VALID_SOURCE_TYPES = {"SharePoint", "IcM", "Email", "ADO", "Teams", "GitHub"}
VALID_PHASES = {"pre_drill", "fault_injection", "recovery", "validation", "post_incident"}
VALID_DEP_TYPES = {"hard", "soft", "implicit"}
VALID_GUARDRAIL_TYPES = {"authorization", "dependency", "data_loss_risk", "known_failure"}
VALID_AUTOMATION_SYSTEMS = {"RAP", "FIS", "FMS", "CustomScript", "None"}


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_rca(rca_id: str) -> dict:
    path = RCAS_DIR / f"{rca_id}.json"
    assert path.exists(), f"Expected JSON file not found: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("rca_id", GENERATED_IDS)
class TestRCAJsonStructure:
    """Structural tests that run against each generated RCA JSON file."""

    def test_file_exists(self, rca_id: str):
        path = RCAS_DIR / f"{rca_id}.json"
        assert path.exists(), f"Missing file: {path}"

    def test_valid_json(self, rca_id: str):
        path = RCAS_DIR / f"{rca_id}.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(doc, dict)

    def test_required_fields_present(self, rca_id: str):
        doc = _load_rca(rca_id)
        for field in REQUIRED_FIELDS:
            assert field in doc, f"Missing required field '{field}' in {rca_id}"

    def test_id_matches_filename(self, rca_id: str):
        doc = _load_rca(rca_id)
        assert doc["id"] == rca_id, (
            f"id field '{doc['id']}' does not match filename '{rca_id}'"
        )

    def test_doc_type_valid(self, rca_id: str):
        doc = _load_rca(rca_id)
        assert doc["doc_type"] in VALID_DOC_TYPES, (
            f"Invalid doc_type '{doc['doc_type']}'; must be one of {VALID_DOC_TYPES}"
        )

    def test_priority_valid(self, rca_id: str):
        doc = _load_rca(rca_id)
        assert doc["priority"] in VALID_PRIORITIES

    def test_service_valid(self, rca_id: str):
        doc = _load_rca(rca_id)
        assert isinstance(doc["service"], list) and len(doc["service"]) >= 1
        for s in doc["service"]:
            assert s in VALID_SERVICES, f"Invalid service '{s}'"

    def test_fault_type_valid(self, rca_id: str):
        doc = _load_rca(rca_id)
        assert isinstance(doc["fault_type"], list) and len(doc["fault_type"]) >= 1
        for ft in doc["fault_type"]:
            assert ft in VALID_FAULT_TYPES, f"Invalid fault_type '{ft}'"

    def test_environment_valid(self, rca_id: str):
        doc = _load_rca(rca_id)
        assert isinstance(doc["environment"], list) and len(doc["environment"]) >= 1
        for env in doc["environment"]:
            assert env in VALID_ENVIRONMENTS

    def test_confidence_level_valid(self, rca_id: str):
        doc = _load_rca(rca_id)
        assert doc["confidence_level"] in VALID_CONFIDENCE

    def test_last_validated_date_iso_format(self, rca_id: str):
        from datetime import date
        doc = _load_rca(rca_id)
        d = doc["last_validated_date"]
        # Must parse as ISO date
        parsed = date.fromisoformat(d)
        assert parsed.year >= 2024, f"Unexpected year in date: {d}"

    def test_vector_tags_non_empty(self, rca_id: str):
        doc = _load_rca(rca_id)
        assert isinstance(doc["vector_tags"], list) and len(doc["vector_tags"]) > 0

    def test_source_structure(self, rca_id: str):
        doc = _load_rca(rca_id)
        src = doc["source"]
        assert "source_type" in src and "uri" in src
        assert src["source_type"] in VALID_SOURCE_TYPES
        assert isinstance(src["uri"], str) and len(src["uri"]) > 0

    def test_content_has_text(self, rca_id: str):
        doc = _load_rca(rca_id)
        assert "text" in doc["content"]
        assert isinstance(doc["content"]["text"], str) and len(doc["content"]["text"]) > 0

    def test_content_phase_valid_if_present(self, rca_id: str):
        doc = _load_rca(rca_id)
        phase = doc["content"].get("phase")
        if phase is not None:
            assert phase in VALID_PHASES, f"Invalid phase '{phase}'"

    def test_dependencies_structure_if_present(self, rca_id: str):
        doc = _load_rca(rca_id)
        deps = doc.get("dependencies", [])
        for dep in deps:
            assert "depends_on" in dep and "dependency_type" in dep
            assert dep["dependency_type"] in VALID_DEP_TYPES

    def test_guardrails_structure_if_present(self, rca_id: str):
        doc = _load_rca(rca_id)
        for gr in doc.get("guardrails", []):
            assert "type" in gr and "rule" in gr
            assert gr["type"] in VALID_GUARDRAIL_TYPES

    def test_automation_scope_if_present(self, rca_id: str):
        doc = _load_rca(rca_id)
        scope = doc.get("automation_scope")
        if scope is None:
            return
        for sys_name in scope.get("automation_systems", []):
            assert sys_name in VALID_AUTOMATION_SYSTEMS, f"Invalid automation system '{sys_name}'"

    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema package not installed")
    def test_validates_against_canonical_schema(self, rca_id: str):
        schema = _load_schema()
        doc = _load_rca(rca_id)
        # Remove internal _source_file key if present (added by KnowledgeBaseService at runtime)
        doc.pop("_source_file", None)
        jsonschema.validate(instance=doc, schema=schema)


class TestGeneratedRcaSetCoverage:
    """Cross-document tests ensuring the full set covers required fault types and services."""

    def test_all_three_files_present(self):
        for rca_id in GENERATED_IDS:
            path = RCAS_DIR / f"{rca_id}.json"
            assert path.exists()

    def test_covers_power_down_fault(self):
        docs = [_load_rca(i) for i in GENERATED_IDS]
        fault_types = {ft for d in docs for ft in d["fault_type"]}
        assert "power_down" in fault_types

    def test_covers_data_loss_fault(self):
        docs = [_load_rca(i) for i in GENERATED_IDS]
        fault_types = {ft for d in docs for ft in d["fault_type"]}
        assert "data_loss" in fault_types

    def test_covers_pfvm_service(self):
        docs = [_load_rca(i) for i in GENERATED_IDS]
        services = {s for d in docs for s in d["service"]}
        assert "PFVM" in services

    def test_covers_dm_service(self):
        docs = [_load_rca(i) for i in GENERATED_IDS]
        services = {s for d in docs for s in d["service"]}
        assert "DM" in services

    def test_dm_dataloss_is_p0(self):
        doc = _load_rca("rca-dm-dataloss-drill-2026-04")
        assert doc["priority"] == "P0"

    def test_all_docs_are_drill_reports(self):
        for rca_id in GENERATED_IDS:
            doc = _load_rca(rca_id)
            assert doc["doc_type"] == "Drill_Report"

    def test_all_ids_unique(self):
        ids = [_load_rca(i)["id"] for i in GENERATED_IDS]
        assert len(ids) == len(set(ids))


class TestGeneratorScript:
    """Smoke-tests the generate_rca_json.py script logic (dry-run, no file writes)."""

    @staticmethod
    def _load_generator_module():
        script_path = Path(__file__).parent.parent / "scripts" / "generate_rca_json.py"
        spec = importlib.util.spec_from_file_location("generate_rca_json", script_path)
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod

    def test_script_importable(self):
        mod = self._load_generator_module()
        assert hasattr(mod, "transform_document")
        assert hasattr(mod, "run")

    def test_transform_returns_required_fields(self):
        mod = self._load_generator_module()
        # Use any existing source document (first .docx found)
        src_docs = sorted(RCAS_DIR.glob("*.docx"))
        if not src_docs:
            pytest.skip("No .docx source documents available")
        result = mod.transform_document(src_docs[0])
        for field in REQUIRED_FIELDS:
            assert field in result, f"transform_document missing '{field}'"

    def test_build_id_deterministic(self):
        mod = self._load_generator_module()
        id1 = mod._build_id("PFVM Power down Scoped Drill Proposal")
        id2 = mod._build_id("PFVM Power down Scoped Drill Proposal")
        assert id1 == id2, "ID generation must be deterministic"
        assert id1.startswith("rca-")
        assert id1 == id1.lower()
