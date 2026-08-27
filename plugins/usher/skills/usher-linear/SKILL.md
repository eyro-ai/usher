---
name: usher-linear
description: Answer questions about work in Linear - issue and project status, who owns what, what is planned, what shipped in a cycle. Use whenever a question asks about the state of work rather than the reasoning behind it. Triggers on "what's the status of", "who owns", "what's planned", "what's in this cycle", "is X done", and on any mention of an issue identifier.
---

# usher-linear

Answers from Linear, through the Linear MCP connector, under the user's own account - so it sees
exactly the teams they can see. Nothing is copied or stored.

## Read only

Never call `save_issue`, `save_comment`, `save_project`, `save_status_update`, `delete_comment`, or
any other tool that changes Linear. The OAuth grant includes write access; this boundary exists only
here. Usher reads.

## Before answering

Call `get_workspace`. If it fails, say Linear is unavailable and that `/mcp` will reconnect it, then
stop. Never describe issues you have not read.

## Choosing what to search

The commonest mistake is answering a project question with issues, or the reverse - both return
something technically correct and useless.

| The question is about | Use |
|---|---|
| A specific piece of work, a bug, an assignment | `list_issues`, then `get_issue` for detail |
| An initiative, a theme, "what are we working on" | `list_projects`, then `get_project` |
| A time box - this cycle, next cycle, what shipped | `list_cycles`, then issues filtered to it |
| Who someone is, or what they own | `list_users`, then issues filtered by assignee |

Refer to these tools by their bare names. The MCP prefix differs depending on whether the connector
was installed as a plugin or through claude.ai, and hardcoding one breaks the other.

## Answering

- **Refetch every time.** Status, assignee and cycle change constantly. Never answer from earlier in
  the conversation, and never from memory.
- **Cite the identifier, not just a link** - `EYR-142 - In Progress, Ana` is checkable in a way a
  bare URL is not. Include the URL as well.
- **Cap at 20 results**, most recently updated first. A dump of every matching issue is not an answer.
- **Stamp it.** Status is a snapshot: say "as of now".
- **End with exactly one line:** `Searched: linear (<n> results)` - including when the answer is
  nothing found.
- If nothing matched, say so plainly. Do not describe work that might exist.
