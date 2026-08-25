# Recordings KB — design

Companion to the decision log. Scope set by **D12**: one folder, three sources, no access model.

> The previous 568-line version of this document described the tiered, ACL-partitioned design
> superseded by D12. It is in git history if the reasoning is ever needed again.

## 1. Shape

```
<kb folder>/            <- ordinary Drive sharing; whoever can open it reads everything
  records/              <- Google Docs. Reorganize by hand freely; subfolders mean nothing.
  index                 <- Sheet, two tabs: Records | Claims
  .cache                <- claims keyed by content_hash
  Entities              <- optional alias map
```

Indexes are **derived**. Deleting one and rebuilding is routine, not recovery — which is what makes
hand-reorganisation free: nothing tracks where a document used to be.

## 2. Records tab

One row per source event: per recording, per issue, per pull request — never per commit. Mixed
granularity destroys ranking, because long documents match everything.

| Column | Notes |
|---|---|
| `record_id` | `{source}:{source_id}`. **Primary key.** Dedup on this, never on title. |
| `source` | `plaud` · `linear` · `github` |
| `source_url` | Back-link to the truth |
| `title` | Not unique. Never used for identity. |
| `occurred_at` | When the event happened, not when ingested |
| `participants` | `entity_id` list, or plain names if Entities is unused |
| `topics` | Flat tags |
| `raw_doc_id` | Drive file id. Empty when link-only. |
| `mutable` | `TRUE` ⇒ refetch before answering; never trust anything cached |
| `content_hash` | Detects upstream change |
| `ingested_at` · `extractor_version` | Staleness and re-distillation triggers |

**No status column.** Caching Linear state is the one change that would make the KB start lying, and
a reader cannot distinguish a stale cell from a fresh one.

Copy the immutable, link the mutable: recordings and merged PRs are copied into Docs; Linear issues
and open PRs get a row and a link, nothing more.

## 3. Claims tab

The distilled layer, and what search actually hits — raw transcripts are long, full of filler and
recognition errors, and match almost any query.

`claim_id` · `record_id` · `statement` (one self-contained sentence) · `type`
(`decision`/`insight`/`commitment`/`risk`/`open-question`) · `speaker` · `occurred_at` ·
`confidence` (`stated`/`implied`) · **`evidence`** (verbatim span) · `evidence_anchor` · `topics` ·
`extractor_version`.

Raw Docs are never modified, so distillation can be re-run whenever prompts improve.

## 4. Ingest

```
read watermark(source)
fetch changed since watermark
for each item:
    never-ingest check      -> skip, logging rule id + count only
    write Doc into the kb folder, stamp identity into appProperties
    write Records row
    distill -> validate evidence verbatim -> write Claims rows
advance watermark            only past fully committed items
```

**The never-ingest gate runs before content is fetched**, and the skip log must not describe what it
skipped: `skipped 3 item(s) (rule: no_one_to_ones)`. A descriptive log recreates the excluded content
somewhere else, which is the leak the rule exists to prevent — and a helpful log is the obvious thing
to write.

**Distillation contract.** 3–15 claims per record; each needs `statement`, `type`, `confidence`, and
an `evidence` span that **appears verbatim in the source**, checked by substring containment.
Failures are discarded, never repaired — string containment either holds or it does not, so it is
the cheapest decisive anti-fabrication guard available. The cap matters: forty claims per recording
dilutes retrieval until ranking is meaningless.

**Dedup** keys on `record_id`. Unchanged `content_hash` and current `extractor_version` ⇒ skip
entirely, no refetch and no LLM spend. Re-extraction replaces a record's claims wholesale rather than
merging, because merged versions produce near-duplicates that never converge.

## 5. Rebuild

Indexes are caches. A rebuild walks `records/`, reads each file's `appProperties` stamp, refetches
the link-only records, and rewrites the index from what is actually present. Files that vanished stop
appearing; files that arrived appear; **moves and renames need no handling at all**, because identity
lives in file metadata rather than in a path or a filename.

Claims are looked up in `.cache` by `content_hash`, so a rebuild after a reshuffle costs almost
nothing.

Watermarks are an optimization for fetching new source material only. They are not load-bearing for
correctness, because a full rebuild is always available.

## 6. Retrieval

1. **Metadata filter** — date range, participants, source, topic, type. Most questions are scoped,
   and this is exact and free.
2. **Lexical** — claim text plus Drive full-text over raw Docs. Names, ticket IDs, error strings —
   exactly what semantic search is worst at.
3. **Semantic rerank** — the agent reads the candidate set. Conceptual recall only.

**No embedding store.** At this corpus size, full-text plus distilled statements plus agent
reranking beats a vector index that must resync on every re-extraction. Revisit when measured recall
fails, not on principle.

**Resolve names to `entity_id` before filtering, never after.** `participants` stores ids, so
matching a raw name returns nothing — silently, and indistinguishably from genuine absence. This is
the most deceptive failure available here.

Anything `mutable` is refetched live before entering an answer; if the source is unreachable the
answer says so rather than falling back to a cached row.

**Every answer carries** its supporting claims with source links and dates, "as of" stamps on live
data, and an explicit *not found* where nothing was found. What was *said* (`stated`), what was
*inferred* (`implied`), and what is *live* stay distinguishable.

Conflicting claims are surfaced with both dates rather than silently resolved toward the recent.
Counts are never presented as measurements: "three people raised churn" is false — the truth is that
churn appears in three recordings that happened to be captured and ingested.

## 7. `kb.config.yaml`

```yaml
version: 1
folder_id: "..."            # the one KB folder
entities_sheet_id: "..."    # optional

sources:
  plaud:  {enabled: true}
  linear: {enabled: true, teams: [ENG, BD]}
  github: {enabled: true, org: acme, repos: ["*"]}

never_ingest:
  title_patterns:  ["1:1", "performance", "comp", "offer"]
  folder_patterns: ["Personal", "HR"]

extraction:
  version: v1
  min_claims: 3
  max_claims: 15

glossary:                   # ASR corrections applied at ingest
  "plod": "Plaud"

retrieval:
  max_claims_in_context: 20
```

No secrets: Google credentials live outside the repo, `gh` holds its own token.

## 8. Assumptions not yet verified

The Plaud connector is unauthorized, so its tool surface is assumed. The design assumes a stable id,
timestamp, and **full transcript text**.

- **Summaries only** — verbatim evidence becomes impossible and claims stop being checkable.
  Material enough to reopen §3, not patch around.
- **No speaker segmentation** — `speaker` stays mostly empty.
- **No folders or tags** — nothing to map in config; everything simply lands in the one folder,
  which under D12 is no longer a problem.
