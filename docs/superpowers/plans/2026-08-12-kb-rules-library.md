# Recordings KB — Phase 1: Rules Library — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pure, fully unit-tested Python package holding every decision rule the KB depends on — the logic that decides whether the system leaks, lies, or silently returns nothing.

**Architecture:** `kb/rules/` contains only pure functions: no network, no filesystem, no Google API, no LLM calls. Everything is passed in and returned. This is what makes the leak-prevention rules verifiable, and it is the only phase that can be built before the Plaud and Drive connectors are authorized. Later phases (Drive client, source adapters, ingest, retrieval, skills) call into this package.

**Tech Stack:** Python 3.14, pytest. No third-party runtime dependencies in this phase — that is a deliberate constraint, not an omission.

**Spec:** `docs/specs/2026-08-12-recordings-kb-design.md` · decisions `docs/specs/2026-08-12-recordings-kb-decisions.md` (D1–D11)

## Global Constraints

- **Pure functions only.** No module in `kb/rules/` may import `requests`, `google.*`, `os`, or `pathlib`. A rule that touches the outside world is not a rule.
- **Reject, never repair.** When input violates a contract, discard it and report why. Never silently coerce.
- **Default deny.** Any ambiguity resolves to the more restrictive outcome.
- **Never log sensitive content.** Log the rule that fired and a count. Never the matched text (spec §2.2).
- Python ≥ 3.13 (`3.14.5` present locally). Test command is always `python3 -m pytest`.
- Every task ends with a commit.

---

### Task 1: Project scaffolding and record identity

**Files:**
- Create: `kb/__init__.py`, `kb/rules/__init__.py`, `kb/rules/records.py`
- Create: `tests/__init__.py`, `tests/test_records.py`
- Create: `pyproject.toml`

**Interfaces:**
- Consumes: nothing.
- Produces: `record_id(source: str, source_id: str) -> str`; `content_hash(text: str) -> str`; `needs_reextraction(existing: dict | None, incoming_hash: str, extractor_version: str) -> bool`

- [ ] **Step 1: Write the failing test**

Create `tests/test_records.py`:

```python
from kb.rules.records import record_id, content_hash, needs_reextraction


def test_record_id_is_source_prefixed():
    assert record_id("plaud", "a1b2c3") == "plaud:a1b2c3"


def test_record_id_ignores_title_entirely():
    # Titles are not unique and change upstream (spec 1.2). Identity must not involve them.
    assert record_id("plaud", "x") == record_id("plaud", "x")


def test_content_hash_is_stable_and_prefixed():
    h = content_hash("hello world")
    assert h.startswith("sha256:")
    assert h == content_hash("hello world")


def test_content_hash_differs_on_change():
    assert content_hash("a") != content_hash("b")


def test_reextraction_needed_when_record_is_new():
    assert needs_reextraction(None, "sha256:abc", "v1") is True


def test_reextraction_skipped_when_unchanged():
    existing = {"content_hash": "sha256:abc", "extractor_version": "v1"}
    assert needs_reextraction(existing, "sha256:abc", "v1") is False


def test_reextraction_needed_when_content_changed():
    existing = {"content_hash": "sha256:abc", "extractor_version": "v1"}
    assert needs_reextraction(existing, "sha256:zzz", "v1") is True


def test_reextraction_needed_when_extractor_upgraded():
    existing = {"content_hash": "sha256:abc", "extractor_version": "v1"}
    assert needs_reextraction(existing, "sha256:abc", "v2") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_records.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kb'`

- [ ] **Step 3: Write minimal implementation**

Create `pyproject.toml`:

```toml
[project]
name = "recordings-kb"
version = "0.1.0"
requires-python = ">=3.13"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

Create empty `kb/__init__.py`, `kb/rules/__init__.py`, `tests/__init__.py`.

Create `kb/rules/records.py`:

```python
"""Record identity and re-extraction decisions (spec 1.2, 2.5)."""

import hashlib


def record_id(source: str, source_id: str) -> str:
    """Stable primary key. Deduplication keys on this, never on title."""
    return f"{source}:{source_id}"


