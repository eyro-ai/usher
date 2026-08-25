# Recordings KB — design

Companion to the decision log (`2026-08-12-recordings-kb-decisions.md`). Decisions D1–D8 are
settled; this document works them into a buildable design.

Status: **complete, awaiting review.** Four sections: data model, ingest + distillation, retrieval,
promotion + configuration.

Blocking before implementation: the Plaud and Google Drive connectors are unauthorized, so §1.7's
assumptions about Plaud's tool surface are unverified.

---

## 1. Data model

### 1.1 Storage unit — the permission class

**The folder tree is the schema (D9) and access is Drive's own folder ACL. There is no declared tier
ladder (D10).** The system discovers the distinct effective permission sets present in the tree and
treats each as a **class**: the set of folders sharing one audience.

Raw documents may be shared at any granularity, because Drive enforces each one individually.
Derived artifacts cannot be. An index is a single file with a single ACL, so every row in it is
visible to everyone who can open it — which means **a derived artifact can only be shared with the
intersection of its inputs' audiences.** That is the whole reason classes exist: one index per
distinct audience, not per folder and not per document.

```
<class root>/           <- one per distinct effective ACL, discovered by scan
  records/              <- raw Docs. People reorganize freely below this point.
    <any subfolder tree the team likes>
  index                 <- derived Sheet: Records | Claims | Links
  .cache                <- derived: content-hash-keyed distillation cache
```

Classes are **discovered, never configured**. Two teams with separately-shared folders become two
classes without anyone naming them; a folder shared with one extra person becomes its own class.
Configuration supplies only the roots to scan.

**Subfolder structure below `records/` carries no meaning to the system.** Only the effective ACL
does. People organize for themselves; the system reads only the boundary.

The **default landing zone** is the most restrictive class available — an owner-only folder. This
needs no ladder to define: "shared with nobody" is the bottom of any permission lattice.

`Entities` is the one exception: a single Sheet in the most widely-shared class, referenced by ID
from every other. Duplicating it per class would guarantee drift.

### 1.2 Records tab

One row per source event. The atomic unit: per recording, per issue, per PR — never per commit.

| Column | Example | Notes |
|---|---|---|
| `record_id` | `plaud:a1b2c3` | **Primary key.** `{source}:{source_id}`. Dedup on this, never on title. |
| `source` | `plaud` | `plaud` · `linear` · `github` |
| `source_id` | `a1b2c3` | Native stable id. PR uses GraphQL `node_id`, not number. |
| `source_url` | `https://…` | Back-link to the truth. |
| `title` | `Partner call — Acme` | Not unique. Never used for identity. |
| `occurred_at` | `2026-07-14T09:30Z` | When the event *happened*, not when ingested. |
| `participants` | `e_004;e_011` | `entity_id` list. |
| `topics` | `pricing;partnerships` | Flat tags. Promote to a tab only if they grow unwieldy. |
| `class` | `c_7f21` | **Derived from the folder's effective ACL on rebuild** (D9, D10). Never declared, so a stored label cannot disagree with reality — it is read from reality. |
| `raw_doc_id` | `1AbC…` | Drive file id of the raw Doc. Empty when link-only. |
| `mutable` | `FALSE` | See 1.5. `TRUE` ⇒ never trust anything cached here; refetch. |
| `content_hash` | `sha256:…` | Detects upstream change on re-sync. |
| `ingested_at` | `2026-07-15T…` | Watermark and staleness. |
| `extractor_version` | `v3` | Which rows need re-distilling when prompts improve. |

Deliberately **absent: any status field.** Caching Linear state is what makes a KB start lying.

### 1.3 Claims tab

The distilled layer — what retrieval actually hits, since raw transcripts are too noisy to rank well.

| Column | Notes |
|---|---|
| `claim_id` | `{record_id}#{n}` |
| `record_id` | FK → Records |
| `statement` | One sentence, self-contained. Readable without its source. |
| `type` | `decision` · `insight` · `commitment` · `risk` · `open-question` |
| `speaker_entity_id` | FK → Entities. Empty when attribution is unreliable. |
| `occurred_at` | Denormalized from the record so date filtering needs no join. |
| `confidence` | `stated` (explicit in source) · `implied` (inferred by the extractor) |
| `evidence` | Verbatim quote span. Never paraphrased. |
| `evidence_anchor` | Timestamp or char offset into the raw Doc, for deep-linking. |
| `topics` | |
| `extractor_version` | |

