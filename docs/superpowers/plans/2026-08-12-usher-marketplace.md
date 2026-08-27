# Usher — Phase 1: Marketplace, first source, and the router

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A working Usher marketplace containing a router skill and one source skill, with a routing eval that proves the router sends questions to the right places.

**Architecture:** A git repo holding a Claude Code plugin marketplace. One plugin, `usher`, carrying every skill — install once, and sources stay independent as separate `SKILL.md` files. No code ships in the plugin: skills are instructions, and the only executable artifact is the eval harness, which lives outside the plugin.

**Tech Stack:** Markdown skills, a `marketplace.json` manifest, `gh` CLI, and `claude -p` headless for the eval.

**Spec:** `docs/specs/2026-08-12-usher.md`

## Global Constraints

- **No config file.** The spec is explicit: auth is ambient, and the one per-person value (Obsidian vault path) is asked for or read from the environment. Do not introduce YAML.
- **No index, no cache, no stored copy.** Every source is queried in place.
- **Every answer ends with a `Searched:` line** naming the sources consulted. This is a spec requirement ("say what was searched") *and* the hook the eval depends on — do not remove or reword it.
- **Empty is an answer.** Never reconstruct a plausible answer when a search returns nothing.
- Skills run under the user's own credentials. Nothing in a skill may take, or suggest, a shared or service token.
- Repo for the marketplace: `~/Projects/usher` (separate from `plaud-kb`, which holds the spec and this plan).

## Why GitHub is the first source

Of the five sources, `gh` is the only one verified reachable right now: Drive and Plaud connectors are unauthorized, the Linear MCP dropped mid-session, Twenty needs a key, and the Obsidian vault path is unknown. Building the pattern against a proven source means Task 2 cannot be blocked on someone else's OAuth flow.

## File structure

```
~/Projects/usher/
  .claude-plugin/marketplace.json      the marketplace manifest
  plugins/usher/
    .claude-plugin/plugin.json         the plugin manifest
    skills/usher/SKILL.md            the router          (Task 4)
    skills/usher-github/SKILL.md        first source        (Task 2)
  eval/
    routing.tsv                        question -> expected sources
    run_routing.py                     the harness         (Task 3)
  README.md
```

---

### Task 1: Marketplace and plugin skeleton

**Files:**
- Create: `~/Projects/usher/.claude-plugin/marketplace.json`
- Create: `~/Projects/usher/plugins/usher/.claude-plugin/plugin.json`
- Create: `~/Projects/usher/README.md`

**Interfaces:**
- Consumes: nothing.
- Produces: a marketplace named `usher` containing one plugin named `usher`, installable with `/plugin marketplace add ~/Projects/usher`.

- [ ] **Step 1: Write the failing check**

Create `~/Projects/usher/eval/check_manifests.py`:

```python
#!/usr/bin/env python3
"""Structural checks on the marketplace and plugin manifests."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


mkt_path = ROOT / ".claude-plugin" / "marketplace.json"
check(mkt_path.exists(), f"missing {mkt_path}")

if mkt_path.exists():
    mkt = json.loads(mkt_path.read_text())
    check(mkt.get("name") == "usher", "marketplace name must be 'usher'")
    check(isinstance(mkt.get("plugins"), list) and mkt["plugins"],
          "marketplace must list at least one plugin")
    for entry in mkt.get("plugins", []):
        check("name" in entry, "plugin entry missing 'name'")
        check("description" in entry, "plugin entry missing 'description'")
        src = entry.get("source")
        check(isinstance(src, str) and src.startswith("./"),
              f"{entry.get('name')}: source must be a relative path string")
        if isinstance(src, str):
            check((ROOT / src).is_dir(), f"{entry.get('name')}: {src} does not exist")
            manifest = ROOT / src / ".claude-plugin" / "plugin.json"
            check(manifest.exists(), f"{entry.get('name')}: missing {manifest}")
            if manifest.exists():
                plug = json.loads(manifest.read_text())
                check(plug.get("name") == entry.get("name"),
                      f"{entry.get('name')}: plugin.json name disagrees with the marketplace entry")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("manifests OK")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 ~/Projects/usher/eval/check_manifests.py`
Expected: FAIL — `missing .../.claude-plugin/marketplace.json`

- [ ] **Step 3: Write the manifests**

