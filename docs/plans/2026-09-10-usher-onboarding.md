# `usher-onboarding` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A seventh skill that takes a fresh machine from "the plugin is installed" to "the sources you actually want are connected and verified".

**Architecture:** One `SKILL.md` inside the existing plugin. It discovers its source list from sibling `usher-*` directories, probes each, shows what is true, asks which unconfigured ones to set up, does what it can, hands over what only a human can do, then re-probes. No code ships; the only executable artifact in this repo remains the eval harness.

**Tech Stack:** Markdown skill · `gh` CLI · the Linear and Google Drive MCP connectors · `curl` for Twenty · `claude plugin validate --strict` · `evals/run_routing.py`.

**Spec:** [`docs/specs/2026-09-10-usher-onboarding.md`](../specs/2026-09-10-usher-onboarding.md)

## Global Constraints

- **This skill is not read-only, and it is the only one.** Every other skill in this plugin forbids writing. This one writes `~/.usher/settings.json` and runs installers. It must say so explicitly, and must still never write to any *source* — no issue, note, file, PR or CRM record.
- **Nothing has to be run before a first question.** Source skills keep asking on first use. If this plan ends with a source skill's asking removed, it has broken the decision in `docs/decisions.md` and must stop.
- **Settings are read-modify-write on the whole object.** Load `~/.usher/settings.json`, change only the keys for sources being set up, write the whole object back. Never construct a fresh file. This is the only skill that writes several keys in one run, so a bug wipes settings for sources it was not asked about.
- **Never store or echo a secret.** Twenty's API key lives in the `.env` the user names; only the path goes in settings.
- **A source is reported working only because a probe succeeded** — never because the user said they clicked something.
- **Never name a source that is not installed.** `usher-notion` does not exist; it must not appear.
- Repo: `~/Projects/usher`. Plugin: `plugins/usher/`. Branch from `main`.

## File structure

```
plugins/usher/skills/usher-onboarding/SKILL.md   Task 2   the skill
evals/routing.tsv                                Task 1   fixtures, both directions
docs/onboarding.md                               Task 3   keeps every step, names the skill
README.md                                        Task 3   install pointer
plugins/usher/.claude-plugin/plugin.json         Task 4   0.5.0 -> 0.6.0
.claude-plugin/marketplace.json                  Task 4   0.5.0 -> 0.6.0
```

## Verified before writing this plan

- `main` is at `b939d22`; the spec and the CLAUDE.md rule are merged.
- Six skills exist: `usher`, `usher-gdrive`, `usher-github`, `usher-linear`, `usher-obsidian`, `usher-twenty`.
- `~/.usher/settings.json` currently holds `obsidian.vaults` and `twenty.env_file`, and no `gdrive.account`.
- The Drive probe works and returns the account: `search_files(query: "owner = 'me'", pageSize: 1)` returns an `owner` field.
- A full eval run is ~50 minutes for 34 fixtures. Targeted single-question checks take ~90 seconds each and do **not** touch `routing.tsv`.

---

### Task 1: Fixtures, in both directions

**Files:**
- Modify: `evals/routing.tsv`

**Interfaces:**
- Consumes: nothing.
- Produces: fixtures that fail until Task 2 lands, and guards that must keep passing after it.

- [ ] **Step 1: Append the fixtures**

Tab-separated, question then expected skill. Append to `evals/routing.tsv`:

```
Set up Usher	usher-onboarding
Help me connect my sources	usher-onboarding
I just installed Usher, what now?	usher-onboarding
Connect Linear	usher-onboarding
Which sources am I connected to?	usher-onboarding
```

Then the guards. **These are the point of this task.** A skill whose description is about setting up sources is a new hazard to the router, and the word "onboarding" already appears in a Linear fixture:

```
What is the status of the onboarding project?	usher-linear
What are my notes on onboarding?	usher-obsidian
How was the onboarding guide written?	usher-github
```

Note `What is the status of the onboarding project?` already exists near the top of the file. Do **not** add a second copy — it is already the guard that matters most. Add only the two that are new.

**One existing fixture is also a guard now, and it is easy to miss.** Line 26 reads:

