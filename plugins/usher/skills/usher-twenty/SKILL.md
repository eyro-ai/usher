---
name: usher-twenty
description: Answer questions about the people and organisations you know - who someone is, how you know them, what they do, what they can help with - and about companies, opportunities and the conversation notes attached to them. Use when a question names a person outside the team, a company, a customer, an account or a deal. Triggers on "who do I know who", "how do I know", "what does X do", "who works at", "what happened with <customer>", "where did the deal land", "what is the history with", and on any mention of a contact, an account or an opportunity. Not for issue status or who owns internal work - those belong to Linear. Not for the user's own notes - those belong to Obsidian.
---

# usher-twenty

Answers from a self-hosted Twenty CRM, reached over HTTP with `curl` under the workspace API key.
Nothing is copied or stored.

## Read only

Never send `POST`, `PATCH`, `PUT` or `DELETE` to `/rest/*`. Never send a GraphQL `mutation`. Never
touch `/metadata` at all - that surface changes the workspace schema, and no question this skill
answers needs it.

The key grants full write access to every record in the workspace, and Twenty does not distinguish a
read key from a write one. There is no API-side guard. This boundary exists only here. Usher reads.

## Never expose the key

Never echo `$TWENTY_API_KEY`, never run a command whose displayed output would contain it, and never
write it into `~/.usher/settings.json` or anywhere else. It is read at query time, used in a header,
and forgotten.

## Reaching Twenty

Two values are needed - a base URL and an API key. Look in this order and stop at the first that
yields both.

**1. The environment.** If `$TWENTY_BASE_URL` and `$TWENTY_API_KEY` are both set, use them.

**2. A `.env` recorded in settings.** Read `~/.usher/settings.json` and take `twenty.env_file`, an
absolute path to a file holding both variables. Extract only those two lines - never source the
whole file, which usually holds unrelated tokens for unrelated services:

```bash
env_file=<the path from settings>
TWENTY_BASE_URL=$(sed -n 's/^TWENTY_BASE_URL=//p' "$env_file" | head -1 | tr -d "\"'")
TWENTY_API_KEY=$(sed -n 's/^TWENTY_API_KEY=//p' "$env_file" | head -1 | tr -d "\"'")
```

**3. Ask, once - but only if there is something to offer.** Look for candidates:

```bash
grep -l '^TWENTY_BASE_URL=' ~/.env ~/*/.env ~/Projects/*/.env 2>/dev/null || true
```

If that finds files, let the user pick one rather than asking them to type a path. If it finds
nothing, Twenty is not set up on this machine: say nothing was found and stop. Do not ask for a path
outright, do not guess one, and do not read a file the user did not name.

Then write the choice into `~/.usher/settings.json` under `twenty.env_file`, and do not ask again.

**Write it as read-modify-write on the whole file.** Load the existing JSON, change only the
`twenty` key, write the whole object back. Never write a file containing just your own key: the file
is shared with every other skill, and replacing it wipes their settings - silently, and not in a way
this skill would ever notice. Store the path absolute; expand `~` before writing.

**Store the path, never the key.** The API key is a JWT and it expires. Reading it fresh from its
own home on every question is the point, not an inefficiency - a copy in settings would go stale and
then fail as though the instance were down.

## Before answering

Make the search call below and read the HTTP status. Turn a failure into a fix, never into a guess:

| Response | Say, then stop |
|---|---|
| `401` | `twenty(unavailable) - the API key is a JWT and has expired; regenerate it under Settings -> APIs & Webhooks` |
| Connection refused, or a timeout | `twenty(unavailable) - the instance at <base URL> is not responding` |

Never describe a record you have not read.

## Choosing what to search

Twenty has one good primitive: a ranked search across every object at once. Reach for it first. Fall
back to per-object filters only when it comes back empty, or when the question is field-shaped.

```bash
curl -sS --max-time 15 -X POST "$TWENTY_BASE_URL/graphql" \
  -H "Authorization: Bearer $TWENTY_API_KEY" -H 'Content-Type: application/json' \
  -d '{"query":"query S($s:String!){search(searchInput:$s,limit:20){edges{node{recordId objectNameSingular label tsRankCD}}}}","variables":{"s":"<terms>"}}'
```

Each hit carries `objectNameSingular` (`person`, `company`, `note`, `opportunity`, `task`), a
`label`, and a `recordId`. Fetch only the records you will actually cite.

| The question is about | Then |
|---|---|
| Who someone is, how you know them, what they can help with | `GET /rest/people/<id>?depth=1` |
| A company, or who is there | `GET /rest/companies/<id>?depth=1` |
| A deal | `GET /rest/opportunities/<id>?depth=1` - `stage`, `amount`, `closeDate` |
| What was said, or the history with someone | the notes attached to them - see below |
| A field-shaped question: everyone in a city, everyone with a skill | `GET /rest/people?limit=20&filter=location[ilike]:%Berlin%` |

The plural in a REST path is Twenty's own: `person` -> `people`, `company` -> `companies`,
`opportunity` -> `opportunities`, `note` -> `notes`, `task` -> `tasks`.

`depth=1` returns a record's relations in the same call - a person's `company`, and `noteTargets`,
which carries a `noteId` for every note attached to them. Fetch the note itself with
`GET /rest/notes/<noteId>`: its text is `bodyV2.markdown` and its `title` is what search matched.

A person carries more than a name. `metAt` and `metThrough` say how the user knows someone;
`skills`, `canHelpWith`, `lookingFor` and `interests` are what "who do I know who..." questions are
actually asking about; `context` is free text about the relationship.

Widen the terms once if the first search is empty. Two empty searches mean it is not in the CRM.

## Not this skill's job

Issue status, who owns a piece of internal work, what is in a cycle - those are `usher-linear`'s,
even when the question names a person. "Who owns billing" is about work; "who do I know who knows
billing" is about people. If a question is about the state of internal work, say so and stop rather
than searching.

The user's own notes are `usher-obsidian`'s. A note here is a captured conversation attached to a
person; a note in the vault is the user's own thinking. Do not answer for the other.

## Answering

- **Cite the record, not just a link.** `Alex Rivera - Acme, met at Web Summit 2025` is checkable in
  a way a bare URL is not. The link is `<base>/object/<objectNameSingular>/<recordId>`.
- **Quote a note rather than summarising it.** These are captured conversations; the wording is the
  evidence. Give the note's title and date alongside the quote.
- **Say when they were last in contact.** `lastContactAt` turns a stale record into a dated one, and
  a CRM record is often older than it reads.
- **Cap at 20 results.** A list of everyone matching a word is not an answer.
- **End with exactly one line:** `Searched: twenty (<n> results)` - including when the answer is
  nothing found.
- If nothing matched, say so plainly. Do not reconstruct a relationship from a name, a company, or
  what you would expect to be there.
