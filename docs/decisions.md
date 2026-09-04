# Decisions

Only decisions that **reversed, or discarded a named alternative**. If the current state would look
arbitrary without the history, it belongs here. Everything else lives in the spec.

Newest first.

---

## `usher-twenty` reads its credentials at query time and stores only a path

Rejected: discovery from the environment alone, which is what the spec said. Also rejected: asking
for the key on first use and storing it.

`TWENTY_BASE_URL` and `TWENTY_API_KEY` are not in the environment on the machine this was built on —
they live in a `.env` belonging to a different project. Environment-only discovery would therefore
make the source *permanently* absent under "a source that cannot answer is simply absent": silently,
and correctly by the rule, which is the worst way to be unavailable.

Storing the key was worse. Twenty's key is a JWT and expires, so a copy in `~/.usher/settings.json`
goes stale and then fails as a 401 — indistinguishable from the instance being down, and repaired in
the wrong place.

So settings record the **path** to the file holding the key, and the key is read from it on every
question. The two `TWENTY_*` lines are extracted individually rather than the file sourced, because
such a file usually holds unrelated tokens for unrelated services.

*Would reopen it:* Twenty issuing non-expiring or per-user keys, or the values moving into the
environment for real.

## Settings exist, but only where discovery cannot express intent

**Reversed twice.** Now: `~/.usher/settings.json`, written by whichever skill needs a value.

1. *Original*: a `settings.json` written up front by a `usher-setup` skill.
2. *Cut*: both removed. Every value seemed discoverable from an authoritative source — the Obsidian
   vault path from Obsidian's own registry, Twenty's URL from the environment, the GitHub org from
   `gh`. A stored value goes stale the way a cached issue status does.
3. *Restored*: Obsidian broke the argument. Its registry lists every vault the user has ever
   opened — including another company's — and the `open` flag reflects what happens to be open, not
   intent. **Discovery answers what exists, never what should be searched.**

The synthesis: discovery supplies *candidates* when a skill asks; settings record the *decision*.
`usher-setup` stayed dead — a skill that needs a value asks for it and writes it, so nothing has to
be run before a first question.

*Would reopen it:* a source whose intent is genuinely discoverable, making its settings key dead weight.

## `usher-github` derives its owner instead of naming one

Rejected: `--owner eyro-ai` in the skill text, which is how it was first written.

The skill has to work for another organisation, so an org name cannot live in it. It now derives the
owner from the repository named in the question, else the repo in hand, else the single org
available — and asks if there are several.

The cost is visible: without a hardcoded scope, a wrong active account yields **empty results**
rather than another company's code. Safer than wrong, but not the same as correct.

*Would reopen it:* a source-skill pattern for asserting identity, which would make the derivation a
safety mechanism rather than the only one.

## Linear owns issue tracking; `usher-github` refuses status questions

Rejected: `usher-github` also searching GitHub issues.

Two skills answering "what's the status of X" means whichever fires first wins, and that can vary
between runs. We already have one such collision on this machine, between `usher` and another
installed skill, and it is unstable.

So `usher-github` is told to say so and stop when a question is about the *state* of work rather
than how it came to be — even when a GitHub issue exists for it.

*Would reopen it:* work tracked in GitHub issues that Linear genuinely does not know about.

## The eval asserts on tool calls, not answer text

Rejected: `claude plugin eval`, which is early access and produces nothing on this account. Also
rejected: parsing the `Searched:` line out of the answer.

A skill can be *instructed* to print `Searched: linear`. It cannot fake having been invoked. The
harness reads `Skill` tool_use events from `--output-format stream-json` instead.

Consequence to keep in mind: it verifies **routing only**. Headless sessions cannot reach the MCP
connectors, so retrieval always needs an interactive check.

*Would reopen it:* `claude plugin eval` becoming generally available.

## No permission model, no tiers

Rejected: a tiered access model, then ACL-derived permission classes, then both.

Everything runs under the user's own account, so each agent sees exactly what that person sees.
Seven decisions had chained off one premise — that a pocket recorder has no ACL to inherit — resting
on a requirement never confirmed: who besides the owner reads this.

*Would reopen it:* a deployment where Usher answers for someone other than the credential holder.

## Nothing is stored

Rejected: Notion as a knowledge store, then Google Drive, then storing at all.

Notion could not delete pages and its relations could not carry properties. Drive fixed both but the
deeper problem survived: any copy needs syncing, dedup, and staleness handling, and every source
already has search. Querying in place does not solve those problems — it means they never arise.

The cross-source edge table went with it. It came from a best-practices tangent, not a requirement,
and contradicted the purpose actually chosen: recall, not traceability.

*Would reopen it:* a question that no source can answer alone and that fan-out demonstrably fails.
