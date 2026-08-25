# Recordings KB — decision log

Running record of design decisions. Started 2026-08-07. Last updated 2026-08-12. Status: **brainstorming in progress** —
this is not yet a finished spec.

## What this is

A knowledge base over three sources: **Plaud** (voice recordings), **Linear** (issues, projects,
initiatives), and **GitHub** (pull requests). Plaud is the corpus; Linear and GitHub supply
context.

Designed to be **generic and configuration-driven** — usable by any individual or organisation
running those three tools, not wired to one company's structure (D6).

## Decisions

### D1 — Standalone KB
*Decided 2026-08-07.*

Its own schema and its own skills, rather than a mode bolted onto an existing knowledge-base
pipeline.

### D2 — Purpose: searchable memory of recordings
*Decided 2026-08-07.*

Optimized for recall — "what do we know about X", "what was said about pricing", "summarize the
partner calls in July" — not for talk-to-work traceability, auto-ticket-creation, or status
reporting.

Consequence: design effort goes into ingest quality, distillation, and retrieval, rather than
write-back into Linear or GitHub.

### D3 — Sources: Plaud + Linear + GitHub
*Decided 2026-08-07.*

Each source is reached through an adapter, so a deployment can enable any subset. Plaud is the
only required one.

### D4 — Storage: Notion — **SUPERSEDED by D8 (2026-08-12)**
*Decided 2026-08-07, reverted 2026-08-12. Retained for the record.*

Rationale: real server-side ACLs (decisive given D5), human-browsable, and a sane API surface.

Accepted tradeoffs:
- Weaker retrieval than a local full-text index; every read is an API call.
- The Notion connector can create/update/move pages but **cannot delete or archive** them. A
  mis-filed page can be moved, never erased — which raises the cost of a mis-tiered write and is
  the main reason D5 defaults to deny.

All Notion identifiers (parent page, database IDs) come from configuration. None are hardcoded.

### D5 — Access control: tier partitioning with default-deny
*Proposed 2026-08-07, confirmed 2026-08-12.*

Governing rule: **any artifact inherits the maximum sensitivity of everything it was derived
from** — summaries, rollups, embeddings, the entity graph, and node titles alike. Existence is
information.

Why not query-time ACL filtering: Plaud has no source ACL to inherit (a personal recorder has no
org permission model), so every recording needs an assigned label regardless. Linear and GitHub
do have ACLs and those are mirrored where available.

Tiers are **configurable**; the default ladder is:

| Tier | Contains |
|---|---|
| Personal | Raw recordings, unpromoted. Default landing zone. |
| Group | Scoped to a named group — a team, a function, a project. Zero or more of these. |
| Open | Visible to everyone in the deployment. |
| *(excluded)* | A configurable never-ingest list — e.g. 1:1s, HR, comp, legal, health. Not a tier: this content never enters the KB at all. |

Mechanics: default deny on ingest (unlabeled -> most restrictive); derive rollups per tier, never
across; promotion between tiers is a deliberate, logged human act; cross-tier links point rather
than embed.

Agent identity: the agent always acts with the asking human's own credentials, never a service
token holding the union of everyone's access.

A single-user deployment collapses this to one tier and skips the promotion flow entirely, without
schema changes — the sensitivity field still exists, always "personal".

Confirmed 2026-08-12. Load-bearing for D8.

### D6 — Generic, not organisation-specific
*Decided 2026-08-07.*

No company's teams, folder names, repo lists, privacy allowlists, or Notion IDs are baked into the
design. Everything deployment-specific lives in a config file: source credentials, Notion target
IDs, tier definitions, group names, the never-ingest list, the identity map, and the ASR glossary.

Consequence: audience (solo vs. team) stops being a design-time decision and becomes
configuration. The schema is built for the tiered case; a solo deployment simply has one tier.

### D7 — Packaging: Claude skills + a config file
*Decided 2026-08-07.*

No compiled artifact and no service to run. Three skills plus one config file:

| Skill | Job |
|---|---|
| recordings-kb-add | Pull from enabled sources, distill, dedup, write to Notion. |
| recordings-kb-search | Retrieve and answer, with citations back to source. |
| recordings-kb-promote | Move a node between tiers — the deliberate human act from D5. |

`kb.config.yaml` holds everything deployment-specific (D6): source credentials and scopes, Notion
target IDs, tier and group definitions, the never-ingest list, the identity map, and the ASR
glossary.

