# Usher

Ask a question. Usher works out which system holds the answer, queries it in place, and cites what it found.

No index, no sync, no copy of your data.

**New here, or on a fresh Mac?** Follow [`docs/onboarding.md`](docs/onboarding.md) — every step from
nothing installed to a first answer using the Claude Desktop app, about 30 minutes.

## Install

```
/plugin marketplace add eyro-ai/usher
/plugin install usher@usher
```

Those are terminal Claude Code. **In the Claude Desktop app `/plugin` is unavailable** — use
`claude plugin marketplace add eyro-ai/usher` and `claude plugin install usher@usher` from a shell,
or follow the onboarding guide above.

Private repo — check `gh auth status` first. The wrong account gives you `Repository not found`, which means wrong identity, not a bad URL.

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
| `usher-gdrive` | What was said in a meeting | planned |
| `usher-notion` | Docs, handbook | planned |
| `usher-obsidian` | Your own notes | ready |
| `usher-twenty` | People and companies you know, customers, deals | ready |
| `usher-github` | How something was built, and why | ready |

All read-only. Each runs under your own credentials, so it sees exactly what you see — nothing more.

## Configuration

Nothing to run before a first question. A skill that needs a value asks for it then, and remembers the answer in `~/.usher/settings.json`.

Values are discovered where they already live — the GitHub org from `gh`, the Linear workspace from the connector, candidate Obsidian vaults from Obsidian's own registry. But discovery answers *what exists*, not *what should be searched*, so the settings file records the decision: which vaults to read, and which `.env` holds Twenty's credentials. Secrets are never copied into it — Twenty's API key is a JWT that expires, so it is read from its own home on every question.
