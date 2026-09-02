---
name: usher-github
description: Answer questions about how something in the codebase was built and why - pull requests, review discussion, commits, and code. Use when a question asks how something is implemented, why the code looks the way it does, what changed in a pull request, or when something shipped. Triggers on "how was X implemented", "why does this code", "what changed in", "when did X ship", "where is X in the code", and on any repository, file or pull request reference. Not for issue status, ownership or what is planned - those belong to Linear.
---

# usher-github

Answers from GitHub using the `gh` CLI under the user's own token, so it sees exactly the
repositories they can see. Nothing is copied or stored.

## Read only

Never run `gh pr create`, `gh pr merge`, `gh pr close`, `gh issue create`, `gh issue close`,
`gh release create`, `gh repo delete`, any `gh api` call with `-X POST`, `-X PATCH`, `-X PUT` or
`-X DELETE`, or any `git push`. `gh` carries the user's full write access; this boundary exists only
here. Usher reads.

## Not this skill's job

Issue status, who owns something, what is planned, what is in a cycle — those are `usher-linear`'s,
even when a GitHub issue exists for the same work. Answering them here would put two skills on the
same question. If a question is about the *state* of work rather than how it came to be, say so and
stop rather than searching.

## Before answering

Run `gh auth status`. If it fails, say GitHub is unavailable, that `gh auth login` will reconnect it,
and stop. Never describe a repository you have not read.

## Choosing what to search

Search pull requests before code. A pull request carries the intent and the argument; a code hit
carries only the line, and the line rarely says why.

| The question is about | Use |
|---|---|
| Why a change was made, what was debated or rejected | `gh search prs --owner <owner> "<terms>" --limit 20 --json number,title,url,repository,state` then `gh pr view <n> --repo <owner/repo> --comments` |
| Where something is implemented | `gh search code --owner <owner> "<terms>" --limit 20 --json path,repository,url` |
| When something landed, or who wrote it | `gh search commits --owner <owner> "<terms>" --limit 20 --json sha,commit,repository` |
| A pull request or file already named in the question | `gh pr view` or `gh api` directly — do not search for what you were handed |

### Deriving `<owner>`

Never search unscoped. Without an owner filter a search sweeps every organisation the token can
reach and returns another company's code.

Derive the owner; never hardcode one:

1. If the question names a repository, use that repository's owner.
2. Otherwise, if the working directory is a git repository with a GitHub remote, use its owner:
   `gh repo view --json owner --jq .owner.login`.
3. Otherwise list what is available — `gh api user/orgs --jq '.[].login'`. If there is exactly one,
   use it. If there are several, ask which before searching.

**Say which owner you searched.** Otherwise a reader cannot tell an empty result meaning "nothing
there" from one meaning "looked in the wrong place".

Widen the terms once if the first search is empty. Do not widen repeatedly — two empty searches mean
the answer is not here.

## Answering

- **Cite `repo#123` alongside the URL** - `usher#1` is checkable in a way a bare link is not. For
  code, cite `repo/path/to/file`.
- **Prefer the discussion over the diff.** What was debated, and what was rejected, lives in the
  review thread. The diff shows what landed, never why.
- **Cap at 20 results.** A list of every match is not an answer.
- **End with exactly one line:** `Searched: github (<n> results)` - including when the answer is
  nothing found.
- If nothing matched, say so plainly. Do not reconstruct a plausible history from the repository's
  name or your own expectations.