`evidence` being verbatim is what lets a reader check a claim instead of trusting it. Combined with
never overwriting the raw Doc, it also means re-distillation stays possible forever.

### 1.4 Links tab

The cross-source edge table. Cheap here — the column that Notion's unlabeled relations could not
carry is just a column (D8).

| Column | Notes |
|---|---|
| `link_id` | |
| `from_record_id` / `to_record_id` | |
| `basis` | `explicit-id` · `time-proximity` · `llm-inferred` — **never rendered as equivalent** |
| `confidence` | `high` · `medium` · `low` |
| `note` | e.g. `"ENG-142 found in PR title"` |
| `detected_at` | |

**Placement rule: an edge is materialized only in the class that can see *both* endpoints — the
intersection of their audiences. If that intersection is empty, the edge exists nowhere.**

Under the declared ladder this was "store it at the more restricted endpoint", which assumed
restrictiveness was a total order. With discovered classes (D10) it is a *partial* order — Team A
and Team B are incomparable, neither stricter than the other. The intersection rule is both simpler
and provably non-leaking: an edge is only ever visible to someone who can already see what it
connects, so "existence is information" (D5) cannot leak through the edge table.

Join precision, descending: `explicit-id` (a `ENG-142` in a branch, PR title, or commit message) >
identity map > `time-proximity` > `llm-inferred`. Only the first is trustworthy unattended.

### 1.5 What gets copied vs. linked

Direct application of "copy the immutable, link the mutable":

| Content | Immutable? | Treatment |
|---|---|---|
| Plaud recording + transcript | Yes | Full copy into a Doc. This is the corpus. |
| GitHub PR, merged | Yes | Snapshot Doc: title, body, review discussion as at merge. |
| GitHub PR, open | No | Row + link only. `mutable = TRUE`. |
| Linear issue / project | No | Row + link only. `mutable = TRUE`. Status always refetched. |

### 1.6 Integrity and drift

Because the index is derived (D9), most classic integrity errors cannot occur — a rebuild
regenerates it from what is actually on disk, and vanished files simply stop appearing. What remains
are the things the folder tree cannot answer for itself:

- **Effective-permission drift — the important one.** Drive folder ACLs are inherited, but
  permissions granted *directly on a file* survive a move. A document dragged from Open into
  Personal can stay readable by whoever held a direct share. Reconcile reads each file's effective
  permissions and flags any exceeding its folder's class. Folder inheritance is not proof of access.
- **Class re-partition (D10).** Someone editing a folder's sharing changes which class it belongs to
  *without touching a single file*. The tree looks identical, so nothing in a file scan reveals it.
  Reconcile must compare effective ACLs against the previous partition and rebuild affected indexes.
- **Exclusion matches in a shared class.** A document hand-moved somewhere more widely shared that
  matches a never-ingest pattern is the loudest signal reconcile can raise — a human bypassed the
  gate (§4.1).
- **Unidentifiable files** — a Doc under `records/` with no identity stamp (§1.7), or a stamp
  pointing at a source that no longer exists. Reported as unrecognised, never guessed at.
- **Edges violating §1.4 intersection placement** after a move or a share change.

### 1.7 File identity survives renames and moves

People reorganize by hand, so identity cannot live in a path or a filename. It is stamped into Drive
`appProperties` — hidden per-file metadata that survives rename, move, and copy, and that the normal
UI cannot disturb:

`record_id` · `source` · `source_id` · `content_hash` · `extractor_version`

Rebuild reads these stamps and infers nothing from filenames.

### 1.8 Assumptions pending Plaud authorization

The connector is unauthorized, so its tool surface is unknown. This section assumes Plaud exposes a
stable id, title, timestamp, and **full transcript text**. Consequences if wrong:

- **Summaries only, no transcript** — `evidence` becomes unquotable and `evidence_anchor`
  meaningless; claims stop being checkable. Material enough to reopen the data model.
- **No speaker segmentation** — `speaker_entity_id` is mostly empty, weakening the identity join.
- **No folders or tags** — nothing to derive a landing folder from, so every recording is filed by hand and
  the promotion flow becomes the primary interaction rather than an occasional one.