```
What do we know about onboarding?	usher-linear,usher-github,usher-obsidian,usher-gdrive,usher-twenty
```

That is the bare-topic fan-out, and it contains the word *onboarding*. Its expectation must stay
exactly those five source skills — `usher-onboarding` must **not** join the fan-out, because it is
not a source and has nothing to contribute to a question about a topic. Do not edit that line. If it
starts failing because onboarding joined, the fix is the skill's description.

- [ ] **Step 2: Verify the fixtures fail**

Do not run the full suite; it is ~50 minutes and most of it is unrelated. Check one question directly:

```bash
claude --plugin-dir ~/Projects/usher/plugins/usher \
  -p "Set up Usher" --output-format stream-json --verbose \
  | grep -o '"skill":"[^"]*"' | sort -u
```

Expected: no `usher-onboarding` in the output, because the skill does not exist yet. Anything else means the fixture is not measuring what it claims.

- [ ] **Step 3: Commit**

```bash
git add evals/routing.tsv
git commit -m "test: usher-onboarding fixtures and router guards (failing until the skill lands)"
```

---

### Task 2: The skill

**Files:**
- Create: `plugins/usher/skills/usher-onboarding/SKILL.md`

**Interfaces:**
- Consumes: the settings keys the source skills already define — `obsidian.vaults` (list of absolute paths), `twenty.env_file` (absolute path), `gdrive.account` (email address).
- Produces: a skill named `usher-onboarding` that writes those same keys and reports a final status table.

- [ ] **Step 1: Write the frontmatter**

The description is what dispatch matches, so it is the highest-risk line in the change. Write it around the **act of connecting and configuring**, never around the word "onboarding" alone:

```yaml
---
name: usher-onboarding
description: Set up Usher's sources on this machine - work out which are already connected, ask which of the rest you want, and configure them. Use when someone has just installed Usher, wants to connect or reconnect a source, or asks what is currently set up. Triggers on "set up Usher", "connect my sources", "connect Linear", "I just installed Usher", "which sources am I connected to", "reconnect", "why is X not answering". Not for questions about work, notes, code, people or meetings - those go to the source skills, even when the question mentions onboarding as a topic.
---
```

That last sentence is deliberate. "What is the status of the onboarding project?" must reach `usher-linear`.

- [ ] **Step 2: Write the body**

Sections, in this order. Each must be written out in full — this file is the only copy a running skill can read, and none of `CLAUDE.md` reaches it.

1. **What this is** — an accelerator, not a prerequisite. Every source skill still asks on first use; skipping this costs nothing.
2. **This one writes** — the single exception in the plugin. It writes `~/.usher/settings.json` and may install `gh`. It still never writes to a *source*: no issue, note, file, pull request or CRM record.
3. **Find the sources** — list sibling directories of this skill's own directory, keep those matching `usher-*`, drop `usher` and `usher-onboarding`. Never hardcode the list; a new source must appear here without anyone editing this file.
4. **Probe each one** — the table below.
5. **Show what is true** — one row per source, naming the account, workspace or org that answered. A tick alone is not enough: a green Linear pointed at the wrong workspace is the failure this system fears most.
6. **Ask which to set up** — offer only the unconfigured ones, multi-select. Report the working ones; do not re-ask.
7. **Per-source setup** — the four subsections below.
8. **Re-probe and report** — final table, same shape.
9. **Settings safety** — the read-modify-write rule, stated at length.

- [ ] **Step 3: Write the probe table**

```
| Source | Probe | Report |
| linear | get_workspace | the workspace name |
| gdrive | search_files(query: "owner = 'me'", pageSize: 1) | the owner field - the account that answered |
| github | gh auth status | the ACTIVE account, and whether others are signed in |
| obsidian | obsidian.vaults in ~/.usher/settings.json | which vaults are recorded |
| twenty | $TWENTY_BASE_URL and $TWENTY_API_KEY, else twenty.env_file | the base URL, never the key |
```

Refer to MCP tools by bare name. The prefix differs between a plugin-installed connector and a claude.ai one, and hardcoding either breaks the other.

- [ ] **Step 4: Write the github subsection — a guided install**

Detect each step, perform only the missing ones, in this order:

```bash
gh --version            # present?
brew --version          # else is Homebrew present?
```

If Homebrew is missing, offer its install line rather than running it unannounced:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then:

```bash
brew install gh
gh auth login          # tell them the choices: GitHub.com, HTTPS, login with a web browser
gh auth setup-git
gh auth status
```

The skill must state why `gh auth setup-git` is not optional: without a credential helper, background refreshes of a private marketplace lose their credentials and updates stop silently.

It must also name the **active** account and say if more than one is signed in. A wrong active account yields empty GitHub results rather than an error.

- [ ] **Step 5: Write the twenty subsection — a guided remote setup**

The instance is remote, so there is nothing to discover locally on a fresh machine. Steps the skill walks:

1. Ask for the base URL of the Twenty instance.
2. Point them at **Settings → APIs & Webhooks** in Twenty to generate an API key.
3. Ask where to keep it, defaulting to `~/.env`, and write the two lines:

```bash
echo 'TWENTY_BASE_URL=<the url>' >> "$env_file"
echo 'TWENTY_API_KEY=<the key>' >> "$env_file"
```

4. Record **only the path** in `twenty.env_file`.
5. Verify with a real request and turn failure into a fix:

```bash
curl -sS --max-time 15 -o /dev/null -w '%{http_code}' \
  -H "Authorization: Bearer $TWENTY_API_KEY" "$TWENTY_BASE_URL/rest/people?limit=1"
```

`401` means the key is a JWT that has expired — regenerate it under Settings → APIs & Webhooks. A connection failure means the instance is not responding at that URL.

The skill must state: never echo the key, never run a command whose displayed output contains it, never write it into settings. Include the reason — Twenty's keys expire, so a copy in settings goes stale and then fails as though the instance were down.

- [ ] **Step 6: Write the linear and gdrive subsections**

Both are `+ → Connectors` in the desktop app followed by a browser flow the skill cannot drive. It gives the instruction, waits, then re-probes.

For **linear**: name the workspace reached and say plainly that a wrong workspace produces confident wrong answers rather than an error.

For **gdrive**: after the probe, tell the user which account answered, ask whether that is the one Usher should read, and write `gdrive.account`. This matches the contract `usher-gdrive` already enforces on every question — a mismatch there refuses rather than degrades.

- [ ] **Step 7: Write the obsidian subsection**

Read Obsidian's registry, offer the vaults it lists, write the chosen ones to `obsidian.vaults`. Registry locations:

```
macOS:   ~/Library/Application Support/obsidian/obsidian.json
Linux:   ~/.config/obsidian/obsidian.json
Flatpak: ~/.var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json
Windows: %APPDATA%/Obsidian/obsidian.json
```

Its `vaults` object maps an id to `{path, ts, open}`. Treat a missing `open` key as closed.

The skill must state: the registry says which vaults *exist*, settings say which the user *wants searched*, and it must never write a vault the user did not pick.

- [ ] **Step 8: Write the settings-safety section**

Copy the mechanic from `usher-obsidian`, then strengthen it, because this skill writes several keys at once:

> Load the whole object from `~/.usher/settings.json`. Change only the keys for the sources being set up. Write the whole object back. Never construct a fresh file containing only what this run touched — the file is shared with every other skill, and replacing it wipes their settings silently, in a way nothing would notice until an answer came back thin.

- [ ] **Step 9: Validate**

Run: `claude plugin validate plugins/usher --strict`
Expected: PASS

- [ ] **Step 10: Verify routing, targeted**

Check the new fixtures fire and the guards hold. Each takes ~90 seconds; do not run the full suite yet.

```bash
for q in "Set up Usher" "Connect Linear" "What is the status of the onboarding project?" "What are my notes on onboarding?"; do
  echo "== $q"
  claude --plugin-dir ~/Projects/usher/plugins/usher -p "$q" \
    --output-format stream-json --verbose | grep -o '"skill":"[^"]*"' | sort -u
done
```

Expected: the first two fire `usher-onboarding`; the third fires `usher-linear` and **not** onboarding; the fourth fires `usher-obsidian` and not onboarding.