def content_hash(text: str) -> str:
    """Detects upstream change so unchanged records skip re-distillation entirely."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def needs_reextraction(
    existing: dict | None, incoming_hash: str, extractor_version: str
) -> bool:
    """True when claims must be regenerated. Absent record, changed content, or a
    newer extractor all force it; anything else is skipped at no cost."""
    if existing is None:
        return True
    if existing.get("content_hash") != incoming_hash:
        return True
    if existing.get("extractor_version") != extractor_version:
        return True
    return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_records.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml kb/ tests/
git commit -m "feat(rules): record identity and re-extraction decisions"
```

---

### Task 2: Exclusion matching and non-describing skip logs

**Files:**
- Create: `kb/rules/exclusion.py`, `tests/test_exclusion.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `ExclusionRule` (NamedTuple: `rule_id: str`, `field: str`, `pattern: str`); `matches_exclusion(meta: dict, rules: list[ExclusionRule]) -> str | None`; `skip_log_line(rule_id: str, count: int) -> str`

- [ ] **Step 1: Write the failing test**

Create `tests/test_exclusion.py`:

```python
from kb.rules.exclusion import ExclusionRule, matches_exclusion, skip_log_line

RULES = [
    ExclusionRule("no_one_to_ones", "title", r"1:1"),
    ExclusionRule("no_comp", "title", r"\b(comp|compensation|salary)\b"),
    ExclusionRule("no_hr_folder", "folder", r"^HR$"),
    ExclusionRule("no_hr_people", "participants", r"head of people"),
]


def test_returns_rule_id_on_title_match():
    meta = {"title": "1:1 with Jamie"}
    assert matches_exclusion(meta, RULES) == "no_one_to_ones"


def test_match_is_case_insensitive():
    assert matches_exclusion({"title": "Salary review"}, RULES) == "no_comp"


def test_matches_on_folder_field():
    assert matches_exclusion({"folder": "HR"}, RULES) == "no_hr_folder"


def test_matches_across_list_valued_fields():
    meta = {"participants": ["Ana", "Head of People"]}
    assert matches_exclusion(meta, RULES) == "no_hr_people"


def test_returns_none_when_nothing_matches():
    assert matches_exclusion({"title": "Partner call - Acme"}, RULES) is None


def test_missing_field_does_not_crash():
    assert matches_exclusion({}, RULES) is None


def test_first_matching_rule_wins():
    meta = {"title": "1:1 about comp"}
    assert matches_exclusion(meta, RULES) == "no_one_to_ones"


def test_skip_log_never_contains_the_excluded_content():
    """The whole point of spec 2.2: a descriptive skip log recreates the leak
    in a file with different permissions."""
    secret_title = "1:1 with Jamie - compensation review"
    line = skip_log_line("no_one_to_ones", 3)
    assert "Jamie" not in line
    assert "compensation" not in line
    assert secret_title not in line


def test_skip_log_reports_rule_and_count():
    line = skip_log_line("no_comp", 2)
    assert "no_comp" in line
    assert "2" in line
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_exclusion.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kb.rules.exclusion'`

- [ ] **Step 3: Write minimal implementation**

Create `kb/rules/exclusion.py`:

```python
"""Never-ingest matching (spec 2.2).