These are assumptions, not findings. Verify before building.

---

## 2. Ingest and distillation

### 2.1 The loop

Per enabled source, per run:

```
read watermark(source)          last successfully committed occurred_at
fetch changed since watermark   incremental, never a full rescan
for each item:
    apply never-ingest rules    -> skip, without recording what was skipped (2.2)
    resolve landing folder      -> default deny (2.3)
    commit record               -> atomic-ish sequence (2.7)
run validate                    -> §1.6
advance watermark               only past fully committed items
```

A full rescan is never the normal path. It exists as an explicit `--rebuild` for when
`extractor_version` changes.

### 2.2 The never-ingest gate comes first

Config carries a never-ingest list — patterns over title, folder/tag, and participants (e.g. 1:1s,
HR, comp, legal, health). It is evaluated **before content is fetched** wherever the source allows
it, so excluded material is never pulled into the agent's context at all.

**The skip log must not describe what was skipped.** Recording `skipped: "1:1 with J — comp review"`
recreates, in a file with different permissions, precisely the leak the rule exists to prevent. Log
the rule that fired and a count: `skipped 3 items (rule: title~/1:1/)`. This is a real leak vector
and it is easy to get wrong, because a helpful log is the obvious thing to write.

### 2.3 Landing-folder resolution — default deny

Ingest chooses a *folder*; the class follows from that folder's ACL (D10).

| Source | Signal | Resolution |
|---|---|---|
| Plaud | Folder or tag, mapped in config | No mapping, or no folder concept ⇒ **owner-only folder** |
| Linear | Team visibility | Private team ⇒ that team's mapped folder · public ⇒ the workspace-shared folder |
| GitHub | Repo visibility | Private repo ⇒ mapped folder · public ⇒ workspace-shared folder |

Anything unresolved lands in the **owner-only** folder. Never the reverse. A recording sitting
unshared costs someone a question; the opposite costs an incident.

### 2.4 Distillation contract

Input: raw text plus record metadata. Output: a strict JSON array, 3–15 items, each:

```json
{
  "statement": "one self-contained sentence",
  "type": "decision|insight|commitment|risk|open-question",
  "speaker": "name as it appears, or null",
  "confidence": "stated|implied",
  "evidence": "verbatim span copied from the source",
  "evidence_anchor": "timestamp or char offset",
  "topics": ["..."]
}
```

Binding rules on the extractor:

1. **`evidence` must appear verbatim in the source.** Enforced programmatically by substring check;
   any claim failing it is discarded, not repaired. This is the cheapest, hardest anti-fabrication
   guard available — string containment either holds or it doesn't.
2. No claim without evidence. Ever.
3. `statement` must be readable standalone, without its source.
4. `confidence: stated` only when the source says it outright; anything reconstructed is `implied`.
5. `speaker` only on unambiguous attribution — ASR speaker labels are unreliable, and a wrong
   attribution is worse than none.
6. The 3–15 cap is deliberate: an extractor that emits forty claims per recording dilutes retrieval
   until ranking is meaningless.

### 2.5 Dedup and re-extraction

Keyed on `record_id` (§1.2), never title.

| Situation | Action |
|---|---|
| `record_id` absent | Create. |
| Present, `content_hash` unchanged, `extractor_version` current | **Skip entirely** — no refetch, no re-extraction, no cost. |
| Present, `content_hash` changed | Refresh row, re-extract. |
| Present, `extractor_version` stale | Re-extract only. |

Re-extraction **replaces all claims for that record wholesale** — delete then rewrite. Merging
distilled claims across extractor versions produces near-duplicates that never converge and slowly
poison ranking. Since `claim_id` is `{record_id}#{n}`, wholesale rewrite is clean by construction.

### 2.6 Identity resolution

Participant strings are matched against `Entities` aliases. No match ⇒ create an entity flagged
`needs_review`, never silently drop the participant — a dropped participant is a broken join that
nobody notices. Two entities are never auto-merged; that is a human call.

### 2.7 Commit order

Order matters for safety, not just tidiness:

1. Never-ingest check
2. Resolve the landing folder
3. **Write the raw Doc directly into that folder** — never write somewhere
   convenient and move it afterwards. A write-then-move leaves the content sitting at the wrong ACL
   for a window, which is an access incident even if it lasts seconds and nobody looks.
