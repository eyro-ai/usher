# Usher — Linear source and router — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One working source skill (`usher-linear`) and the router (`usher`), with an eval that proves questions reach the right skill.

**Architecture:** Both are `SKILL.md` files inside the existing `plugins/usher` plugin. No code ships in the plugin — the only executable artifact is the eval harness under `evals/`, which loads the plugin with `--plugin-dir` and inspects the `Skill` tool calls Claude actually makes.

**Tech Stack:** Markdown skills · the Linear MCP connector · `claude -p --output-format stream-json` for the eval · `claude plugin validate --strict`.

**Spec:** `docs/specs/2026-08-12-usher.md`

## Global Constraints

- **Read-only.** `usher-linear` may never call `save_issue`, `save_comment`, `save_project`, `delete_comment` or any other mutating tool. The OAuth grant includes write, so the boundary exists only in the skill.
- **Never name the MCP tool prefix.** Refer to Linear tools by bare name (`list_issues`, `get_issue`, `list_projects`). The prefix differs between the plugin connector (`mcp__plugin_linear_linear__*`) and the claude.ai one (`mcp__claude_ai_Linear__*`), and hardcoding one breaks the other.
- **Every answer ends with a `Searched:` line.** Spec requirement, and it is how a reader sees what was *not* looked at.
- **No settings file, no setup step.** Every value is discovered from where it already lives (spec: Configuration). A source that cannot answer is simply absent.
- **Empty is an answer.** Never reconstruct issues that were not read.
- Repo: `~/Projects/usher`. Plugin: `plugins/usher/`.

## Verified before writing this plan

- `claude plugin validate --strict` passes on both manifests, locally and as cloned from the private repo.
- `claude plugin eval` is **early access and unavailable on this account** — it produces nothing. This plan does not use it.
- `--plugin-dir <path>` loads an uninstalled plugin for a single session.
- `--output-format stream-json --verbose` emits `tool_use` events; a fired skill appears as
  `{"name": "Skill", "input": {"skill": "<plugin>:<skill>", "args": "..."}}`. The eval asserts on that.
- The Linear connector is authorized against workspace **eyro** (`linear.app/eyro`), one team, `Eyro`.

## File structure

```
plugins/usher/skills/
  usher-linear/SKILL.md      Task 2
  usher/SKILL.md             Task 3
evals/
  routing.tsv                question -> expected skill      Task 1
  run_routing.py             the harness                     Task 1
```

---

### Task 1: The routing eval harness

**Files:**
- Create: `evals/routing.tsv`
- Create: `evals/run_routing.py`

**Interfaces:**
- Consumes: nothing — it runs against the plugin as it stands.
- Produces: `python3 evals/run_routing.py` exits 0 when every question dispatches to its expected skill, 1 otherwise. Task 3 is done when this passes.

- [ ] **Step 1: Write the fixtures**

Create `evals/routing.tsv` — tab-separated, question then expected skill. Only Linear is built here, so unrelated questions expect `none`: the router must **not** invent a source that does not exist.

```
# question	expected skill (or 'none')
What is the status of the onboarding project?	usher-linear
Who owns the billing work?	usher-linear
What issues are in the current cycle?	usher-linear
What is planned for next cycle?	usher-linear
Show me open bugs	usher-linear
Which projects are in progress?	usher-linear
What did the partner call decide?	none
What are my notes on positioning?	none
```

- [ ] **Step 2: Write the harness**

Create `evals/run_routing.py`:

```python
#!/usr/bin/env python3
"""Routing eval - does each question dispatch to the expected skill?

Asserts on the Skill tool calls Claude actually makes, read from the
stream-json event log, rather than on any text a skill was told to print.
A skill can be instructed to claim it searched Linear; it cannot fake
having been invoked.
"""
import csv
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PLUGIN = HERE.parent / "plugins" / "usher"
FIXTURES = HERE / "routing.tsv"
TIMEOUT_SECONDS = 300


def skills_invoked(stream: str) -> set:
    """Skill names fired during the run, with the plugin prefix stripped."""
    fired = set()
    for line in stream.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == "Skill":
                name = block.get("input", {}).get("skill", "")
                fired.add(name.split(":")[-1])
    return fired


def ask(question: str) -> str:
    result = subprocess.run(
        [
            "claude",
            "--plugin-dir", str(PLUGIN),
            "-p", question,
            "--output-format", "stream-json",
            "--verbose",
        ],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    return result.stdout


def load_fixtures():
    rows = []
    with FIXTURES.open() as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if not row or row[0].startswith("#"):
                continue
            expected = row[1].strip()
            rows.append((row[0].strip(), set() if expected == "none" else {expected}))
    return rows


def main() -> int:
    failures = []
    fixtures = load_fixtures()

    for question, expected in fixtures:
        fired = skills_invoked(ask(question))
        # Only judge usher skills; an unrelated skill firing is not a routing error.
        fired = {s for s in fired if s == "usher" or s.startswith("usher-")}
        fired.discard("usher")  # the router itself is not a destination

        if fired == expected:
            print("PASS  " + question[:58])
        else:
            failures.append((question, sorted(expected), sorted(fired)))
            print("FAIL  " + question[:58])

    print("\n%d/%d routed correctly" % (len(fixtures) - len(failures), len(fixtures)))
    for question, expected, got in failures:
        print("\n  %s\n    expected: %s\n    fired:    %s"
              % (question, expected or ["none"], got or ["none"]))

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Run it to verify it fails**

Run: `python3 evals/run_routing.py`
Expected: FAIL — the six `usher-linear` rows fire nothing, because no skills exist yet. The two `none` rows pass trivially; that is expected, and is why they are not the whole suite.

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/usher
git add evals/
git commit -m "test: routing eval asserting on Skill dispatch (failing until skills land)"
```

