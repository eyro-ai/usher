---
name: usher-onboarding
description: Set up Usher's sources on this machine - work out which are already connected, ask which of the rest you want, and configure them. Use when someone has just installed Usher, wants to connect or reconnect a source, or asks what is currently set up. Triggers on "set up Usher", "connect my sources", "connect Linear", "I just installed Usher", "which sources am I connected to", "reconnect", "why is X not answering". Not for questions about work, notes, code, people or meetings - those go to the source skills, even when the question mentions onboarding as a topic.
---

# usher-onboarding

Gets this machine from "the plugin is installed" to "the sources you actually want are connected and
verified". It is the only skill here that is not a source: it sets things up, and never answers a
question about work, notes, code, people or meetings.

If a question arrives that is about *content* rather than *connection* — the status of something, a
note, a pull request, a customer, a meeting — this is the wrong skill. Say so and stop, so the source
skill can take it.

## An accelerator, not a prerequisite

**Nothing has to be run before a first question.** Every source skill still asks for what it needs on
first use, and will keep doing so. This skill writes the same settings keys those skills would have
written, in advance, for someone who would rather do it all at once.

So never tell the user that Usher must be set up before it can be used, never say a question is
blocked on running this, and never suggest that skipping a source here disables it. Skipping this
entirely costs nothing.

## This skill writes — and it is the only one that does

Every other skill in the plugin is read-only and says so. This one is the exception, and the
exception is narrow:

| It may write | It must never write |
|---|---|
| `~/.usher/settings.json` | Anything in a source |
| A `.env` file the user names, for Twenty's credentials | Any file inside an Obsidian vault |
| Installing `gh` (and offering the Homebrew install line) | |

**It never writes to a source.** No Linear issue, comment, project or status update. No Obsidian
note. No Drive file, and no change to who can see one. No GitHub issue, pull request, release or
`git push`. No Twenty record — no `POST`, `PATCH`, `PUT` or `DELETE` to `/rest/*`, no GraphQL
`mutation`, nothing under `/metadata`.

Every token involved grants write access. Linear's OAuth includes it, Drive's includes it, `gh`
carries the user's full access, Twenty's key does not distinguish read from write, and a vault is
ordinary files. There is no API-side guard on any of them. The boundary exists only in this text.

Setting a source up is a read against it plus a write to local settings. Nothing more.

## Never store or echo a secret

Twenty's API key lives in the `.env` file the user names. **Only the path goes into settings.**

Never echo the key, never run a command whose displayed output would contain it, never put it in a
message, and never write it into `~/.usher/settings.json`. The reason is not only exposure: Twenty's
keys are JWTs and they expire, so a copy in settings goes stale and then fails as though the instance
were down.

The same holds for every other credential encountered here. Record paths and account names. Never
record a token.

## Step 1 — find the sources

**Never hardcode the list of sources.** Discover them, so a source added to the plugin later appears
here without anyone editing this file.

This file lives at `<plugin>/skills/usher-onboarding/SKILL.md`. List the sibling directories of its
own directory, keep the ones matching `usher-*`, and drop two: `usher` — that is the router, not a
source — and `usher-onboarding`, which is this skill.

```bash
skills_dir=<the directory containing this skill's own directory>
ls -1 "$skills_dir" | grep '^usher-' | grep -vx 'usher-onboarding'
```

If that directory is not known, find it:

```bash
find ~/.claude/plugins -maxdepth 6 -type d -path '*/usher/skills/usher-*' 2>/dev/null
```

**This can return several matches** — the plugin cache keeps more than one installed version, and
each holds the same skill directories. **Take one** and read the source list from it. They are the
same set; listing a source twice because two cached copies were walked is the only way this goes
wrong.

`-maxdepth` goes before the tests, not after. GNU `find` warns when it comes later, and the warning
in the output is easy to mistake for the search having failed.

The result of this step is the set of sources that exist on this machine. **Never name a source that
is not in it** — not in a table, not as a suggestion, not as something that could be added. A source
whose skill is not installed is invisible, not missing.