4. Write the Records row
5. Extract → validate evidence containment → write Claims rows
6. Detect links → write Links rows, honouring the §1.4 placement rule
7. Run validate (§1.6)
8. Advance the watermark

The watermark advances only after a record fully commits. A crash mid-record leaves it unmoved and
the next run retries; policy-skips advance it, error-skips do not.

---

### 2.8 Rebuild is the normal path, not the exception (D9)

Indexes are caches. Deleting one and regenerating it is routine, not recovery.

A rebuild, per class:

1. Walk the class folder; read each file's identity stamp (§1.7).
2. Refetch link-only records (Linear, GitHub) from source — they have no file to scan.
3. Rewrite `Records` from what is actually present. Files that vanished stop appearing; files that
   arrived appear. Moves need no special handling because nothing tracked where they used to be.
4. Look up each record's claims in the class cache by `content_hash`; re-distill only on a miss.
5. Recompute `Links`, honouring §1.4 placement.
6. Run the drift checks (§1.6).

**The claim cache is keyed by content hash and scoped per class.** Content addressing makes it immune
to reorganisation *within* a class — a document that moved folders still hits its cached claims, so a
rebuild costs almost nothing. Per-class scoping means a document moved *between* classes misses and
re-distills, which is the correct security behaviour: distilled claims must never pre-exist in a class
before the document itself arrives.

Watermarks (§2.1) survive only as an optimization for fetching new source material. They stop being
load-bearing for correctness, because a full rebuild is always available and cheap in everything
except distillation.

## 3. Retrieval

### 3.1 Scope is discovered, not configured

The retrieval skill holds **no table of who may read what**. It attempts to open each configured
class; Drive returns what the asking human can see and denies the rest. Access is a boundary,
not a filter.

This matters because a configured table would drift out of sync with actual Drive membership, and
because a filter applied by an agent is a filter an agent can be talked out of. Letting the ACL
answer means the failure mode is "no results" rather than "results that shouldn't have appeared".

Consequence: **the same question yields different answers for different people.** That is correct.
But it makes the scope note in §3.5 mandatory — an unscoped partial answer reads as a complete one,
and the reader has no way to tell.

### 3.2 Three-stage funnel

| Stage | Mechanism | When |
|---|---|---|
| 1. Metadata filter | Sheet columns: `occurred_at`, `participants`, `source`, `topics`, `type` | Always first. Most questions are scoped ("the partner calls in July") and this is exact and free. |
| 2. Lexical | `Claims.statement` + `Claims.evidence`, unioned with Drive `fullText contains` over raw Docs | Names, ticket IDs, error strings, product names — exactly what semantic search is worst at. |
| 3. Semantic | Agent reads and reranks the candidate set from 1–2 | Only for conceptual recall, or when 1–2 return too little. |

**No embedding store.** At this corpus size, Drive's full-text index plus distilled claim statements
plus agent reranking beats a vector index that has to be kept in sync with every re-extraction. The
sync burden is real and arrives immediately; the recall benefit arrives much later, if ever. Revisit
only when measured recall actually fails — not on principle.

### 3.3 Claims first, raw second

Retrieval hits `Claims`. Raw Docs are the verification layer, fetched by `raw_doc_id` when a claim
needs surrounding context or a reader wants to check the quote.

Searching transcripts directly is the classic mistake: they are long, full of filler and ASR
errors, and consequently match almost everything, which destroys ranking.

### 3.4 Mutable records are refetched, never read from the sheet

Any candidate with `mutable = TRUE` (§1.5) — Linear issues, open PRs — is refetched live before it
enters an answer. The row supplies identity and a link, nothing more.

If the source is unreachable, say so. An answer that quietly falls back to a cached row is how a KB
starts lying, and it is unfalsifiable from the reader's side.

### 3.5 Citation and answer contract

Every answer carries:

- **The claims it rests on**, each with `source_url`, `occurred_at`, speaker where known, and
  `confidence`
- **Provenance for anything that arrived through a link** — an `llm-inferred` edge is marked as
  inferred, never presented as established
- **A scope note**: which classes were searched and over what date range
- **"As of" stamps** on anything refetched live
- **An explicit "not found"** where nothing was found

