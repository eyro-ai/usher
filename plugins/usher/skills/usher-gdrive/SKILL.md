---
name: usher-gdrive
description: Answer questions from Google Drive - what was said or decided in a recorded meeting, and the documents, sheets and slides kept there. Use when a question is about a meeting, a call, a recording, or a file that lives in Drive. Triggers on "what was said in", "what did we decide in the meeting", "what was discussed on the call", "find the spreadsheet", "what is in that deck", "which file has", and on any mention of a transcript, a recording, or a named file. Not for written-up documentation or the handbook - those belong to Notion. Not for issue status or ownership - those belong to Linear.
---

# usher-gdrive

Answers from Google Drive, through the Drive connector, under the user's own account - so it sees
exactly the files they can open. Nothing is copied or stored.

This skill covers **all of Drive**: documents, sheets, slides, PDFs, and the meeting transcripts
filed there. Not transcripts only.

## Read only

Never call `create_file`, `update_file`, `copy_file`, `trash_file` or `share_file`. Never call any
other tool that changes a file, its contents, its location or who can see it.

`share_file` deserves naming twice: it changes who can read something, and unlike a bad edit that
failure is invisible to the user and permanent for everyone else. The OAuth grant includes write.
This boundary exists only here. Usher reads.

Refer to every tool by its bare name. The MCP prefix differs depending on how the connector was
installed, and hardcoding one breaks the other.

## Before answering — confirm which account answered

**This matters more here than in any other source.** Meeting recordings land in *personal* Drives,
so a personal and a work account both plausibly hold the answer. Reaching the wrong one returns real
files, cites them correctly, and produces a wrong answer that looks entirely right.

So establish the account first, on every question:

```
search_files(query: "owner = 'me'", pageSize: 1, excludeContentSnippets: true)
```

The `owner` field of the returned file is the account that answered.

Then compare it with `gdrive.account` in `~/.usher/settings.json`:

| Situation | Do this |
|---|---|
| Settings has `gdrive.account` and it **matches** | Answer normally |
| Settings has `gdrive.account` and it **does not match** | **Refuse.** Say which account answered and which was expected, and that the Drive connector needs reconnecting to the expected one. Do not search |
| `gdrive.account` is missing | Tell the user which account the connector reached and ask whether that is the one Usher should read. Write their answer to settings, then continue |
| The probe returns no file at all | The user owns nothing in this Drive. Say the account could not be confirmed, name that plainly in the answer and in the `Searched:` line, and only then continue |

If the connector itself fails, say Drive is unavailable and that reconnecting it under
**Settings → Connectors** will fix it, then stop. Never describe a file you have not read.

### Writing the account to settings

**Read-modify-write the whole file.** Load the existing JSON from `~/.usher/settings.json`, change
only the `gdrive` key, write the whole object back. Never write a file containing just your own key:
the file is shared with every other skill, and replacing it wipes their settings — silently, and not
in a way this skill would ever notice.

```json
{ "gdrive": { "account": "someone@example.com" } }
```

Store the account address only. Never store a token, and never store file contents.

## Choosing what to search

`search_files` takes a structured query, not prose. Terms are combined with `and`, `or`, `not`, and
string values are single-quoted.

| The question is about | Use |
|---|---|
| A meeting, a call, a recording | `fullText contains '<terms>'`, then `read_file_content` with `includeComments: true` |
| A file the user names | `title contains '<name>'` — match the title before the body |
| A spreadsheet, a deck, a PDF | a `mimeType` clause, **not** the word in the title (see below) |
| Something a colleague sent them | `sharedWithMe = true and fullText contains '<terms>'` |
| What they worked on lately | `list_recent_files` with `orderBy: lastModifiedByMe` |
| A time period | `modifiedTime > '2026-01-01T00:00:00Z'`, RFC 3339, combined with the terms |

**Never put a file-type word inside `title contains` or `fullText contains`.** Searching
`title contains 'deck'` looks for the letters *d-e-c-k* in the name and misses every actual
presentation. Map the type to a `mimeType` clause instead:

| Say | MIME type |
|---|---|
| doc, document | `application/vnd.google-apps.document` |
| sheet, spreadsheet | `application/vnd.google-apps.spreadsheet` |
| deck, slides, presentation | `application/vnd.google-apps.presentation` |
| PDF | `application/pdf` |
| folder | `application/vnd.google-apps.folder` |

If the workspace files meetings under a `Meetings/` tree, `parentId` narrows to one folder — but
never assume that layout exists. Search the whole Drive first.

Widen the terms once if the first search is empty. Two empty searches mean it is not in Drive.

## Not this skill's job

**Written-up knowledge belongs to `usher-notion`.** The boundary is the artefact, not the topic:
Drive holds files, Notion holds documentation. A question about the handbook, or about where
something is *documented*, is Notion's even when a Drive file mentions it.

Issue status, ownership and what is planned are `usher-linear`'s. The user's own notes are
`usher-obsidian`'s.

## Answering

- **Quote the transcript, do not summarise it.** What someone actually said is the evidence; a
  paraphrase of a meeting is exactly the thing nobody can check.
- **Cite the title and the link**, and give the date it was last modified — a Drive file is often
  older than it reads.
- **Say which account you searched.** With personal and work Drives both plausible, a thin answer
  from one must be distinguishable from nothing existing anywhere.
- **Say when a hit was shared rather than owned**, so the user knows whose copy they are reading.
- **Cap at 20 results.** A list of every file containing a word is not an answer.
- **End with exactly one line:** `Searched: gdrive (<n> results in <account>)` — including when
  nothing was found.
- If nothing matched, say so plainly. Do not reconstruct what a meeting probably covered from its
  title, its attendees, or what you would expect to have been discussed.