## Step 2 — probe each one

Probe every discovered source before asking the user anything. They choose against what is true, not
against a blank list.

**A probe is a read that something answered. Reading a setting is not a probe.** A recorded path
proves a path was recorded, not that anything is there. Every row below ends in an observation:

| Source | Probe | Report |
|---|---|---|
| linear | `get_workspace` | the workspace name |
| gdrive | `search_files(query: "owner = 'me'", pageSize: 1, excludeContentSnippets: true)` | the `owner` field — the account that answered |
| github | `gh auth status` | the **active** account, and whether others are signed in |
| obsidian | read `obsidian.vaults` from `~/.usher/settings.json`, then **stat every path in it** | the vaults that exist on disk, and by name any recorded path that does not |
| twenty | read the credentials, then **make the real request** (both below) | the base URL and what the request returned, never the key |

**Refer to MCP tools by their bare name** — `get_workspace`, `search_files` — never with an MCP
prefix. The prefix differs between a plugin-installed connector and a claude.ai one, and hardcoding
either breaks the other.

If a discovered source is not in this table, read its own `SKILL.md` to learn what it needs, and
probe with the cheapest read it describes. Do not guess a probe.

### Three states, not two

Every source lands in exactly one of these, and the table in Step 3 must distinguish all three:

| State | Means |
|---|---|
| **connected** | a probe just succeeded, and the account, workspace, org or path it reached is named |
| **not configured** | nothing to probe with — no credentials, no recorded path. This is the state offered for setup |
| **configured but not answering** | there were credentials or a recorded path, and the probe still failed. Say what failed and why |

Never collapse the last two into one row. "Not configured" invites setup; "configured but not
answering" means something that was working has broken, and the fix is different — a regenerated key,
a vault that moved, a reconnected connector.

### Probing twenty

Read the credentials first, exactly as `usher-twenty` does — the environment, and failing that the
path in `twenty.env_file`:

```bash
# 1. the environment
[ -n "$TWENTY_BASE_URL" ] && [ -n "$TWENTY_API_KEY" ]   # if both set, use them

# 2. else the .env recorded in settings
env_file=<the twenty.env_file value from ~/.usher/settings.json>
TWENTY_BASE_URL=$(sed -n 's/^TWENTY_BASE_URL=//p' "$env_file" | head -1 | tr -d "\"'")
TWENTY_API_KEY=$(sed -n 's/^TWENTY_API_KEY=//p' "$env_file" | head -1 | tr -d "\"'")
```

Extract only those two lines. **Never source the whole file** — it usually holds unrelated tokens for
unrelated services.

If no credentials are found by either route, Twenty is **not configured**. Stop there; there is
nothing to probe. If credentials were found, probe with the real request — this is the same command
as in Step 5, and it is the probe, not merely a setup-time check:

```bash
curl -sS --max-time 15 -o /dev/null -w '%{http_code}' \
  -H "Authorization: Bearer $TWENTY_API_KEY" "$TWENTY_BASE_URL/rest/people?limit=1"
```

**Run it with `$TWENTY_API_KEY` exactly as written — never substitute the key itself.** The text of a
Bash command is displayed before it runs, so a key pasted into that header is on screen, in the
transcript, and in the shell history of whatever ran it.

`200` is **connected**; anything else is **configured but not answering**, read through the result
table in Step 5 — `401` in particular means the key is a JWT that has expired.

**Credentials on file are not a working Twenty.** A key recorded months ago has very likely expired,
and reporting it as connected because the path is still in settings is a wrong answer that looks
right — precisely the failure this skill exists to prevent.

### Probing obsidian

Read `obsidian.vaults` from `~/.usher/settings.json`, then stat each path:

```bash
for v in <each path in obsidian.vaults>; do
  [ -d "$v" ] && echo "ok   $v" || echo "MISSING $v"
done
```