Three things must stay visually distinct and never blend into unattributed prose: what was *said*
(`stated`), what was *inferred* (`implied` or an inferred link), and what is *live* (refetched).

### 3.6 Read-time leak rules

- **Never report suppressed results.** "3 further results exist in classes you cannot access" is an
  existence leak, and it is the natural, helpful-seeming thing to build. Out-of-scope material is
  absent, not redacted.
- **Never persist a cross-class synthesis into a more widely shared class.** Someone who can open two classes may
  receive a blended answer in conversation — they hold both, so nothing leaks. Writing that
  synthesis into the broader class would move the narrower one's content across the boundary. This is D5's
  derived-artifact rule applied at read time, and it is the likeliest place to breach it by
  accident, because summarising an answer into the KB feels like a feature.

### 3.7 Failure modes

- **Nothing found** — say so plainly and suggest widening the date range or terms. Never fill the
  gap with plausible-sounding recall.
- **Conflicting claims** — surface both with their dates rather than silently preferring the more
  recent. Two recordings disagreeing is a finding, not noise to resolve.
- **Single-source answers** — flag when an answer rests on one claim from one recording. Confidence
  should track corroboration.

### 3.8 Query planning — question shapes

Questions are not uniform, and a single retrieval path serves them badly. Classify first, then plan:

| Shape | Example | Plan |
|---|---|---|
| Point lookup | "What did we decide about pricing?" | Filter `topics`, `type=decision` → lexical → return claims |
| Person-scoped | "What has Ana committed to?" | Resolve entity → filter `participants`/`speaker`, `type=commitment` |
| Time-window digest | "Summarize the partner calls in July" | Filter date range + topic → group by record → §3.10 |
| Entity history | "How did our thinking on X change?" | Filter topic, sort `occurred_at` ascending, surface deltas |
| Traceability | "Did anything come of the Acme call?" | Start at record → traverse `Links` → refetch mutable endpoints |
| Existence | "Have we ever discussed Y?" | Lexical over claims + raw full-text → explicit not-found |

**Resolve names to `entity_id` before filtering, never after.** `participants` stores IDs, so
matching the string "Ana" against it returns nothing — silently. A retrieval that quietly returns
zero because of an unresolved alias is indistinguishable from a genuine absence, which makes this
the most deceptive bug available in this design.

### 3.9 Multi-hop traversal

Path: claim → its record → `Links` → linked records → their claims. **Depth 2 by default.**

Traversal is governed by `basis`:

- `explicit-id` — traverse freely. A ticket ID in a PR title is a fact.
- `time-proximity` / `llm-inferred` — traverse **only** when the question is explicitly exploratory
  ("what might be related to…"), and mark the entire downstream branch as inferred.

Silently traversing an inferred edge and presenting the far side as related is how a guess is
laundered into a finding. Each hop compounds the error of the last.

### 3.10 Aggregation and temporal queries

**Digests fan out, then synthesize.** Retrieve the N records, summarize each independently, then
synthesize across the summaries. Concatenating transcripts into one context both overflows it and
biases the result toward whichever recording happened to be longest.

**Temporal questions sort ascending and look for supersession.** A later `decision` on a topic
supersedes an earlier one but never deletes it — both remain, ordered, with dates. The change is
usually the answer.

**Never present counts from the KB as measurements.** "Three people raised churn" is false; the
truth is "churn appears in three recordings that were captured, ingested, and distilled." The
corpus is a convenience sample shaped by who records what and which classes the asker can open.
Quantitative claims over it are unsound, and they are seductive precisely because the data looks
tabular.

### 3.11 Ranking and context budget

Descending precedence: exact metadata match > lexical hit in `statement` > lexical hit in
`evidence` > lexical hit in raw Doc > semantic-only match. Tie-break on recency, then `stated` over
`implied`. Corroboration across independent records boosts.

Cap the answer context at roughly the top 20 claims. Past that, reranking quality degrades rather
than improves, and the marginal claim adds noise.

### 3.12 Cost discipline

Every Sheet and Drive read is an API call. Read each reachable class's index once per session and filter
in memory; never re-read per query. Cache within a session only — never across, since `mutable`
rows and class membership both change underneath.

---

## 4. Promotion and configuration

### 4.1 Promotion is a human file move (D9)