If a guard fails, fix the **description**, never the fixture. A fixture edited to pass measures nothing. Note that widening a description has already regressed a guard once in this repo — narrow the setup skill's description rather than widening a neighbour's.

- [ ] **Step 11: Verify retrieval interactively**

Routing is not the same as working. Run the skill for real and confirm each probe returns what the table claims, especially that the Drive probe names an account and the GitHub probe names the *active* one.

- [ ] **Step 12: Commit**

```bash
git add plugins/usher/skills/usher-onboarding/
git commit -m "feat: usher-onboarding - guided setup for a fresh machine"
```

---

### Task 3: Docs

**Files:**
- Modify: `docs/onboarding.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the skill from Task 2.
- Produces: a guide that still reads start to finish, and names the skill as the faster route.

- [ ] **Step 1: Keep every step in `docs/onboarding.md`**

Do **not** replace Steps 5–8 with a pointer. `docs/decisions.md` records this: a reader who has installed nothing, or who would rather read than run a wizard, must be able to follow the guide start to finish. Indirection costs them the whole document; duplication only costs maintenance.

- [ ] **Step 2: Add the hand-off after Step 4**

Insert after the install step, before "Step 5 — Connect Linear":

```markdown
> **Faster route:** with Usher installed, you can type `set up Usher` and it will walk you through
> the remaining steps, check what is already connected, and verify each one as it goes. The steps
> below are the same thing done by hand — follow either.
```

- [ ] **Step 3: Update the README install section**

The README currently points only at the guide. Add the skill alongside it, so someone who has installed already sees the shorter path.

- [ ] **Step 4: Commit**

```bash
git add docs/onboarding.md README.md
git commit -m "docs: name usher-onboarding as the interactive route, keeping every written step"
```

---

### Task 4: Release

**Files:**
- Modify: `plugins/usher/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Bump both manifests**

`0.5.0` → `0.6.0` in **both** files. Without both, `/plugin update` sees no change and installs nothing. This has been missed twice in this repo.

Also update the marketplace entry's `description`, which enumerates what is live.

- [ ] **Step 2: Validate both**

```bash
claude plugin validate . --strict
claude plugin validate plugins/usher --strict
```
Expected: PASS on both.

- [ ] **Step 3: Run the full routing eval**

```bash
python3 evals/run_routing.py
```

~50 minutes, 41 fixtures (34 today, plus five onboarding questions and two new guards). **Do not commit while it runs** — a scoped run swaps `routing.tsv`, and committing across that has destroyed 13 fixtures before. Commit first, then start it.

Expect flake, not a clean sweep. Judge the run by these, not by the total:

- All five `usher-onboarding` fixtures fire the skill.
- All four onboarding-word guards behave: the Linear, Obsidian and GitHub ones reach their source
  skill and not onboarding, and the bare-topic fan-out still lists exactly its five sources.
- `Who owns the meeting notes action items?` is a known-unstable guard — it fired `usher-gdrive` in one run and `usher-linear` when re-run alone. A third sample is useful; a failure there is not this change's fault.
- `How was the router skill implemented?` fails because the eval's working directory is this repo, so a question *about this repo* is answered with `Bash` and no skill fires. Not a routing failure.

Reproduce any other failure individually before editing anything. One failure is not a signal.

- [ ] **Step 4: Commit and open the PR**

```bash
git add plugins/usher/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "Release 0.6.0: usher-onboarding"
```

The PR body must state the eval number, which fixtures are new, and any failure left standing with the reason it was left.

---

## Exit criteria

- `claude plugin validate . --strict` and `claude plugin validate plugins/usher --strict` both pass.
- The five `usher-onboarding` fixtures route to the skill.
- The onboarding-word guards still reach `usher-linear`, `usher-obsidian` and `usher-github`, and
  `What do we know about onboarding?` still fans out to exactly its five source skills.
- Running the skill for real connects at least one source end to end and reports it only after a probe succeeded.
- No source skill lost its ask-on-first-use behaviour.
- Both manifests read `0.6.0`.

## Not in this plan

`usher-notion`, which does not exist and must not be named. Any change to a source skill's asking — that would reverse the decision this skill was designed around. Removing the stale `onboarding-doc` worktree, which is unrelated housekeeping.