Evaluated before content is fetched, so excluded material never enters context.
"""

import re
from typing import NamedTuple


class ExclusionRule(NamedTuple):
    rule_id: str
    field: str
    pattern: str


def matches_exclusion(meta: dict, rules: list[ExclusionRule]) -> str | None:
    """Return the id of the first rule that fires, or None.

    Returns the rule id rather than the matched text on purpose — callers must
    never be handed the sensitive value to log.
    """
    for rule in rules:
        value = meta.get(rule.field)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            value = " ".join(str(v) for v in value)
        if re.search(rule.pattern, str(value), re.IGNORECASE):
            return rule.rule_id
    return None


def skip_log_line(rule_id: str, count: int) -> str:
    """The only sanctioned way to log an exclusion.

    Takes a rule id and a count, never the item, so it is structurally incapable
    of reproducing what was excluded.
    """
    return f"skipped {count} item(s) (rule: {rule_id})"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_exclusion.py -v`
Expected: PASS — 9 passed

- [ ] **Step 5: Commit**

```bash
git add kb/rules/exclusion.py tests/test_exclusion.py
git commit -m "feat(rules): exclusion matching with non-describing skip logs"
```

---

### Task 3: Verbatim evidence validation

**Files:**
- Create: `kb/rules/evidence.py`, `tests/test_evidence.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `normalize(text: str) -> str`; `is_verbatim(evidence: str, source: str) -> bool`

- [ ] **Step 1: Write the failing test**

Create `tests/test_evidence.py`:

```python
from kb.rules.evidence import is_verbatim, normalize

SOURCE = """
So the thing is, we agreed to hold  pricing  at forty-nine
until the Acme deal closes. Ana said she'd own the follow-up.
"""


def test_exact_span_is_verbatim():
    assert is_verbatim("we agreed to hold  pricing  at forty-nine", SOURCE) is True


def test_whitespace_differences_are_tolerated():
    assert is_verbatim("we agreed to hold pricing at forty-nine", SOURCE) is True


def test_line_breaks_are_tolerated():
    assert is_verbatim("at forty-nine until the Acme deal closes", SOURCE) is True


def test_case_differences_are_tolerated():
    assert is_verbatim("ANA SAID SHE'D OWN THE FOLLOW-UP", SOURCE) is True


def test_paraphrase_is_rejected():
    assert is_verbatim("we decided to keep the price the same", SOURCE) is False


def test_plausible_fabrication_is_rejected():
    assert is_verbatim("Ana agreed to a discount for Acme", SOURCE) is False


def test_empty_evidence_is_rejected():
    assert is_verbatim("", SOURCE) is False
    assert is_verbatim("   ", SOURCE) is False


def test_normalize_collapses_whitespace_and_case():
    assert normalize("  Hello   WORLD \n x ") == "hello world x"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_evidence.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kb.rules.evidence'`

- [ ] **Step 3: Write minimal implementation**

Create `kb/rules/evidence.py`:

```python
"""Verbatim evidence checking (spec 2.4).

The strongest practical anti-fabrication guard available, and nearly free:
string containment either holds or it does not. No judgement involved.
"""

import re

_WHITESPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Collapse whitespace and case so transcription line breaks do not cause
    false rejections. Nothing else is altered — this must not become lenient."""
    return _WHITESPACE.sub(" ", text).strip().lower()


def is_verbatim(evidence: str, source: str) -> bool:
    """True when the evidence span genuinely appears in the source.

    A claim failing this is discarded, never repaired (spec 2.4 rule 1).
    """
    if not evidence or not evidence.strip():
        return False
    return normalize(evidence) in normalize(source)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_evidence.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
git add kb/rules/evidence.py tests/test_evidence.py
git commit -m "feat(rules): verbatim evidence validation"
```

---

### Task 4: Distillation contract validation

**Files:**
- Create: `kb/rules/claims.py`, `tests/test_claims.py`

**Interfaces:**
- Consumes: `kb.rules.evidence.is_verbatim`
- Produces: `CLAIM_TYPES: frozenset[str]`; `CONFIDENCE_LEVELS: frozenset[str]`; `Rejection` (NamedTuple: `index: int`, `reason: str`); `validate_claims(claims: list[dict], source: str, max_claims: int = 15) -> tuple[list[dict], list[Rejection]]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_claims.py`:

```python
from kb.rules.claims import Rejection, validate_claims

SOURCE = "We agreed to hold pricing at forty-nine. Ana will own the follow-up."


def good_claim(**over):
    base = {
        "statement": "Pricing holds at forty-nine until the Acme deal closes.",
        "type": "decision",
        "confidence": "stated",
        "evidence": "We agreed to hold pricing at forty-nine",
    }
    base.update(over)
    return base


def test_valid_claim_is_kept():
    kept, rejected = validate_claims([good_claim()], SOURCE)
    assert len(kept) == 1
    assert rejected == []


def test_claim_with_fabricated_evidence_is_rejected():
    bad = good_claim(evidence="Ana approved a twenty percent discount")
    kept, rejected = validate_claims([bad], SOURCE)
    assert kept == []
    assert rejected == [Rejection(0, "evidence_not_verbatim")]


