#!/usr/bin/env python3
"""
generate_rca_json.py
--------------------
Scans backend/knowledge_base/rcas/ for source RCA/drill documents (.docx, .doc, .txt, .md)
and emits a corresponding JSON file per document that conforms to the Canonical Schema
(backend/knowledge_base/Canonical Schema).

Usage
-----
    python3 backend/scripts/generate_rca_json.py [--since YYYY-MM-DD] [--dry-run]

    --since   Only process documents whose OLE/filesystem creation date falls on or after
              this date (ISO 8601, default: 90 days before today).
    --dry-run Print the JSON that would be written without writing any files.

Design notes
------------
* The .docx files currently in the repository are MIP-protected (Confidential – Internal Only)
  and their body text cannot be decrypted without Microsoft 365 tenant credentials.  The script
  therefore derives as many schema fields as possible from:
    1. The document filename (title, service, fault_type, drill date hints)
    2. OLE Compound Document metadata (author, page count, word count, create/modify dates)
    3. MIP label XML embedded in the OLE DataSpaces stream
  and fills the `content.text` field with a structured summary of those metadata facts.

* When a document IS readable (plain-text .md / .txt, or an unlocked .docx), the script
  will use python-docx to extract paragraph text and populate `content.text` with up to
  2 000 characters of actual body content.

* Field mapping assumptions are documented inline with "# ASSUMPTION:" comments.

* The output filename is derived deterministically from the generated `id` field:
    <id>.json  →  placed next to the source document in rcas/.

Extend this script when new fault_type / service values are added to the Canonical Schema.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ── Optional imports (graceful degradation) ──────────────────────────────────
try:
    import olefile  # pip install olefile  – reads OLE2 compound documents
    HAS_OLEFILE = True
except ImportError:
    HAS_OLEFILE = False

try:
    from docx import Document as DocxDocument  # pip install python-docx
    HAS_PYTHON_DOCX = True
except ImportError:
    HAS_PYTHON_DOCX = False

# ── Constants ─────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
KB_ROOT = REPO_ROOT / "backend" / "knowledge_base"
RCAS_DIR = KB_ROOT / "rcas"
SCHEMA_PATH = KB_ROOT / "Canonical Schema"

# Maps filename keywords → service enum values (schema: DM | SEC | PFVM | Titan | ZK | Platform | Multi)
# ASSUMPTION: Service names are inferred from well-known acronyms in file names.
_SERVICE_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bpfvm\b", re.IGNORECASE), "PFVM"),
    (re.compile(r"\bsec\b",  re.IGNORECASE), "SEC"),
    (re.compile(r"\btitan\b", re.IGNORECASE), "Titan"),
    (re.compile(r"\b(zk|zookeeper)\b", re.IGNORECASE), "ZK"),
    (re.compile(r"\bdm\b",   re.IGNORECASE), "DM"),
    (re.compile(r"\bplatform\b", re.IGNORECASE), "Platform"),
]

# Maps filename keywords → fault_type enum values
# (schema: data_loss | power_down | zone_down | dependency_loss | hardware_failure | unknown)
# ASSUMPTION: Fault types are inferred from drill/incident keywords in file names.
_FAULT_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"data.?loss|dataloss", re.IGNORECASE), "data_loss"),
    (re.compile(r"power.?down|powerdown", re.IGNORECASE), "power_down"),
    (re.compile(r"zone.?down|zonedown", re.IGNORECASE), "zone_down"),
    (re.compile(r"dependency.?loss", re.IGNORECASE), "dependency_loss"),
    (re.compile(r"hardware.?fail|hw.?fail", re.IGNORECASE), "hardware_failure"),
    # FC (Fault Controller) failure maps to zone_down – ASSUMPTION: FC failure is zone-scoped.
    (re.compile(r"\bfc\b.*recov|recov.*\bfc\b", re.IGNORECASE), "zone_down"),
]

# Maps filename keywords → doc_type enum values
_DOCTYPE_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\[drill\]|drill", re.IGNORECASE), "Drill_Report"),
    (re.compile(r"proposal", re.IGNORECASE), "Drill_Report"),
    (re.compile(r"\brca\b", re.IGNORECASE), "RCA"),
    (re.compile(r"tsg|troubleshoot", re.IGNORECASE), "Recovery_TSG"),
    (re.compile(r"design|context", re.IGNORECASE), "Design_Context"),
]

# Maps fault_type → guardrail suggestions
_DEFAULT_GUARDRAILS: dict[str, list[dict[str, str]]] = {
    "data_loss": [
        {"type": "data_loss_risk",
         "rule": "No writes to affected partitions until restore protocol completes and integrity check passes"},
        {"type": "authorization",
         "rule": "Data-loss recovery requires explicit approval from service owner and PFR DRI before execution"},
    ],
    "power_down": [
        {"type": "authorization",
         "rule": "Power-down drills require DRI sign-off and approved change management ticket before execution"},
        {"type": "data_loss_risk",
         "rule": "Ensure soft-delete or snapshot backup is completed before initiating power-down sequence"},
    ],
    "zone_down": [
        {"type": "data_loss_risk",
         "rule": "Soft Delete must be confirmed enabled on all in-scope nodes before triggering recovery sequence"},
        {"type": "authorization",
         "rule": "Zone-down recovery drills must run inside an approved maintenance window with DRI oversight"},
    ],
}


# ── OLE metadata helpers ──────────────────────────────────────────────────────

def _read_ole_metadata(path: Path) -> dict[str, Any]:
    """Return a dict of useful fields extracted from an OLE2 compound document."""
    if not HAS_OLEFILE:
        return {}
    try:
        ole = olefile.OleFileIO(str(path))
    except Exception:
        return {}

    meta: dict[str, Any] = {}

    # SummaryInformation (PIDSI constants):
    #   4=Author, 8=LastSavedBy, 12=CreateTime, 13=LastSavedTime, 14=PageCount, 15=WordCount
    if ole.exists("\x05SummaryInformation"):
        try:
            si = ole.getproperties("\x05SummaryInformation", convert_time=True)
            meta["author"] = (si.get(4) or b"").decode("latin-1", errors="replace").strip()
            meta["last_saved_by"] = (si.get(8) or b"").decode("latin-1", errors="replace").strip()
            ct = si.get(12)
            if isinstance(ct, datetime) and ct.year > 1601:
                meta["create_time"] = ct.date().isoformat()
            lt = si.get(13)
            if isinstance(lt, datetime) and lt.year > 1601:
                meta["last_saved_time"] = lt.date().isoformat()
            meta["page_count"] = si.get(14)
            meta["word_count"] = si.get(15)
        except Exception:
            pass

    # MIP DRM issue time from LabelInfo stream
    label_stream = ["\x06DataSpaces", "TransformInfo", "LabelInfo"]
    if ole.exists(label_stream):
        try:
            xml_bytes = ole.openstream(label_stream).read()
            m = re.search(r"<ISSUEDTIME>([^<]+)</ISSUEDTIME>", xml_bytes.decode("utf-8", errors="replace"))
            if m:
                meta["drm_issued"] = m.group(1)[:10]  # YYYY-MM-DD
        except Exception:
            pass

    ole.close()
    return meta


# ── Text extraction helpers ───────────────────────────────────────────────────

def _extract_text_docx(path: Path, max_chars: int = 2000) -> str:
    """Return up to max_chars of body text from an unlocked .docx using python-docx."""
    if not HAS_PYTHON_DOCX:
        return ""
    try:
        doc = DocxDocument(str(path))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        full = " ".join(parts)
        return full[:max_chars]
    except Exception:
        return ""


def _extract_text_plaintext(path: Path, max_chars: int = 2000) -> str:
    """Return up to max_chars of content from a plain-text file (.md, .txt)."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except Exception:
        return ""