No recorded vaults at all is **not configured**. Every recorded vault present is **connected** —
report them. **A recorded vault that is not on disk is a failure, and the path goes in the report by
name**: a vault that was renamed, moved, or lives on an unmounted volume answers nothing, and saying
"connected" because settings still mention it is the same wrong-answer-that-looks-right failure.

If some vaults exist and others do not, say both: name what is searchable and name what is missing.

## Step 3 — show what is true

One row per source. Connected or not, **and the account, workspace or org that answered**.

A tick alone is not enough. A green Linear pointed at the wrong workspace is the failure this whole
system fears most: it answers confidently, cites correctly, and is wrong, and nothing in the output
looks unusual. The account name is the only thing that catches it, so it goes in the table every
time.

```
| Source   | Status                       | Reached                                      |
|----------|------------------------------|----------------------------------------------|
| linear   | connected                    | workspace "Eyro"                             |
| gdrive   | connected                    | someone@example.com                          |
| github   | connected                    | active account: someuser                     |
| obsidian | configured but not answering | recorded vault missing: /Users/me/Old Vault  |
| twenty   | not configured               | no credentials in the environment or settings|
```

Use all three statuses from Step 2. A source with a recorded path or key that failed its probe is
**configured but not answering** — never "not configured", which would send the user to set up
something already set up, and never "connected".

**A source is reported working only because a probe succeeded.** Never because the user said they
clicked something, and never because a setting exists — a recorded path proves a path was recorded,
not that anything answers. This rule outranks anything else in this file: if some other line here
could be read as letting a settings value stand in for a probe, it is wrong and this rule wins.

## Step 4 — ask which to set up

Offer **only the sources that are not working**, as a multi-select — that is both failing states, *not
configured* and *configured but not answering*. Report the connected ones and leave them alone; do not
re-ask about a source that just answered.

Say which of the two a source is in when you offer it. Setting up something for the first time and
repairing something that has stopped answering are different jobs, and the user knows which they are
looking at.

If the user wants to change a source that is already working — a different vault, a different
account — do that on request. Do not volunteer it.

An unselected source is skipped. It is not recorded as disabled, and nothing is written for it.
Choosing not to set something up is indistinguishable from not having it, and that is deliberate.

## Step 5 — set up each chosen source

OAuth flows and `gh auth login` are interactive and browser-bound. Do what can be done, hand the rest
over with exact instructions, wait, then re-probe.

### github — a guided install

Detect each step and perform only the missing ones, in this order.

```bash
gh --version            # present? then skip to auth
brew --version          # else is Homebrew present?
```

If Homebrew is missing, **offer the install line rather than running it unannounced** — it is a large
change to the machine and the user should choose it:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then:

```bash
brew install gh
gh auth login          # choices: GitHub.com, HTTPS, login with a web browser
gh auth setup-git
gh auth status
```

**`gh auth setup-git` is not optional.** Without a credential helper, background refreshes of a
private marketplace lose their credentials and updates stop silently — no error, just a plugin that
never changes again.

From `gh auth status`, **name the active account, and say if more than one is signed in.** A wrong
active account returns empty GitHub results rather than an error, which reads as "nothing was written
down" instead of "you are looking at the wrong org".

### twenty — a guided remote setup

The instance is remote, so on a fresh machine there is nothing to discover locally and no amount of
searching will find it. This is the source that most often ends up permanently and silently absent,
which is why it is worth walking through.

1. Ask for the **base URL** of the Twenty instance.
2. Point the user at **Settings → APIs & Webhooks** in Twenty to generate an API key.
3. Ask where to keep it, defaulting to `~/.env`.

**Refuse a path inside a git repository.** Claude Code's working directory is usually a checkout, so
`.env` in the folder in hand is the likeliest answer the user gives and the likeliest key to be
committed and pushed:

```bash
if git -C "$(dirname "$env_file")" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "inside a git work tree - refuse and ask for a path outside it"
fi
```

Say why in one line — a key written inside a repository gets committed and pushed sooner or later —
and ask for somewhere outside it. `~/.env` is the suggestion.