---

### Task 2: `usher-linear`

**Files:**
- Create: `plugins/usher/skills/usher-linear/SKILL.md`

**Interfaces:**
- Consumes: the Linear MCP connector, authorized as the user.
- Produces: a skill named `usher-linear` that answers Linear questions and ends with `Searched: linear (<n> results)`.

- [ ] **Step 1: Write the skill**

Create `plugins/usher/skills/usher-linear/SKILL.md`:

```markdown
---
name: usher-linear
description: Answer questions about work in Linear - issue and project status, who owns what, what is planned, what shipped in a cycle. Use whenever a question asks about the state of work rather than the reasoning behind it. Triggers on "what's the status of", "who owns", "what's planned", "what's in this cycle", "is X done", and on any mention of an issue identifier.
---

# usher-linear

Answers from Linear, through the Linear MCP connector, under the user's own account - so it sees
exactly the teams they can see. Nothing is copied or stored.

## Read only

Never call `save_issue`, `save_comment`, `save_project`, `save_status_update`, `delete_comment`, or
any other tool that changes Linear. The OAuth grant includes write access; this boundary exists only
here. Usher reads.

## Before answering

Call `get_workspace`. If it fails, say Linear is unavailable and that `/mcp` will reconnect it, then
stop. Never describe issues you have not read.

## Choosing what to search

The commonest mistake is answering a project question with issues, or the reverse - both return
something technically correct and useless.

| The question is about | Use |
|---|---|
| A specific piece of work, a bug, an assignment | `list_issues`, then `get_issue` for detail |
| An initiative, a theme, "what are we working on" | `list_projects`, then `get_project` |
| A time box - this cycle, next cycle, what shipped | `list_cycles`, then issues filtered to it |
| Who someone is, or what they own | `list_users`, then issues filtered by assignee |

Refer to these tools by their bare names. The MCP prefix differs depending on whether the connector
was installed as a plugin or through claude.ai, and hardcoding one breaks the other.

## Answering

- **Refetch every time.** Status, assignee and cycle change constantly. Never answer from earlier in
  the conversation, and never from memory.
- **Cite the identifier, not just a link** - `EYR-142 - In Progress, Ana` is checkable in a way a
  bare URL is not. Include the URL as well.
- **Cap at 20 results**, most recently updated first. A dump of every matching issue is not an answer.
- **Stamp it.** Status is a snapshot: say "as of now".
- **End with exactly one line:** `Searched: linear (<n> results)` - including when the answer is
  nothing found.
- If nothing matched, say so plainly. Do not describe work that might exist.
```

- [ ] **Step 2: Validate the plugin**

Run: `claude plugin validate plugins/usher --strict`
Expected: PASS

- [ ] **Step 3: Verify it retrieves, end to end**

Run:

```bash
claude --plugin-dir ~/Projects/usher/plugins/usher \
  -p "What issues are open right now? Answer briefly." \
  --output-format text
```

Expected: real issues from the **eyro** workspace, each carrying an identifier like `EYR-…`, and a
final `Searched: linear (<n> results)` line. If Linear is disconnected, the expected output is
instead a clear "Linear is unavailable, run /mcp" — a pass for the skill and a fail for the connector.

- [ ] **Step 4: Run the routing eval**

Run: `python3 evals/run_routing.py`
Expected: the six `usher-linear` rows now PASS, because the skill's description matches those
questions directly. **8/8.**

If they do not all pass, the fix is the skill's `description` frontmatter — that is what dispatch
matches on. Do not weaken the fixtures.

- [ ] **Step 5: Commit**

```bash
cd ~/Projects/usher
git add plugins/usher/skills/usher-linear/
git commit -m "feat: usher-linear - read-only Linear source skill"
```

