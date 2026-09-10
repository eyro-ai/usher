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
find ~/.claude/plugins -type d -path '*/usher/skills/usher-*' -maxdepth 6 2>/dev/null
```

The result of this step is the set of sources that exist on this machine. **Never name a source that
is not in it** — not in a table, not as a suggestion, not as something that could be added. A source
whose skill is not installed is invisible, not missing.

## Step 2 — probe each one

Probe every discovered source before asking the user anything. They choose against what is true, not
against a blank list.

| Source | Probe | Report |
|---|---|---|
| linear | `get_workspace` | the workspace name |
| gdrive | `search_files(query: "owner = 'me'", pageSize: 1)` | the `owner` field — the account that answered |
| github | `gh auth status` | the **active** account, and whether others are signed in |
| obsidian | `obsidian.vaults` in `~/.usher/settings.json` | which vaults are recorded |
| twenty | `$TWENTY_BASE_URL` and `$TWENTY_API_KEY`, else `twenty.env_file` in settings | the base URL, never the key |

**Refer to MCP tools by their bare name** — `get_workspace`, `search_files` — never with an MCP
prefix. The prefix differs between a plugin-installed connector and a claude.ai one, and hardcoding
either breaks the other.

If a discovered source is not in this table, read its own `SKILL.md` to learn what it needs, and
probe with the cheapest read it describes. Do not guess a probe.

## Step 3 — show what is true

One row per source. Connected or not, **and the account, workspace or org that answered**.

A tick alone is not enough. A green Linear pointed at the wrong workspace is the failure this whole
system fears most: it answers confidently, cites correctly, and is wrong, and nothing in the output
looks unusual. The account name is the only thing that catches it, so it goes in the table every
time.

```
| Source   | Status       | Reached                        |
|----------|--------------|--------------------------------|
| linear   | connected    | workspace "Eyro"               |
| gdrive   | connected    | someone@example.com            |
| github   | connected    | active account: someuser       |
| obsidian | not set up   | no vaults recorded             |
| twenty   | not set up   | no base URL found              |
```

**A source is reported working only because a probe succeeded.** Never because the user said they
clicked something, and never because a setting exists — a recorded path proves a path was recorded,
not that anything answers.

## Step 4 — ask which to set up

Offer **only the sources that are not working**, as a multi-select. Report the working ones and leave
them alone; do not re-ask about a source that just answered.

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
3. Ask where to keep it, defaulting to `~/.env`, and append the two lines:

```bash
echo 'TWENTY_BASE_URL=<the url>' >> "$env_file"
echo 'TWENTY_API_KEY=<the key>' >> "$env_file"
```

4. Record **only the path** in `twenty.env_file`, absolute, with `~` expanded.
5. Verify with a real request:

```bash
curl -sS --max-time 15 -o /dev/null -w '%{http_code}' \
  -H "Authorization: Bearer $TWENTY_API_KEY" "$TWENTY_BASE_URL/rest/people?limit=1"
```

Read the result as a fix, not a verdict:

| Result | Means |
|---|---|
| `200` | Working. Report the base URL |
| `401` | The key is a JWT and it has expired. Regenerate it under **Settings → APIs & Webhooks** and rewrite the line |
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

Write the chosen vaults to `obsidian.vaults` as a list of absolute paths, with `~` expanded.

**The registry says which vaults *exist*; settings say which the user *wants searched*.** They are
different questions and only the second one is recorded here. **Never write a vault the user did not
pick**, however obvious it looks, and never write the whole registry as a shortcut.

If the registry is absent, ask for a path outright. Never guess one.

## Step 6 — re-probe and report

After the chosen sources have been set up, **run every probe again** and print the same table as in
Step 3, with the same columns and the same rule: a source is connected only because a probe just
succeeded.

Do not carry a row forward from the first table because nothing was changed for it — the point of the
second table is that it is observed, not remembered.

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