Tier changes happen by dragging a document between class folders in Drive. There is no tool-mediated
move, and the tooling cannot require one.

**This makes the safety checks detective rather than preventive — a real weakening, not a cosmetic
one.** Participant-exposure and never-ingest re-evaluation can no longer block a move. They run at
the next reconcile and report. The interval between a careless drag and that reconcile is genuine
exposure, and no amount of tooling closes it while hand-moves remain the interface.

Two mitigations, neither of which closes that window:

- Reconcile runs often, and treats an exclusion match in a widely shared class as its highest-priority alert.
- A `promote` helper runs the checks *first*, then performs the move, for people who want them. It is
  a convenience, not a gate.

### 4.2 What reconcile checks after a move or share change

1. **Never-ingest rules, re-evaluated.** Material that was fine in Personal may match an exclusion
   once shared — the rules govern sharing, and sharing is what just happened.
2. **Participant exposure.** A promotion exposes everyone who spoke. Flagged for a human; never
   auto-resolved.
3. **Effective permissions** (§1.6) — direct shares survive moves, so the folder does not prove the ACL.
4. **Edge placement** (§1.4) — edges are re-materialized at the intersection of their endpoints' audiences.

### 4.3 Demotion is containment, not erasure

Moving a document into a more restrictive folder does not undo exposure. Whoever read it, read it;
Drive keeps revision history; copies others made are untouched. Critically, **direct shares granted
while it sat in the open persist through the move** and must be revoked explicitly — which is
exactly why §1.6 checks effective permissions instead of trusting the folder.

Log demotions as potential incidents, not as undo.

### 4.4 Claims follow their document for free

Because claims are regenerated at the document's current location (§2.8), a hand-move needs no
bookkeeping: the old class's rebuild stops emitting them, the new class's rebuild produces them.
Nothing is migrated and nothing is orphaned in a sheet the person never knew existed.

This is the main dividend of making indexes disposable — the failure mode where a moved file leaves
stale derived rows behind simply cannot arise.

### 4.5 `kb.config.yaml`

Everything deployment-specific, per D6. The skills contain no organisation's names, IDs, or rules.

```yaml
version: 1

sources:
  plaud:
    enabled: true
    folder_map:             # empty or absent ⇒ everything lands in default_landing
      "Team syncs": open
      "Partner calls": group:bd
  linear:
    enabled: true
    teams: [ENG, BD]        # private team ⇒ its mapped folder
  github:
    enabled: true
    org: acme
    repos: ["*"]            # public ⇒ shared folder; private ⇒ mapped folder

roots:                      # folders to scan. Permission classes are DISCOVERED, not declared (D10)
  - folder_id: "..."        # e.g. the team's shared parent
  - folder_id: "..."        # e.g. a private landing folder
default_landing: "..."      # owner-only folder; every unresolved ingest goes here

reconcile:
  on_start: true            # rebuild before answering, so hand-moves are never stale
  acl_scan: every_run       # share changes leave no file-move trace (D10)
  alert_on: [exclusion_match_in_shared_class, effective_permission_drift,
             unidentified_file, class_repartition]
entities_sheet_id: "..."

never_ingest:               # evaluated before content is fetched (§2.2)
  title_patterns:       ["1:1", "performance", "comp", "offer"]
  folder_patterns:      ["Personal", "HR"]
  participant_patterns: []

extraction:
  version: v1
  min_claims: 3
  max_claims: 15
  types: [decision, insight, commitment, risk, open-question]

glossary:                   # ASR corrections, applied at ingest
  "plod": "Plaud"
  "linnear": "Linear"

retrieval:
  max_claims_in_context: 20
  max_hop_depth: 2
  traverse_inferred: false
```

No secrets live here — OAuth is held by the connectors, and `gh` holds its own token.

### 4.6 Bootstrap

First run, given an otherwise empty config:

1. Scan the roots, compute effective ACLs, and derive the class partition. Create each `index`
   Sheet with its tab headers inside its class folder.
2. Create the `Entities` sheet in the most widely shared class.
3. Seed entities from Linear members and GitHub org members, matching on email where available.
   Every seeded entity is flagged `needs_review` — an auto-matched identity is a hypothesis.
4. Report what was created and what needs a human: unmapped folders, unresolved identities, and any
   source with no folder mapping (all of which default to the owner-only landing folder).