4. Write the two lines, **replacing them if they are already in the file**, and lock the file down:

```bash
umask 077
tmp="$env_file.usher.tmp"
grep -v '^TWENTY_BASE_URL=' "$env_file" 2>/dev/null | grep -v '^TWENTY_API_KEY=' > "$tmp"
printf 'TWENTY_BASE_URL=%s\n' '<the url>' >> "$tmp"
printf 'TWENTY_API_KEY=%s\n' '<the key>' >> "$tmp"
mv "$tmp" "$env_file"
chmod 600 "$env_file"
```

**Never append a second `TWENTY_API_KEY=` line to a file that already has one.** Both this skill and
`usher-twenty` read the value with `sed -n 's/^TWENTY_API_KEY=//p' … | head -1` — the **first** match
wins. An appended key is therefore never read: the stale one keeps answering, the Step 6 re-probe
returns the same `401`, and the file is now holding two secrets instead of one. That `head -1` is the
contract to conform to, not a bug to route around, so a rewrite that turns this back into `>>` puts
the repair path back where it was. Stripping the old lines first also makes this correct when the
variables are absent, so there is no second code path to get wrong.

**Say this to the user plainly, before running it:** those `printf` lines put the key in clear text on
a command line, so it lands in the shell history of whatever runs it and is visible to anything
watching the process list for the moment it runs. There is no way to write the file without the key
passing through somewhere. The `chmod 600` is therefore not optional — it makes the file readable only
by its owner, and a `.env` at default permissions is world-readable on a shared machine. If the user
would rather not have the key on a command line at all, tell them to paste it into the file in their
own editor and give this skill only the path.

5. Record **only the path** in `twenty.env_file`, absolute, with `~` expanded.
6. Verify with a real request — the same one Step 2 probes with, and re-run there every time. Read
   the key out of the file into `$TWENTY_API_KEY` first, and pass **the variable**:

```bash
curl -sS --max-time 15 -o /dev/null -w '%{http_code}' \
  -H "Authorization: Bearer $TWENTY_API_KEY" "$TWENTY_BASE_URL/rest/people?limit=1"
```

**`$TWENTY_API_KEY`, never the literal key.** The command text is displayed before it runs, so
pasting the key in puts it on screen and in the transcript — for a value that was just written to a
`chmod 600` file precisely to keep it off both.

Read the result as a fix, not a verdict:

| Result | Means |
|---|---|
| `200` | Working. Report the base URL |
| `401` | The key is a JWT and it has expired. Regenerate it under **Settings → APIs & Webhooks** and **replace** the existing line as in step 4 — appending a second one changes nothing, because the first match is the one that gets read |
| A connection failure | The instance is not responding at that URL. Check the URL before touching the key |

Note the shape of that command: it writes the key into a header and discards the body with
`-o /dev/null`, printing only the status code. **Never replace it with something that prints the
response, and never echo the file back to check it.** Read the two variables out of the file the way
`usher-twenty` does — extracting only those lines, never sourcing the whole file, which usually holds
unrelated tokens for unrelated services.

### linear — connect, then confirm the workspace

Linear is reached through its MCP connector. Tell the user to add it under **`+` → Connectors** in
the desktop app and complete the browser flow — that flow cannot be driven from here. Then re-probe
with `get_workspace`.

**Name the workspace that answered, and ask whether it is the right one.** Say plainly why: a
connector pointed at the wrong workspace does not error. It answers from that workspace, cites it
correctly, and produces a confident wrong answer. On a machine where more than one organisation's
workspace is reachable, this is the likeliest way to be quietly wrong.

If the connector cannot be reached at all, say Linear is unavailable and that `/mcp` reconnects it.

### gdrive — connect, then record the account

Same route: **`+` → Connectors**, then the browser flow, which cannot be driven from here. Then probe:

```
search_files(query: "owner = 'me'", pageSize: 1, excludeContentSnippets: true)
```

The `owner` field of the returned file is the account that answered. **Tell the user which account it
is, ask whether that is the one Usher should read, and write their answer to `gdrive.account`.**

