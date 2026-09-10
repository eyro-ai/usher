# Usher

Ask a question. Usher works out which system holds the answer, queries it in place, and cites what it found.

No index, no sync, no copy of your data.


## Install

Follow [`docs/onboarding.md`](docs/onboarding.md) — every step from
nothing installed to a first answer using the Claude Desktop app, about 30 minutes.

In a hurry, and `gh` already signed in to an account with `eyro-ai` access:

```bash
claude plugin marketplace add eyro-ai/usher
claude plugin install usher@usher
```

Use a terminal, not the app's plugin manager — the app clones over SSH and usually cannot reach your
key, which surfaces as a bare "Failed to add marketplace". Restart Claude afterwards.

Already installed? Type `set up Usher` and it walks you through connecting the rest interactively.

## Use

Just ask. The router picks the source.

```
> What's the status of the onboarding project?

EYR-56 — Implement Router skill — In Progress, Yury
https://linear.app/eyro/issue/EYR-56/implement-router-skill

Searched: linear (3 results)
```

## Sources

| Skill | Answers about | |
|---|---|---|
| `usher-linear` | Issue and project status, ownership, cycles | ready |
| `usher-gdrive` | Meetings, and all of Drive - docs, sheets, slides | ready |
| `usher-notion` | Docs, handbook | planned |
| `usher-obsidian` | Your own notes | ready |
| `usher-twenty` | People and companies you know, customers, deals | ready |
| `usher-github` | How something was built, and why | ready |

Every source skill is read-only — it never creates, edits or deletes anything in a source. Each runs
under your own credentials, so it sees exactly what you see — nothing more.

Alongside them, `usher-onboarding` connects the sources: say `set up Usher` and it probes what is
already working and configures the rest. It is the one skill that writes, and it writes only your own
settings file and the `.env` you name — never a source.

## Configuration

Nothing to run before a first question. A skill that needs a value asks for it then, and remembers the answer in `~/.usher/settings.json`.

Values are discovered where they already live — the GitHub org from `gh`, the Linear workspace from the connector, candidate Obsidian vaults from Obsidian's own registry. But discovery answers *what exists*, not *what should be searched*, so the settings file records the decision: which vaults to read, and which `.env` holds Twenty's credentials. Secrets are never copied into it — Twenty's API key is a JWT that expires, so it is read from its own home on every question.