---

### Task 3: `usher` — the router

**Files:**
- Create: `plugins/usher/skills/usher/SKILL.md`
- Modify: `evals/routing.tsv` (append two rows)

**Interfaces:**
- Consumes: source skills by name. Only `usher-linear` exists; the rest are named so routing works the moment they are added.
- Produces: a skill named `usher` that dispatches to source skills and never queries a source itself.

- [ ] **Step 1: Add fixtures the router must handle**

Append to `evals/routing.tsv`:

```
What do we know about onboarding?	usher-linear
Tell me everything about the billing work	usher-linear
```

These are unscoped. With one source installed, fanning out means Linear alone — which is the
behaviour to lock in now, so that adding a source later changes the expectation visibly.

- [ ] **Step 2: Run the eval to see the new rows fail**

Run: `python3 evals/run_routing.py`
Expected: 8/10 — the two unscoped rows fail, since nothing yet tells the agent to fan out.

- [ ] **Step 3: Write the router**

Create `plugins/usher/skills/usher/SKILL.md`:

```markdown
---
name: usher
description: The front door to Eyro's knowledge. Use for any question about what was said, decided, built, planned or agreed - meetings, notes, issues, customers, code, documentation. Works out which systems hold the answer, asks them, and replies with citations. Triggers on "what do we know about", "what was decided", "what's the status of", "what happened with", "how was this built", "where is X documented", and on any question naming a customer, project, meeting or repository.
---

# usher

Work out which sources can answer, invoke their skills, and reply with citations.

**Never query a source directly.** Invoke its skill. That boundary is what lets a source be swapped
or removed without touching this file.

## Route

| The question is about | Skill |
|---|---|
| Status, ownership, what is planned, what shipped | `usher-linear` |
| What was said or decided in a meeting | `usher-gdrive` |
| Documentation, handbook, written-up knowledge | `usher-notion` |
| The user's own notes and thinking | `usher-obsidian` |
| A customer, a deal, an account's history | `usher-twenty` |
| How something was built, or why the code is that way | `usher-github` |

Route on the noun. A question naming a customer goes to `usher-twenty`; one naming a repository goes
to `usher-github`. Only fan out when there is genuinely no signal - a bare topic, or "what do we know
about X".

Route to **more than one** skill when the question spans them: "why did we build it that way" is
`usher-github` for what and `usher-gdrive` for why.

## Which sources exist

There is no configuration to read. A source skill that is not installed cannot be invoked, and a
source that has never been able to answer is simply absent - omit it entirely rather than reporting
it missing. Someone with no Twenty account should never read the word Twenty.

A source that normally works and is failing right now is different, and worth saying:
`linear(unavailable) - run /mcp to reconnect`.

## Rules

- **Refetch, never remember.** Status, ownership and deal state come from the source every time, even
  if they appeared earlier in this conversation.
- **Cite, don't merge.** Each claim names its source and links back. Never blend several systems into
  unattributed narrative.
- **Empty is an answer.** "Nothing in Linear" beats a plausible reconstruction. Never fill the gap.
- **A broken source is reported, not hidden.** If a skill reports its source unavailable, pass that
  on with the fix - `linear(unavailable) - run /mcp to reconnect`. Silently dropping it makes an
  incomplete answer look complete.

## Every answer ends with one line

    Searched: linear, gdrive(unavailable)

Name every source you invoked, whether or not it returned anything. Omit sources that are not set up
at all - they are not part of the picture. This line is how a reader learns what was *not* looked
at.
```

- [ ] **Step 4: Validate**

Run: `claude plugin validate plugins/usher --strict`
Expected: PASS

- [ ] **Step 5: Run the eval to verify it passes**

Run: `python3 evals/run_routing.py`
Expected: **10/10 routed correctly**

If the two `none` rows now fail — meaning the router invoked `usher-linear` for a meeting question —
the routing table's wording is too permissive. Fix the skill, not the fixtures: a fixture edited to
match behaviour is an eval that measures nothing.

- [ ] **Step 6: Commit**

```bash
cd ~/Projects/usher
git add plugins/usher/skills/usher/ evals/routing.tsv
git commit -m "feat: usher router - 10/10 routing fixtures pass"
```

---

## Exit criteria

- `claude plugin validate . --strict` and `claude plugin validate plugins/usher --strict` both pass.
- `python3 evals/run_routing.py` reports 10/10.
- A real Linear question returns real `EYR-…` issues with a `Searched: linear` line.
- Neither skill can write to Linear.

## Not in this plan

The other five source skills. There is no `usher-setup`: every value a skill needs is discovered from
where it already lives, so there is nothing to configure. The one that looked like it needed storing
- the Obsidian vault path - turned out to be in Obsidian's own registry.
