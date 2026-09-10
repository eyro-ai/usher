# `usher-onboarding` — design

## What it is

A skill that gets a fresh machine from "the plugin is installed" to "the sources you actually want
are connected and verified". It is the **seventh skill and the first that is not a source**: it sets
things up, and never answers a question.

## The boundary that keeps the old decision intact

`docs/decisions.md` records `usher-setup` as cut, twice, on one principle: **nothing has to be run
before a first question.** This skill does not reverse that.

Every source skill keeps asking for what it needs on first use. `usher-onboarding` writes the same
settings keys those skills would have written, in advance, for someone who would rather do it all at
once. Skipping it costs nothing; running it changes no behaviour that would not otherwise happen.

**It is an accelerator, not a prerequisite.** If that ever stops being true — if a source skill drops
its own asking because onboarding exists — the decision has been reversed by accident and should be
recorded as such.

## Why it earns its place anyway

Twenty is the case that justifies it. `usher-twenty` says: if no `.env` holding the credentials is
found, *"Twenty is not set up on this machine: say nothing was found and stop. Do not ask for a path
outright."*

With a **remote** Twenty instance and a fresh Mac there is no such file, and nothing in the
ask-on-first-use model ever creates one. The source is therefore permanently and silently absent —
which `docs/decisions.md` already names as the worst available failure mode. A skill that can walk
someone through obtaining a base URL and a key, write them somewhere, and record the path is the
only thing that breaks that deadlock.

## Sources are discovered, never listed

The skill enumerates its sibling `usher-*` skill directories inside the plugin and treats that as the
set of possible sources, excluding itself and the router.

A hardcoded list would be correct exactly once. When `usher-notion` lands it must appear in
onboarding without anyone remembering to edit a second file — the same reason the router's route
table is the only place source names are written down today.

## Flow

**Detect, then offer.** The user chooses against what is true, not against a blank list.

1. **Probe every discovered source.**

   | Source | Probe | Reports |
   |---|---|---|
   | linear | `get_workspace` | the workspace name reached |
   | gdrive | `search_files(owner = 'me')`, 1 result | the account that answered |
   | github | `gh auth status` | the **active** account, and whether others are signed in |
   | obsidian | `obsidian.vaults` in settings | which vaults are recorded |
   | twenty | `$TWENTY_BASE_URL`/`$TWENTY_API_KEY`, else `twenty.env_file` | the base URL, never the key |

2. **Show what is true now** — one row per source, connected or not, naming the account or workspace
   where one answered. An account is worth more than a tick: a green Linear pointed at the wrong
   workspace is the failure this whole system fears.

3. **Ask which sources to set up**, offering the unconfigured ones. A source already working is
   reported and left alone, not re-asked.

4. **Set up each chosen source** — below.

5. **Re-probe and show a final table.** A source is reported working **only because a probe
   succeeded**, never because the user said they clicked something.

## What the skill does, and what only the user can do

OAuth flows and `gh auth login` are interactive and browser-bound. The skill does what it can, hands
the rest over with exact instructions, and then re-checks.

### github — guided install

Detect each step and perform only the missing ones:

`gh` present? → else Homebrew present? → else offer the Homebrew install line → `brew install gh` →
`gh auth login` (tell them the choices: GitHub.com, HTTPS, login with a web browser) →
`gh auth setup-git` → `gh auth status` to confirm.

`gh auth setup-git` is not optional here. Without a credential helper, background refreshes of a
private marketplace lose their credentials and updates stop silently.

**Name the active account, and say if there is more than one.** A wrong active account yields empty
GitHub results rather than an error, so it is worth surfacing before it confuses someone.

### twenty — guided remote setup

The instance is remote, so there is nothing to discover locally on a fresh machine.

1. Ask for the base URL of the Twenty instance.
2. Point them at **Settings → APIs & Webhooks** in Twenty to generate an API key.
3. Ask where to keep it, defaulting to `~/.env`, and write the two `TWENTY_*` lines there.
4. Record **only the path** in `twenty.env_file`.
5. Verify with a real request, and turn a failure into a fix: `401` means the key is a JWT that has
   expired, not that the instance is down.

**The key is never stored in settings and never echoed.** It lives in the file the user chose and is
read fresh on every question, because Twenty's keys expire.

### linear, gdrive — verify and confirm

Both are `+ → Connectors` in the desktop app, followed by a browser flow the skill cannot drive.

For **gdrive** the skill additionally confirms the account that answered and writes
`gdrive.account`, matching the contract `usher-gdrive` already enforces on every question.

For **linear** it names the workspace reached and says plainly that a wrong workspace produces
confident wrong answers rather than an error.

### obsidian — offer candidates

Read Obsidian's own registry, offer the vaults it lists, write the chosen ones to `obsidian.vaults`.

The registry says which vaults *exist*; settings say which the user *wants searched*. Only the second
question is the skill's to record, and it must never write a vault the user did not pick.

## Settings safety

This becomes **the only skill that writes several keys in one run**, and therefore the most dangerous
writer in the repo.

Load the whole object from `~/.usher/settings.json`, change only the keys for the sources being set
up, write the whole object back. Never construct a fresh file containing only what this run touched:
a bug there wipes settings for sources it was not even asked about, silently, in a way nothing would
notice until an answer came back thin.

## Relationship to `docs/onboarding.md`

**The guide stays complete.** Its per-source steps are not replaced by a pointer at this skill.

A reader who has installed nothing yet, or who would simply rather read than run a wizard, must be
able to follow the guide start to finish. Indirection costs them the whole document; duplication only
costs maintenance. The guide is rewritten to name `usher-onboarding` as the faster interactive route
to the same outcome, and the README's install pointer says the same.

The drift risk is real and accepted: when a setup procedure changes, both must change. That is the
trade made deliberately, recorded in `docs/decisions.md`.

## Routing risk

A skill whose description is about *setting up sources* is a new hazard to the router. "What's the
status of the onboarding project?" contains the word onboarding and must still reach `usher-linear`.

So the description is written around the act of connecting and configuring, never around the word
onboarding alone, and the eval gains guards in both directions: questions that must reach it, and
ordinary questions that must not.

## Not in this design

No `enabled` flag. The spec's rule holds — a source that cannot answer is simply absent, and choosing
not to set something up is indistinguishable from not having it. Unselected sources are skipped, not
recorded as disabled and not disabled in the harness.