Accepted tradeoff: weakest at bulk and scheduled sync, since every run is agent-driven rather than
cron-driven. Mitigation if it bites: a scheduled routine invoking the add skill on a cadence.

### D8 — Storage: Google Drive, company workspace
*Decided 2026-08-12. Supersedes D4.*

Files in a company Google Workspace rather than Notion.

What this buys over Notion:
- **Deletion actually works.** Drive can trash and permanently delete. Notion could not, which was
  the single biggest risk under default-deny (D5) — a mis-tiered write was permanent. It is now
  recoverable.
- **Shared Drives map onto tiers directly.** Membership of a Shared Drive *is* the ACL. Promotion
  (D5) becomes moving a file between drives: a real, auditable, reversible act rather than a
  property edit.
- **Edge provenance becomes trivial.** A spreadsheet column holds `basis` natively, so the
  three-relation workaround forced by Notion's unlabeled relations is no longer needed.
- **Lexical search comes free.** Drive full-text indexes Docs, so raw transcripts are searchable
  without building an index.

What it costs:
- **No database primitives.** No typed properties, no relations, no filtered views. Records /
  Claims / Entities must be re-expressed as Sheets plus Docs.
- **The file is the permission unit.** This is structural: a single spreadsheet cannot hold rows of
  differing sensitivity, because anyone who can open the file reads every row. The index therefore
  **shards per tier** — one index Sheet per tier, never one global sheet. This turns D5's "derive
  per tier, never across" from a discipline into an enforced property of the layout.
- **Referential integrity is ours to keep.** IDs are by convention; nothing validates them.
- Cross-tier questions require reading several sheets and unioning — done by the agent, and only
  across tiers the asking human can already open, which is the correct behaviour regardless.

Resulting layout, one unit per tier:

```
Shared Drive: "Recordings KB — Open"
  /records/          one Google Doc per recording (raw transcript, verbatim)
  index              one Sheet, tabs: Records | Claims | Links
Shared Drive: "Recordings KB — <group>"
  ...same structure, membership-scoped
My Drive:    "Recordings KB — Personal"
  ...same structure, unshared. Default landing zone.
```

Entities (the identity map) is a single Sheet at the most open tier, referenced by ID from every
other tier — duplicating it per tier would guarantee drift. Open question: whether membership
itself is sensitive in some deployments.

Note: "company workspace" implies a shared deployment, so the tiers of D5 are live rather than
collapsed. This does not change D6 — the design stays generic and config-driven; group names and
drive IDs are configuration.

### D9 — Folders are the organization; indexes are derived and disposable
*Decided 2026-08-12. Amends D5 and D8.*

Three rules, and everything else follows from them:

1. **Data lives in folders.** The folder tree is the organizing structure. Below each tier folder,
   people arrange documents however they like; subfolder structure carries no meaning to the system.
2. **People move original documents by hand, freely.** Drive's own UI is the interface. The tooling
   never requires a tool-mediated move and must stay correct when one never happens.
3. **All indexes rebuild automatically.** Indexes are caches, not records. Any of them can be
   deleted and regenerated from what is actually on disk.

Access is **Google Drive folder ACLs**: a tier is a folder whose sharing settings define who reads
it, and the tier's index lives inside that folder so it inherits the same permissions.

What this improves:
- The folder becomes the single authority on tier. No label can disagree with reality, because the
  label is derived from the location rather than compared against it.
- Hand-moves need no bookkeeping. Claims are regenerated at the document's current location, so the
  old tier stops emitting them and the new tier starts — nothing to migrate, nothing orphaned.
- Rebuild-from-scratch replaces a whole class of integrity bugs; deletions and moves are handled by
  simply not finding the file.

What it costs, stated plainly:
- **Promotion checks become detective, not preventive.** Participant exposure and never-ingest
  re-evaluation can no longer gate a move — they run at the next reconcile and report. The interval
  between a careless drag and that reconcile is genuine exposure. A `promote` helper offers the
  checks up front, but it is a convenience, not a gate.
- **Drive's permission model hides a trap.** Folder ACLs are inherited, but permissions granted
  *directly on a file* survive a move. A document dragged from Open into Personal can stay readable
  by anyone holding a direct share. Reconcile must therefore verify each file's *effective*
  permissions rather than trusting folder inheritance.
- Distillation cost returns on any move between tiers (see the cache rule below).

