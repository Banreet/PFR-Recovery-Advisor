# Knowledge Base – RCAs

This folder holds **source RCA/drill documents** (`.docx`) and the corresponding
**generated JSON files** that conform to the
[Canonical Schema](../Canonical%20Schema) used by the PFR Recovery Advisor.

---

## Contents

| File | Type | Description |
|------|------|-------------|
| `PFVM Power down Scoped Drill Proposal.docx` | Source | PFVM power-down scoped drill proposal (Apr 2026) |
| `[Drill] PFVM Test FC recovery on PFVMs using Soft Delete May 2026.docx` | Source | PFVM Fault Controller recovery via Soft Delete drill (May 2026) |
| `[PFR] DM Dataloss drill April-26.docx` | Source | DM data-loss PFR drill (April 2026) |
| `rca-pfvm-powerdown-scoped-drill-2026-04.json` | Generated | JSON for PFVM power-down drill proposal |
| `rca-pfvm-fc-softdelete-drill-2026-05.json` | Generated | JSON for PFVM FC Soft Delete recovery drill |
| `rca-dm-dataloss-drill-2026-04.json` | Generated | JSON for DM dataloss drill |
| `sample_rca_001.json` | Legacy | Legacy incident-style RCA (pre-schema) |

---

## JSON Naming Convention

Generated JSON files are named after their stable `id` field:

```
rca-<service>-<fault-hint>-<date-hint>.json
```

The `id` is derived deterministically from the source document filename by the
generator script (see below).  The `id` is guaranteed to be:
- Lowercase
- Hyphen-separated
- Prefixed with `rca-`
- Stable across re-generation (i.e. re-running the script will overwrite, not duplicate)

---

## Scope: Last 3 Months (2026-01-29 → 2026-04-29)

All three source documents were authored or last-validated in April 2026, within
the three-month window.  All are **scoped outage drills** – controlled fault-injection
exercises targeting a specific service (PFVM, DM) within a bounded scope.

---

## (Re)Generating JSON Files

A generator script is provided at `backend/scripts/generate_rca_json.py`.

### Requirements

```bash
pip install olefile            # reads OLE2 legacy .doc metadata
pip install python-docx        # reads unlocked .docx body text
pip install jsonschema         # optional – enables schema validation in tests
```

### Usage

```bash
# Generate JSON for documents created in the last 90 days (default):
python3 backend/scripts/generate_rca_json.py

# Generate JSON for documents since a specific date:
python3 backend/scripts/generate_rca_json.py --since 2026-01-29

# Preview without writing files:
python3 backend/scripts/generate_rca_json.py --dry-run
```

The script writes one `<id>.json` file per source document it processes,
placing it in the same `rcas/` directory.

---

## Assumptions & Field Mappings

The source `.docx` files are **MIP-protected** (Microsoft Information Protection,
label: *Confidential – Internal Only*).  Their body text is encrypted with Azure
Rights Management and cannot be decrypted without tenant credentials.  The
generator therefore derives all fields from:

1. **Filename** – title, service, fault type, doc type, date hints
2. **OLE SummaryInformation stream** – author, last-saved-by, create/modify date,
   page count, word count
3. **MIP LabelInfo XML** – DRM key issuance date

Specific assumptions made per field:

| Field | Assumption |
|-------|-----------|
| `source.source_type` | All documents are assumed to originate from **SharePoint** |
| `service` | Derived from acronyms in filename (PFVM, DM, SEC, …); defaults to `Platform` |
| `fault_type` | Derived from filename keywords; FC failure → `zone_down`; defaults to `unknown` |
| `environment` | Defaults to `["prod"]` – drills target production recovery procedures |
| `confidence_level` | `"high"` for executed drills; `"medium"` for proposals |
| `priority` | `"P0"` for data-loss scenarios; `"P1"` for all others |
| `content.phase` | `"pre_drill"` for proposals/power-down; `"fault_injection"` for active FC drills; `"recovery"` for data-loss drills |
| `content.text` | Structured metadata summary (page count, author, dates) when body is inaccessible; actual extracted text when the document is unlocked |

Update `backend/scripts/generate_rca_json.py` when new `service` or `fault_type`
enum values are added to the Canonical Schema.

---

## Validation

```bash
cd backend
pytest tests/test_rca_json.py -v
```

Tests verify:
- All three generated files exist and contain valid JSON
- All required Canonical Schema fields are present
- All enum values are within allowed sets
- `id` matches the filename
- `last_validated_date` is a valid ISO date
- (When `jsonschema` is installed) Full JSON Schema validation against the Canonical Schema
