# Usher

Ask a question. Usher works out which system holds the answer, queries it in place, and cites what it found.

No index, no sync, no copy of your data.

## Install

```
/plugin marketplace add eyro-ai/usher
/plugin install usher@usher
```

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
| `usher-obsidian` | Your own notes | planned |
| `usher-twenty` | Customers, deals | planned |
| `usher-github` | How something was built, and why | planned |

All read-only. Each runs under your own credentials, so it sees exactly what you see — nothing more.

## Configuration

None. Every value is discovered from where it already lives: the Obsidian vault path from Obsidian's own registry, Twenty's URL from the environment, the GitHub org from `gh`. A stored path goes stale the way a cached status does.