This matters because `usher-gdrive` enforces that value on every question: if the connector later
reaches a different account it refuses rather than degrades. Writing the wrong address here turns
every future Drive question into a refusal, so confirm it rather than assuming.

If the probe returns no file, the account cannot be confirmed — the user owns nothing in that Drive.
Say so, and do not write an account you did not observe.

### obsidian — offer the vaults that exist

Read Obsidian's own registry and offer what it lists. Never ask the user to type a path while there
is a list to pick from.

```
macOS:   ~/Library/Application Support/obsidian/obsidian.json
Linux:   ~/.config/obsidian/obsidian.json
Flatpak: ~/.var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json
Windows: %APPDATA%/Obsidian/obsidian.json
```

Its `vaults` object maps an id to `{path, ts, open}`. Treat a **missing** `open` key as closed — not
every entry has one.

**Stat each chosen path before writing it**, and do not record one that is not a directory — say
which, and ask again. A registry entry can outlive the vault it names.

Write the chosen vaults to `obsidian.vaults` as a list of absolute paths, with `~` expanded.

**The registry says which vaults *exist*; settings say which the user *wants searched*.** They are
different questions and only the second one is recorded here. **Never write a vault the user did not
pick**, however obvious it looks, and never write the whole registry as a shortcut.

If the registry is absent, ask for a path outright. Never guess one.

## Step 6 — re-probe and report

After the chosen sources have been set up, **run every probe again** and print the same table as in
Step 3, with the same columns, the same three statuses, and the same rule: a source is connected only
because a probe just succeeded.

Do not carry a row forward from the first table because nothing was changed for it — the point of the
second table is that it is observed, not remembered.

**Re-run means re-run the request, not re-read the setting.** In particular:

- **twenty** — re-read the credentials and issue the `curl` again. A row that says `connected`
  because a path is in `twenty.env_file` is exactly the stale verdict this table exists to prevent:
  the key is a JWT, it expires, and an expired key reported as connected is a wrong answer that
  looks right.
- **obsidian** — stat every path in `obsidian.vaults` again, including ones just written. A path the
  user typed or picked can still be wrong, and the moment to catch that is here, not on their first
  question.
- **linear**, **gdrive**, **github** — call `get_workspace`, `search_files` and `gh auth status`
  again and name what answered, even if the user said the browser flow succeeded. What they saw in a
  browser is not evidence that this machine can reach it.

For anything still not working, say what remains to be done in one line, and say plainly that the
rest of Usher works without it. A missing source narrows what can be answered; it does not break
anything.

## Settings safety — read, modify, write the whole object

Every skill in the plugin shares `~/.usher/settings.json`. **This is the only skill that writes
several keys in one run, which makes it the most dangerous writer in the repo.**

**Load the whole object from `~/.usher/settings.json`. Change only the keys for the sources being set
up. Write the whole object back.**

**Never construct a fresh file containing only what this run touched.** A run that sets up Twenty and
writes `{"twenty": {...}}` erases `obsidian.vaults` and `gdrive.account` for sources it was never
asked about — silently, with no error, and in a way nothing would notice until an answer came back
thin or a Drive question started refusing. That failure would look exactly like the sources having
never been configured, and the user would have no reason to connect it to this run.

So, in order, every time:

1. Read the existing file. If it does not exist, start from `{}`. If it exists but does not parse,
   **stop and say so** — do not overwrite a file whose contents could not be read.
2. Merge in only the keys for the sources being set up.
3. Write the whole merged object back.
4. Read it back and confirm the keys that were there before this run are still there.

The keys, and nothing else:

```json
{
  "obsidian": { "vaults": ["/absolute/path/to/Vault"] },
  "twenty":   { "env_file": "/absolute/path/to/.env" },
  "gdrive":   { "account": "someone@example.com" }
}
```

Store absolute paths with `~` expanded, and account names as plain strings. Never store a token, a
key, a file's contents, or a list of what was found.