# ── Field inference helpers ───────────────────────────────────────────────────

def _deduplicate(items: list[str]) -> list[str]:
    """Return a deduplicated list preserving original insertion order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _infer_services(name: str) -> list[str]:
    services = [val for pat, val in _SERVICE_HINTS if pat.search(name)]
    if not services:
        services = ["Platform"]  # ASSUMPTION: fallback to Platform if unknown
    return _deduplicate(services)


def _infer_fault_types(name: str) -> list[str]:
    faults = [val for pat, val in _FAULT_HINTS if pat.search(name)]
    if not faults:
        faults = ["unknown"]
    return _deduplicate(faults)


def _infer_doc_type(name: str) -> str:
    for pat, dtype in _DOCTYPE_HINTS:
        if pat.search(name):
            return dtype
    return "RCA"  # ASSUMPTION: default doc_type is RCA if no keywords match


def _infer_drill_date(name: str, ole_meta: dict[str, Any]) -> str:
    """
    Return an ISO date string for when the drill/incident took place.
    Priority: explicit date in filename → DRM issued time → OLE create time → today.
    """
    # Pattern: Month-YY or Month-YYYY anywhere in name
    m = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[- _](\d{2,4})",
                  name, re.IGNORECASE)
    if m:
        month_str = m.group(1)[:3].capitalize()
        year_str = m.group(2)
        year = int(year_str) if len(year_str) == 4 else (2000 + int(year_str))
        month_map = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
        }
        day = 1
        try:
            return date(year, month_map[month_str], day).isoformat()
        except (ValueError, KeyError):
            pass

    # Pattern: YYYY-MM anywhere
    m2 = re.search(r"(20\d{2})[- _](\d{2})", name)
    if m2:
        try:
            return date(int(m2.group(1)), int(m2.group(2)), 1).isoformat()
        except ValueError:
            pass

    if ole_meta.get("drm_issued"):
        return ole_meta["drm_issued"]
    if ole_meta.get("create_time"):
        return ole_meta["create_time"]
    return date.today().isoformat()


def _build_id(stem: str) -> str:
    """
    Convert a document filename stem to a stable, lowercase slug for use as the `id` field.
    Brackets, special characters, and runs of spaces/hyphens are normalised.
    ASSUMPTION: The id is deterministic and derived solely from the stem (not content).
    """
    s = re.sub(r"[\[\](){}]", "", stem)     # remove brackets
    s = re.sub(r"[^a-zA-Z0-9\s\-]", "", s)  # keep alphanum, spaces, hyphens
    s = re.sub(r"[\s_]+", "-", s.strip())    # spaces → hyphens
    s = re.sub(r"-{2,}", "-", s)             # collapse runs
    return "rca-" + s.lower().strip("-")


def _build_vector_tags(name: str, services: list[str], fault_types: list[str]) -> list[str]:
    tags: list[str] = list(services) + list(fault_types) + ["scoped_outage"]
    # Add extra semantic tags from filename keywords
    kw_map = {
        "drill": "drill",
        "proposal": "drill_proposal",
        "soft.?delete": "soft_delete",
        r"\bfc\b|fault.?controller": "fault_controller",
        "recovery": "recovery",
        "pfr": "PFR",
        "scoped": "scoped_drill",
    }
    for pattern, tag in kw_map.items():
        if re.search(pattern, name, re.IGNORECASE) and tag not in tags:
            tags.append(tag)
    return tags


def _build_guardrails(fault_types: list[str]) -> list[dict[str, str]]:
    guardrails: list[dict[str, str]] = []
    seen: set[str] = set()
    for ft in fault_types:
        for gr in _DEFAULT_GUARDRAILS.get(ft, []):
            key = gr["rule"]
            if key not in seen:
                guardrails.append(gr)
                seen.add(key)
    if not guardrails:
        guardrails.append({"type": "authorization",
                           "rule": "Recovery actions require DRI approval and an approved change ticket"})
    return guardrails


def _build_content_text(
    stem: str,
    ole_meta: dict[str, Any],
    body_text: str,
) -> str:
    if body_text:
        return body_text
    # Build a structured summary from available metadata when body is inaccessible (MIP encrypted)
    parts = [f'Source document: "{stem}"']
    if ole_meta.get("page_count"):
        parts.append(f"{ole_meta['page_count']} pages")
    if ole_meta.get("word_count"):
        parts.append(f"~{ole_meta['word_count']} words")
    if ole_meta.get("author"):
        parts.append(f"Author: {ole_meta['author']}")
    if ole_meta.get("last_saved_by"):
        parts.append(f"Last saved by: {ole_meta['last_saved_by']}")
    if ole_meta.get("create_time"):
        parts.append(f"Document created: {ole_meta['create_time']}")
    if ole_meta.get("drm_issued"):
        parts.append(f"DRM key issued: {ole_meta['drm_issued']}")
    summary = ". ".join(parts) + "."
    note = (
        " NOTE: Source document is MIP-protected (Confidential – Internal Only); "
        "all structured fields are derived from document filename, OLE metadata, "
        "and MIP label data – the ciphertext is inaccessible without tenant credentials."
    )
    return summary + note


def _infer_phase(doc_type: str, fault_types: list[str]) -> str:
    if doc_type in ("Drill_Report", "Drill_Master_ICM"):
        if "power_down" in fault_types:
            return "pre_drill"
        if "data_loss" in fault_types:
            return "recovery"
        return "fault_injection"
    return "post_incident"  # ASSUMPTION: non-drill RCAs default to post_incident phase


# ── Core document → JSON transform ───────────────────────────────────────────

_EXCLUDE_NAMES = frozenset({"readme.md", "readme.txt", "readme"})


def _is_source_document(path: Path) -> bool:
    """Return True if the file should be treated as an RCA source document.

    Excluded: README files, already-generated JSON files, and hidden/system files.
    """
    if path.name.startswith("."):
        return False
    if path.name.lower() in _EXCLUDE_NAMES:
        return False
    return path.suffix.lower() in {".docx", ".doc", ".md", ".txt"}


def transform_document(path: Path) -> dict[str, Any]:
    """
    Transform a single RCA source document into a Canonical Schema JSON object.
    Raises ValueError if the file cannot be mapped to required schema fields.
    """
    stem = path.stem
    name = path.name

    ole_meta = _read_ole_metadata(path)

    # Try to extract real body text (only works for unlocked docx / plain text)
    body_text = ""
    if path.suffix.lower() == ".docx":
        body_text = _extract_text_docx(path)
    elif path.suffix.lower() in {".md", ".txt"}:
        body_text = _extract_text_plaintext(path)

    services = _infer_services(name)
    fault_types = _infer_fault_types(name)
    doc_type = _infer_doc_type(name)
    drill_date = _infer_drill_date(name, ole_meta)
    doc_id = _build_id(stem)
    vector_tags = _build_vector_tags(name, services, fault_types)
    guardrails = _build_guardrails(fault_types)
    content_text = _build_content_text(stem, ole_meta, body_text)
    phase = _infer_phase(doc_type, fault_types)

    # ASSUMPTION: All drills target prod; adjust manually if canary/euap drills appear.
    environment = ["prod"]

    # ASSUMPTION: confidence_level is "high" for executed drills, "medium" for proposals.
    confidence_level = "medium" if re.search(r"proposal", name, re.IGNORECASE) else "high"

    # ASSUMPTION: DM data-loss drills are P0 (highest); other drill types are P1.
    priority = "P0" if "data_loss" in fault_types else "P1"

    return {
        "id": doc_id,
        "title": stem.lstrip("[").replace("[", "").replace("]", "").strip(),
        "doc_type": doc_type,
        "priority": priority,
        "source": {
            "source_type": "SharePoint",  # ASSUMPTION: all docs originate from SharePoint
            "uri": f"rcas/{name}",
        },
        "service": services,
        "fault_type": fault_types,
        "environment": environment,
        "confidence_level": confidence_level,
        "last_validated_date": drill_date,
        "vector_tags": vector_tags,
        "guardrails": guardrails,
        "content": {
            "text": content_text,
            "phase": phase,
        },
    }


# ── Date filtering ─────────────────────────────────────────────────────────────

def _document_date(path: Path, ole_meta: dict[str, Any]) -> date:
    """Best-effort document date for --since filtering."""
    # Prefer OLE create_time, fall back to file mtime
    raw = ole_meta.get("create_time") or ole_meta.get("drm_issued")
    if raw:
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            pass
    return date.fromtimestamp(path.stat().st_mtime)


# ── Main entry point ──────────────────────────────────────────────────────────

def run(since: date, dry_run: bool = False) -> None:
    if not RCAS_DIR.is_dir():
        print(f"ERROR: RCAs directory not found: {RCAS_DIR}", file=sys.stderr)
        sys.exit(1)

    source_docs = sorted(p for p in RCAS_DIR.iterdir() if _is_source_document(p))
    if not source_docs:
        print("No source RCA documents found.", file=sys.stderr)
        return

    generated = 0
    for src in source_docs:
        ole_meta = _read_ole_metadata(src)
        doc_date = _document_date(src, ole_meta)
        if doc_date < since:
            print(f"  SKIP (too old: {doc_date}): {src.name}")
            continue

        try:
            item = transform_document(src)
        except Exception as exc:
            print(f"  ERROR transforming {src.name}: {exc}", file=sys.stderr)
            continue

        out_path = RCAS_DIR / f"{item['id']}.json"
        json_text = json.dumps(item, indent=2, ensure_ascii=False)

        if dry_run:
            print(f"\n{'─'*60}")
            print(f"Would write: {out_path.name}")
            print(json_text)
        else:
            out_path.write_text(json_text, encoding="utf-8")
            print(f"  WROTE: {out_path.name}")
        generated += 1

    print(f"\n{'Dry-run: would generate' if dry_run else 'Generated'} {generated} JSON file(s).")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Canonical Schema JSON files from RCA source documents."
    )
    default_since = (date.today() - timedelta(days=90)).isoformat()
    parser.add_argument(
        "--since",
        default=default_since,
        help=f"Only process documents on or after this ISO date (default: {default_since})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print JSON output without writing files",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        since_date = date.fromisoformat(args.since)
    except ValueError:
        print(f"ERROR: --since must be an ISO date (YYYY-MM-DD), got: {args.since}", file=sys.stderr)
        sys.exit(1)
    run(since=since_date, dry_run=args.dry_run)