def test_claim_missing_evidence_is_rejected():
    bad = good_claim()
    del bad["evidence"]
    kept, rejected = validate_claims([bad], SOURCE)
    assert kept == []
    assert rejected[0].reason == "missing_fields:evidence"


def test_unknown_type_is_rejected():
    kept, rejected = validate_claims([good_claim(type="vibe")], SOURCE)
    assert kept == []
    assert rejected[0].reason == "bad_type"


def test_unknown_confidence_is_rejected():
    kept, rejected = validate_claims([good_claim(confidence="pretty sure")], SOURCE)
    assert kept == []
    assert rejected[0].reason == "bad_confidence"


def test_claims_over_the_cap_are_rejected_not_kept():
    """An extractor emitting forty claims dilutes retrieval until ranking is
    meaningless (spec 2.4 rule 6)."""
    claims = [good_claim() for _ in range(20)]
    kept, rejected = validate_claims(claims, SOURCE, max_claims=15)
    assert len(kept) == 15
    assert len(rejected) == 5
    assert all(r.reason == "over_cap" for r in rejected)


def test_valid_and_invalid_are_separated_not_all_or_nothing():
    claims = [good_claim(), good_claim(type="nonsense"), good_claim()]
    kept, rejected = validate_claims(claims, SOURCE)
    assert len(kept) == 2
    assert [r.index for r in rejected] == [1]


