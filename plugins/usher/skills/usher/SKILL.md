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