Create `~/Projects/usher/.claude-plugin/marketplace.json`:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "usher",
  "description": "Usher — internal knowledge skills — ask one question, get it routed to the system that holds the answer",
  "owner": {
    "name": "Eyro"
  },
  "plugins": [
    {
      "name": "usher",
      "description": "Ask questions across Google Drive, Obsidian, Linear, Twenty CRM and GitHub. Queries each source in place and answers with citations.",
      "version": "0.1.0",
      "category": "productivity",
      "author": {
        "name": "Eyro"
      },
      "source": "./plugins/usher"
    }
  ]
}
```

Create `~/Projects/usher/plugins/usher/.claude-plugin/plugin.json`:

```json
{
  "name": "usher",
  "version": "0.1.0",
  "description": "Ask questions across Eyro's systems. A router skill plus one skill per source, each querying in place.",
  "author": {
    "name": "Eyro"
  }
}
```

Create `~/Projects/usher/README.md`:

```markdown
# Usher

Ask Claude a question; it works out which system holds the answer, queries it in
place, and replies with citations. There is no index and no copy of any data.

## Install

    /plugin marketplace add ~/Projects/usher
    /plugin install usher@usher

## Skills

- `usher` — the router. The only one worth remembering.
- `usher-github` — pull requests, code, and review discussion.

Each source skill runs under your own credentials, so it sees exactly what you see.

## Design

See `docs/specs/2026-08-12-usher.md` in the `plaud-kb` repo.
```

- [ ] **Step 4: Run the check to verify it passes**

Run: `python3 ~/Projects/usher/eval/check_manifests.py`
Expected: PASS — `manifests OK`

- [ ] **Step 5: Commit**

```bash
cd ~/Projects/usher
git init -q
printf '.DS_Store\n' > .gitignore
git add -A
git commit -m "feat: usher marketplace skeleton"
```

---

### Task 2: The `usher-github` source skill

**Files:**
- Create: `~/Projects/usher/plugins/usher/skills/usher-github/SKILL.md`

**Interfaces:**
- Consumes: `gh` CLI, authenticated as the user.
- Produces: a skill that answers GitHub questions and ends every answer with a line matching `Searched: github (<n> results)`. Task 3's harness parses exactly that line.

- [ ] **Step 1: Write the failing smoke check**

Create `~/Projects/usher/eval/smoke_github.sh`:

```bash
#!/usr/bin/env bash
# Does usher-github actually retrieve, and does it report what it searched?
set -uo pipefail

if ! gh auth status >/dev/null 2>&1; then
  echo "SKIP: gh is not authenticated"; exit 0
fi

QUESTION="Using the usher-github skill, find any pull request in my repositories that mentions tests. Answer briefly."
OUT=$(claude -p "$QUESTION" --output-format text 2>/dev/null)

if ! grep -qiE '^Searched: *github' <<<"$OUT"; then
  echo "FAIL: no 'Searched: github' line in the answer"
  echo "--- last 15 lines ---"; tail -15 <<<"$OUT"
  exit 1
fi
echo "PASS: usher-github answered and reported its search"
```

Make it executable: `chmod +x ~/Projects/usher/eval/smoke_github.sh`

- [ ] **Step 2: Run it to verify it fails**

Run: `~/Projects/usher/eval/smoke_github.sh`
Expected: FAIL — no `Searched: github` line, because the skill does not exist yet.

- [ ] **Step 3: Write the skill**

Create `~/Projects/usher/plugins/usher/skills/usher-github/SKILL.md`:

```markdown
---
name: usher-github
description: Search GitHub for how something was built and why — pull requests, review discussion, and code. Use when a question is about implementation, when a change shipped, who wrote it, or why the code looks the way it does. Called directly, or by usher when routing a question.
---

# usher-github

Answers from GitHub using the `gh` CLI under the user's own token, so it sees exactly the
repositories they can see. Nothing is copied or stored.

## Before searching

Run `gh auth status`. If it fails, say GitHub is unavailable and stop — never describe repository
contents you have not read.

## How to search

In this order, because a pull request carries intent and discussion while a code hit carries only a
line:

1. **Pull requests by topic**
   `gh search prs --owner <org> "<terms>" --limit 20 --json number,title,url,repository,closedAt`
2. **Code**
   `gh search code --owner <org> "<terms>" --limit 20 --json path,repository,url`
3. **One pull request in depth**
   `gh pr view <number> --repo <owner/repo> --comments`

Widen the terms once if the first search is empty. Do not widen repeatedly — two empty searches
mean the answer is not here.

## Answering

- Cite every claim with its pull request or file URL. A claim with no link is not an answer.
- Prefer what the discussion says over what the diff implies; the reasoning lives in the comments.
- **End every answer with exactly one line:**
  `Searched: github (<n> results)`
  where `<n>` is how many results you actually looked at. Include this line even when the answer is
  "nothing found" — an incomplete answer must look incomplete.