Two mechanisms make it work:
- **Identity lives in Drive `appProperties`** — hidden per-file metadata that survives rename, move
  and copy. Filenames and paths are never used to identify a document, because humans change both.
- **The distillation cache is content-hash-keyed and scoped per tier.** Content addressing makes it
  immune to reorganisation within a tier; per-tier scoping means a document moved *between* tiers
  re-distills, which is correct — claims must never pre-exist in a tier before the document arrives.

### D10 — Permission classes discovered from ACLs, replacing the declared tier ladder
*Decided 2026-08-12. Supersedes the fixed ladder in D5; refines D9.*

There is no configured personal/group/open ladder. The system walks the configured roots, computes
each folder's **effective** Drive ACL, and groups folders sharing one audience into a **class**.

The reason the grouping cannot simply be dropped:

> A derived artifact can only be shared with the **intersection** of its inputs' audiences.

Raw documents are fine at any granularity — Drive enforces each individually, so sharing a single
folder with one extra person is free. An index is not: it is one file with one ACL, and every row in
it is visible to anyone who can open it. So there must be one index per distinct audience. That is
what a tier always was; the error was declaring it rather than discovering it.

What it buys:
- Arbitrary fine-grained sharing works. Two teams with separately-shared folders become two classes
  with nobody naming them.
- Configuration loses the entire `tiers:` block — only roots and a default landing folder remain,
  which strengthens D6.
- No label to drift: class membership is computed from the ACL every rebuild.

What it costs:
- **Class explosion.** Index count and rebuild cost scale with *distinct ACLs*, not documents.
  Ad-hoc per-file sharing creates a class per unique share, and because direct shares survive moves
  (D9), a single file can become a class of one. Worth a policy note: share folders, not files.
- **Restrictiveness becomes a partial order.** Team A and Team B are incomparable. The §1.4 edge
  rule therefore changes from "store at the more restricted endpoint" to "materialize only in the
  intersection of both endpoints' audiences; if empty, nowhere." Simpler and provably non-leaking.
- **Share changes re-partition the derived layer with no file move to detect.** Previously only
  moves mattered and moves are visible in the tree; now editing a folder's sharing invalidates
  indexes while the tree looks identical. Reconcile must scan effective ACLs every run, not just
  walk files.

Unchanged: the owner-only default landing zone (no ladder needed — "shared with nobody" is the
bottom of any lattice), the never-ingest exclusion list (orthogonal to access), and the
content-hash-keyed claim cache, now scoped per class.

## Open questions

- Packaging — Claude skills, a CLI, or both? What does a user actually install and run?
- Corpus size and sync cadence; whether sync is manual, scheduled, or both.
- Plaud's actual tool surface — blocked on authorization.
- Retrieval interface — a skill, Notion's own search, or both.
- Identity map: hand-maintained, or bootstrapped from Linear/GitHub member lists?

## Design principles carried forward

- Copy the immutable (recordings, merged PRs), link the mutable (Linear status, open PRs).
- One atomic node per event: per recording, per issue, per PR — never per commit.
- Two layers: raw record preserved verbatim + distilled claims indexed on top. Never overwrite raw
  with extraction, so re-distillation stays possible when prompts improve.
- Label every cross-source edge with how it was derived: explicit-id / time-proximity /
  llm-inferred. Never render an inferred edge as fact.
- Dedup on stable source keys (plaud_id, Linear id, PR node_id), never on title — recording titles
  are not unique.
- Retrieval order: metadata filter -> lexical -> semantic.
- Cross-source join keys, in descending precision: explicit IDs (ENG-123 in branch/PR/commit) >
  identity map (speaker <-> Linear user <-> GitHub handle) > time proximity > semantic inference.

## Local environment (not part of the design)

Status of this machine as of 2026-08-07, for implementation only:

| Source | Access |
|---|---|
| Plaud | **Not yet authorized** — needs /mcp -> "claude.ai Plaud Web MCP" (mcp.plaud.ai). Tool surface unknown until then. |
| Linear | MCP connector available. |
| GitHub | gh CLI authenticated (scopes: repo, read:org, workflow). The GitHub MCP plugin exposed no tools; gh api is the path. |
| Google Drive | **Not yet authorized** — needs /mcp -> "claude.ai Google Drive". Write capability unconfirmed until then. |
| Notion | Connector available, but no longer part of the design (D8). |