def test_empty_input_yields_empty_output():
    assert validate_claims([], SOURCE) == ([], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_claims.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kb.rules.claims'`

- [ ] **Step 3: Write minimal implementation**

Create `kb/rules/claims.py`:

```python
"""Distillation contract enforcement (spec 2.4).

Rejects, never repairs. A claim that fails any rule is discarded and reported.
"""

from typing import NamedTuple

from kb.rules.evidence import is_verbatim

CLAIM_TYPES = frozenset(
    {"decision", "insight", "commitment", "risk", "open-question"}
)
CONFIDENCE_LEVELS = frozenset({"stated", "implied"})
REQUIRED_FIELDS = frozenset({"statement", "type", "confidence", "evidence"})


class Rejection(NamedTuple):
    index: int
    reason: str


def validate_claims(
    claims: list[dict], source: str, max_claims: int = 15
) -> tuple[list[dict], list[Rejection]]:
    """Split extractor output into what may be stored and what must be dropped.

    Partial acceptance is deliberate: one bad claim should not discard a whole
    recording's distillation.
    """
    kept: list[dict] = []
    rejected: list[Rejection] = []

    for index, claim in enumerate(claims):
        missing = REQUIRED_FIELDS - set(claim)
        if missing:
            rejected.append(
                Rejection(index, "missing_fields:" + ",".join(sorted(missing)))
            )
            continue
        if claim["type"] not in CLAIM_TYPES:
            rejected.append(Rejection(index, "bad_type"))
            continue
        if claim["confidence"] not in CONFIDENCE_LEVELS:
            rejected.append(Rejection(index, "bad_confidence"))
            continue
        if not is_verbatim(claim["evidence"], source):
            rejected.append(Rejection(index, "evidence_not_verbatim"))
            continue
        if len(kept) >= max_claims:
            rejected.append(Rejection(index, "over_cap"))
            continue
        kept.append(claim)

    return kept, rejected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_claims.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
git add kb/rules/claims.py tests/test_claims.py
git commit -m "feat(rules): distillation contract validation"
```

---

### Task 5: Permission class partitioning

**Files:**
- Create: `kb/rules/classes.py`, `tests/test_classes.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Folder` (frozen dataclass: `id: str`, `path: str`, `acl: frozenset[str]`); `acl_fingerprint(acl: frozenset[str]) -> str`; `partition_by_acl(folders: list[Folder]) -> dict[str, list[Folder]]`; `class_acls(folders: list[Folder]) -> dict[str, frozenset[str]]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_classes.py`:

```python
from kb.rules.classes import Folder, acl_fingerprint, class_acls, partition_by_acl

ENG = frozenset({"ana@x.com", "bo@x.com"})
BD = frozenset({"cy@x.com"})
ALL = frozenset({"ana@x.com", "bo@x.com", "cy@x.com"})


def test_same_acl_yields_same_fingerprint_regardless_of_order():
    a = acl_fingerprint(frozenset({"ana@x.com", "bo@x.com"}))
    b = acl_fingerprint(frozenset({"bo@x.com", "ana@x.com"}))
    assert a == b


def test_different_acls_yield_different_fingerprints():
    assert acl_fingerprint(ENG) != acl_fingerprint(BD)


def test_fingerprint_is_prefixed_for_readability():
    assert acl_fingerprint(ENG).startswith("c_")


def test_folders_sharing_an_acl_collapse_into_one_class():
    folders = [
        Folder("f1", "/eng/notes", ENG),
        Folder("f2", "/eng/archive", ENG),
    ]
    partition = partition_by_acl(folders)
    assert len(partition) == 1
    assert len(next(iter(partition.values()))) == 2


def test_distinct_acls_produce_distinct_classes():
    folders = [
        Folder("f1", "/eng", ENG),
        Folder("f2", "/bd", BD),
        Folder("f3", "/all", ALL),
    ]
    assert len(partition_by_acl(folders)) == 3


def test_one_extra_share_creates_its_own_class():
    """Ad-hoc sharing multiplies classes — the cost recorded in D10."""
    folders = [
        Folder("f1", "/eng", ENG),
        Folder("f2", "/eng/odd", ENG | {"guest@x.com"}),
    ]
    assert len(partition_by_acl(folders)) == 2


def test_class_acls_maps_id_to_audience():
    folders = [Folder("f1", "/eng", ENG), Folder("f2", "/bd", BD)]
    mapping = class_acls(folders)
    assert mapping[acl_fingerprint(ENG)] == ENG
    assert mapping[acl_fingerprint(BD)] == BD


def test_empty_input_yields_empty_partition():
    assert partition_by_acl([]) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_classes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kb.rules.classes'`

- [ ] **Step 3: Write minimal implementation**

Create `kb/rules/classes.py`:

```python
"""Permission classes discovered from effective ACLs (spec 1.1, D10).

A class is the set of folders sharing one audience. Classes are discovered by
scanning, never declared — so a stored label cannot disagree with reality.
"""

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Folder:
    id: str
    path: str
    acl: frozenset[str]


def acl_fingerprint(acl: frozenset[str]) -> str:
    """Stable id for an audience. Sorted before hashing so set order is irrelevant."""
    joined = "\n".join(sorted(acl))
    return "c_" + hashlib.sha256(joined.encode("utf-8")).hexdigest()[:8]


def partition_by_acl(folders: list[Folder]) -> dict[str, list[Folder]]:
    """Group folders into classes. One index will be built per returned key."""
    partition: dict[str, list[Folder]] = {}
    for folder in folders:
        partition.setdefault(acl_fingerprint(folder.acl), []).append(folder)
    return partition


def class_acls(folders: list[Folder]) -> dict[str, frozenset[str]]:
    """Class id -> the audience it represents. Needed for edge placement."""
    return {acl_fingerprint(f.acl): f.acl for f in folders}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_classes.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
git add kb/rules/classes.py tests/test_classes.py
git commit -m "feat(rules): permission class partitioning from effective ACLs"
```

---

### Task 6: Edge placement by audience intersection

**Files:**
- Create: `kb/rules/edges.py`, `tests/test_edges.py`

**Interfaces:**
- Consumes: `kb.rules.classes.acl_fingerprint`
- Produces: `edge_class(acl_a: frozenset[str], acl_b: frozenset[str], class_acls: dict[str, frozenset[str]]) -> str | None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_edges.py`:

```python
from kb.rules.classes import acl_fingerprint
from kb.rules.edges import edge_class

ANA = "ana@x.com"
BO = "bo@x.com"
CY = "cy@x.com"

ENG = frozenset({ANA, BO})
BD = frozenset({CY})
ALL = frozenset({ANA, BO, CY})
ANA_ONLY = frozenset({ANA})

CLASSES = {
    acl_fingerprint(ENG): ENG,
    acl_fingerprint(BD): BD,
    acl_fingerprint(ALL): ALL,
    acl_fingerprint(ANA_ONLY): ANA_ONLY,
}


def test_edge_between_identical_audiences_lands_in_that_class():
    assert edge_class(ENG, ENG, CLASSES) == acl_fingerprint(ENG)


def test_edge_between_nested_audiences_lands_in_the_narrower_one():
    # Everyone who can see the ENG record can also see the ALL record.
    assert edge_class(ALL, ENG, CLASSES) == acl_fingerprint(ENG)


def test_incomparable_audiences_with_no_overlap_produce_no_edge():
    """Neither team is stricter; nobody can see both ends, so the edge exists
    nowhere (D10). Materializing it anywhere would leak existence."""
    assert edge_class(ENG, BD, CLASSES) is None


def test_partial_overlap_lands_in_the_overlap_class():
    assert edge_class(ENG, ANA_ONLY, CLASSES) == acl_fingerprint(ANA_ONLY)


def test_overlap_with_no_matching_class_produces_no_edge():
    overlap_only = frozenset({BO})  # intersection is {BO}, no class equals it
    classes = {acl_fingerprint(ENG): ENG, acl_fingerprint(ALL): ALL}
    assert edge_class(frozenset({BO, CY}), ENG, classes) is None


def test_empty_audience_produces_no_edge():
    assert edge_class(frozenset(), ENG, CLASSES) is None


def test_result_is_always_a_subset_of_both_endpoints():
    result = edge_class(ALL, ENG, CLASSES)
    assert CLASSES[result] <= ALL
    assert CLASSES[result] <= ENG


def test_class_with_empty_audience_is_never_selected():
    """An empty audience is a subset of every intersection. If it is not filtered
    out it wins whenever no real class fits, materializing the edge into a class
    that represents nobody."""
    classes = {
        acl_fingerprint(ENG): ENG,
        acl_fingerprint(frozenset()): frozenset(),
    }
    # Intersection is {BO}; no class equals it, so the answer must be None.
    assert edge_class(frozenset({BO, CY}), ENG, classes) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_edges.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kb.rules.edges'`

- [ ] **Step 3: Write minimal implementation**

Create `kb/rules/edges.py`:

```python
"""Edge placement (spec 1.4, D10).

An edge is materialized only where both of its endpoints are visible. Under the
old declared ladder this was "store at the more restricted endpoint", which
assumed a total order; discovered classes form only a partial order, so the rule
is an intersection.
"""


def edge_class(
    acl_a: frozenset[str],
    acl_b: frozenset[str],
    class_acls: dict[str, frozenset[str]],
) -> str | None:
    """Return the class an edge belongs in, or None if it belongs nowhere.

    Chooses the widest class whose audience can see both endpoints, so the edge
    reaches as many entitled readers as possible without reaching anyone else.
    """
    visible_to_both = acl_a & acl_b
    if not visible_to_both:
        return None

    candidates = [
        (class_id, acl)
        for class_id, acl in class_acls.items()
        if acl and acl <= visible_to_both
    ]
    if not candidates:
        return None

    # Widest first; class_id breaks ties so the result is deterministic.
    return max(candidates, key=lambda pair: (len(pair[1]), pair[0]))[0]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_edges.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
git add kb/rules/edges.py tests/test_edges.py
git commit -m "feat(rules): edge placement by audience intersection"
```

---

### Task 7: Identity resolution before filtering

**Files:**
- Create: `kb/rules/identity.py`, `tests/test_identity.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `build_alias_index(entities: list[dict]) -> dict[str, str]`; `resolve(name: str, index: dict[str, str]) -> str | None`; `resolve_all(names: list[str], index: dict[str, str]) -> tuple[list[str], list[str]]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_identity.py`:

```python
from kb.rules.identity import build_alias_index, resolve, resolve_all

ENTITIES = [
    {
        "entity_id": "e_004",
        "name": "Ana Petrova",
        "aliases": ["Ana", "ana@x.com", "apetrova"],
    },
    {"entity_id": "e_011", "name": "Bo Chen", "aliases": ["bo@x.com", "bchen"]},
]
INDEX = build_alias_index(ENTITIES)


def test_resolves_canonical_name():
    assert resolve("Ana Petrova", INDEX) == "e_004"


def test_resolves_short_alias():
    assert resolve("Ana", INDEX) == "e_004"


def test_resolves_github_handle():
    assert resolve("bchen", INDEX) == "e_011"


def test_resolution_is_case_and_whitespace_insensitive():
    assert resolve("  ANA petrova ", INDEX) == "e_004"


def test_unknown_name_resolves_to_none():
    assert resolve("Someone Else", INDEX) is None


def test_resolve_all_separates_known_from_unknown():
    """Unresolved names must surface, never be silently dropped — an unresolved
    alias returning zero rows is indistinguishable from genuine absence
    (spec 3.8)."""
    resolved, unresolved = resolve_all(["Ana", "Ghost", "bchen"], INDEX)
    assert resolved == ["e_004", "e_011"]
    assert unresolved == ["Ghost"]


def test_resolve_all_on_empty_input():
    assert resolve_all([], INDEX) == ([], [])


def test_entity_without_aliases_still_resolves_by_name():
    index = build_alias_index([{"entity_id": "e_099", "name": "Solo Person"}])
    assert resolve("Solo Person", index) == "e_099"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_identity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kb.rules.identity'`

- [ ] **Step 3: Write minimal implementation**

Create `kb/rules/identity.py`:

```python
"""Identity resolution (spec 2.6, 3.8).

Participants are stored as entity ids, so a raw name matched against them returns
nothing — silently. Names must resolve to ids BEFORE filtering, never after.
"""


def _key(name: str) -> str:
    return name.strip().lower()


def build_alias_index(entities: list[dict]) -> dict[str, str]:
    """Flatten the identity map into alias -> entity_id lookups."""
    index: dict[str, str] = {}
    for entity in entities:
        names = [entity["name"], *entity.get("aliases", [])]
        for name in names:
            index[_key(name)] = entity["entity_id"]
    return index


def resolve(name: str, index: dict[str, str]) -> str | None:
    return index.get(_key(name))


def resolve_all(
    names: list[str], index: dict[str, str]
) -> tuple[list[str], list[str]]:
    """Return (resolved_ids, unresolved_names).

    Unresolved names are returned rather than discarded so callers can surface
    them — a dropped participant is a broken join nobody notices.
    """
    resolved: list[str] = []
    unresolved: list[str] = []
    for name in names:
        entity_id = resolve(name, index)
        if entity_id is None:
            unresolved.append(name)
        else:
            resolved.append(entity_id)
    return resolved, unresolved
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_identity.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Run the whole suite and commit**

Run: `python3 -m pytest -v`
Expected: PASS — 57 passed

```bash
git add kb/rules/identity.py tests/test_identity.py
git commit -m "feat(rules): identity resolution before filtering"
```

---

## Verification status

Every code block in this plan was extracted and executed before the plan was
issued: **57 tests pass** against the implementations exactly as written here.

The suite was also mutation-tested on the three leak-critical rules. Two
mutations were caught immediately (a skip log that names the excluded item; an
evidence check that accepts paraphrase). A third — removing the `acl and` guard
in `edge_class` — initially **survived**, because the two guards in that function
mask each other. `test_class_with_empty_audience_is_never_selected` was added to
close that gap and now fails when the guard is removed.

Note for the implementer: the `if not visible_to_both: return None` early exit in
`edge_class` is defence-in-depth, not load-bearing — the candidate filter already
handles empty intersections. Keep it for clarity; do not rely on it alone.

## Phase 1 exit criteria

- `python3 -m pytest` passes with 57 tests.
- No module in `kb/rules/` imports anything beyond the standard library.
- Every rule from spec §1.4, §2.2, §2.4, §2.5, §2.6, §3.8 and D10 has a test that would fail if the rule were removed.

## What comes next

| Phase | Builds | Blocked on |
|---|---|---|
| 2 | Drive/Sheets client: folder walk, `permissions.list`, `appProperties` read/write, Sheet CRUD | Google API credentials |
| 3 | Source adapters: Plaud, Linear, GitHub | Plaud connector authorization |
| 4 | Ingest pipeline and reconcile/rebuild, wiring phases 1–3 together | Phases 2, 3 |
| 5 | Retrieval and the three Claude skills | Phase 4 |

Phase 2's first task must be a spike that verifies `appProperties` and `permissions.list` behave as D9 and D10 assume. If they do not, those decisions need reopening before any more code is written.