- If nothing matched, say so plainly and stop. Do not reconstruct a plausible history.
```

- [ ] **Step 4: Run the smoke check to verify it passes**

First install the plugin so the skill is live:

```bash
# in an interactive Claude session
/plugin marketplace add ~/Projects/usher
/plugin install usher@usher
```

Then run: `~/Projects/usher/eval/smoke_github.sh`
Expected: PASS — `usher-github answered and reported its search`

- [ ] **Step 5: Commit**

```bash
cd ~/Projects/usher
git add -A
git commit -m "feat: usher-github source skill with a retrieval smoke check"
```

---

### Task 3: The routing eval harness

**Files:**
- Create: `~/Projects/usher/eval/routing.tsv`
- Create: `~/Projects/usher/eval/run_routing.py`

**Interfaces:**
- Consumes: the `Searched: <sources>` line produced by every source skill (Task 2) and by the router (Task 4).
- Produces: `python3 eval/run_routing.py` exits 0 when every fixture routes correctly, 1 otherwise.

- [ ] **Step 1: Write the fixtures and the harness**

Create `~/Projects/usher/eval/routing.tsv` (tab-separated: question, then expected sources):

```
# question	expected sources (comma separated)
How was retry logic implemented in our API client?	github
Why does the auth middleware look like that?	github
What pull requests shipped last week?	github
What are my notes on positioning?	obsidian
What was I thinking about pricing last month?	obsidian
What is the status of the onboarding project?	linear
Who owns the billing epic?	linear
What is planned for this cycle?	linear
What happened with the Acme account?	twenty
Where did the Globex deal land?	twenty
What was decided in the partner call?	gdrive
What did we say in the product review meeting?	gdrive
What do we know about churn?	gdrive,obsidian,linear,twenty,github
Tell me everything about the pricing change	gdrive,obsidian,linear,twenty,github
```

Create `~/Projects/usher/eval/run_routing.py`:

```python
#!/usr/bin/env python3
"""Routing eval — does usher send each question to the right sources?

Parses the `Searched:` line every skill is required to emit. A source marked
"(unavailable)" still counts as routed to: the router chose it, the source could
not answer, and hiding that would make an incomplete answer look complete.
"""
import csv
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
FIXTURES = HERE / "routing.tsv"
SEARCHED = re.compile(r"^Searched:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
TIMEOUT_SECONDS = 300


def parse_searched(text):
    """Return the set of sources named in the last Searched line, or None."""
    matches = SEARCHED.findall(text)
    if not matches:
        return None
    return {
        part.split("(")[0].strip().lower()
        for part in matches[-1].split(",")
        if part.strip()
    }


def load_fixtures():
    rows = []
    with FIXTURES.open() as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if not row or row[0].startswith("#"):
                continue
            rows.append((row[0].strip(), {s.strip() for s in row[1].split(",")}))
    return rows


def ask(question):
    result = subprocess.run(
        ["claude", "-p", question, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    return result.stdout


def main():
    failures = []
    fixtures = load_fixtures()

    for question, expected in fixtures:
        answer = ask(question)
        got = parse_searched(answer)

        if got is None:
            failures.append((question, sorted(expected), "no Searched line"))
            status = "FAIL"
        elif got != expected:
            failures.append((question, sorted(expected), sorted(got)))
            status = "FAIL"
        else:
            status = "PASS"
        print(f"{status}  {question[:64]}")

    print(f"\n{len(fixtures) - len(failures)}/{len(fixtures)} routed correctly")
    for question, expected, got in failures:
        print(f"\n  {question}\n    expected: {expected}\n    got:      {got}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 ~/Projects/usher/eval/run_routing.py`
Expected: FAIL — most rows report `no Searched line`, because no router exists yet. The `github` rows may already pass from Task 2; that is fine and expected.

- [ ] **Step 3: Record the baseline**

Note in the commit message how many rows passed before the router existed. A routing eval that was already passing would be measuring nothing.

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/usher
git add -A
git commit -m "test: routing eval harness and fixtures (failing until the router lands)"
```

---

### Task 4: The `usher` router

**Files:**
- Create: `~/Projects/usher/plugins/usher/skills/usher/SKILL.md`

**Interfaces:**
- Consumes: the source skills. Only `usher-github` exists so far; the others are named here so the router routes to them the moment they are installed.
- Produces: an answer ending in `Searched: <source>[, <source>...]`, satisfying `eval/run_routing.py`.

- [ ] **Step 1: Run the eval to confirm it is still failing**

Run: `python3 ~/Projects/usher/eval/run_routing.py`
Expected: FAIL — the non-github rows have no `Searched` line.

- [ ] **Step 2: Write the router skill**

Create `~/Projects/usher/plugins/usher/skills/usher/SKILL.md`:

```markdown
---
name: usher
description: The front door to Eyro's knowledge. Use for any question about what was said, decided, built, planned, or agreed — meetings, notes, issues, customers, code. Works out which systems hold the answer, queries them in place, and answers with citations. Triggers on "what do we know about", "what was decided", "what's the status of", "what happened with", "how was this built", and on any question naming a customer, project, meeting, or repository.
---

# usher

Route the question to the sources that can answer it, ask them, and answer with citations.

**Nothing is stored.** Every question is answered from live sources, so nothing here can go stale.

## Route

| The question is about | Ask |
|---|---|
| What was said or decided in a meeting | `usher-gdrive` |
| The user's own notes and thinking | `usher-obsidian` |
| Status, ownership, what is planned | `usher-linear` |
| A customer, a deal, an account's history | `usher-twenty` |
| How something was built, or why the code is that way | `usher-github` |
| An open topic, with no obvious home | **all five** |

When the question is unscoped — a bare topic, or "what do we know about X" — **fan out to every
source.** The cost is latency; the alternative is silently missing where the answer actually was.

Route to more than one source whenever the question spans them. "Why did we build it that way"
is often `usher-github` *and* `usher-gdrive`: the code says what, the meeting says why.

## Rules

- **Refetch, never remember.** Status, ownership, and deal state come from the source every time.
  Never answer these from earlier in the conversation.
- **Cite, don't merge.** Each claim names its source and links back. Never blend several systems
  into unattributed narrative.
- **Empty is an answer.** "Nothing in Linear or Drive" beats a plausible reconstruction. Never fill
  a gap with something that sounds right.
- **A missing source is reported, not hidden.** If a source skill is not installed, or its auth
  fails, still name it — as `<source>(unavailable)`. Silently dropping it makes an incomplete
  answer look complete.

## Every answer ends with one line

    Searched: gdrive, linear, github(unavailable)

List every source you routed to, whether or not it returned anything. This is how the reader knows
what was *not* looked at — and an answer without it is not finished.
```

- [ ] **Step 3: Reinstall the plugin so the new skill is picked up**

```bash
# in an interactive Claude session
/plugin uninstall usher@usher
/plugin install usher@usher
```

- [ ] **Step 4: Run the eval to verify it passes**

Run: `python3 ~/Projects/usher/eval/run_routing.py`
Expected: PASS — `14/14 routed correctly`

If some rows fail, the fix is the routing table's wording, not the fixtures. Fixtures describe what
you want; changing them to match the behaviour is how an eval stops meaning anything.

- [ ] **Step 5: Commit**

```bash
cd ~/Projects/usher
git add -A
git commit -m "feat: usher router — 14/14 routing fixtures pass"
```

---

## Verification status

Every artifact in this plan was extracted and exercised before the plan was issued:

- `check_manifests.py` runs — **fails** with the manifest removed, **passes** with it in place, and
  validated the actual JSON here (both manifests parse, names agree, the source path resolves).
- `run_routing.py`'s parser was unit-tested against both `Searched:` formats the skills emit —
  `Searched: github (12 results)` and `Searched: gdrive, linear, github(unavailable)` — plus
  case-insensitivity, last-line-wins, and the missing-line case. All correct.
- All 14 fixtures load, and every source name in them matches a real skill. No typos.
- `smoke_github.sh` passes `bash -n`.
- Both `SKILL.md` files have valid frontmatter whose `name` matches its directory.

Not verified, because it needs a live session and real credentials: whether the skills actually
trigger and route correctly. That is what Tasks 2 and 4 measure.

## Phase 1 exit criteria

- `python3 eval/check_manifests.py` passes.
- `eval/smoke_github.sh` passes — a real GitHub question returns cited results.
- `python3 eval/run_routing.py` reports 14/14.
- `/plugin install usher@usher` works from a clean session, and `usher` appears in the skill list.

## What comes next

| Phase | Builds | Blocked on |
|---|---|---|
| 2 | `usher-gdrive`, `usher-linear`, `usher-twenty`, `usher-obsidian` — one skill each, same shape as `usher-github`, one routing fixture batch each | Drive and Linear auth; Twenty's base URL and key; the Obsidian vault path |
| 3 | The scheduled ingest routine: `PlaudInbox` → `Meetings/<category>`, original to `Processed/`, errors to `Failed/` | The Zapier connection from Plaud to Drive; phase 2's `usher-gdrive` |

Phase 2 is four near-identical tasks and can be split across parallel workers once `usher-github`
has settled the pattern. Do not start it before Task 4 passes — the router's shape is what the other
sources conform to.

Phase 3 needs one decision that is still open: **which Drive account and folder** the routine
operates on, and whether it runs as a cloud routine or is triggered manually at first. Manual first
is the safer default — a scheduled job that mis-files silently is harder to notice than one you
watched run.
