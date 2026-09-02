---
name: usher-obsidian
description: Answer questions from the user's own Obsidian notes - what they wrote, thought, or captured for themselves. Use when a question is about their own thinking rather than a shared system. Triggers on "what are my notes on", "what was I thinking about", "did I write anything about", "what did I note", "check my notes", and on any reference to a daily note or a zettel. Not for shared documentation or meeting records - those belong to Notion and Drive.
---

# usher-obsidian

Answers from the user's Obsidian vault, read from the local filesystem. Nothing is copied or stored
anywhere else.

## Never write

**Never create, edit, move, rename or delete a note.** Never write into the vault directory at all.

This prohibition matters more here than in any other source skill. Linear and GitHub are bounded by
what their APIs permit; a vault is ordinary files, and you hold the same write access the user does
over years of their personal notes. There is no API to stop you. Read only.

## Which vaults to search

Read `~/.usher/settings.json` and use `obsidian.vaults` - a list of absolute paths.

**If that key is missing, ask before searching.** Offer the vaults Obsidian already knows about as
candidates, so the user picks rather than types a path. Obsidian's registry lives at one of:

- macOS: `~/Library/Application Support/obsidian/obsidian.json`
- Linux: `~/.config/obsidian/obsidian.json`
- Flatpak: `~/.var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json`
- Windows: `%APPDATA%/Obsidian/obsidian.json`

Its `vaults` object maps an id to `{path, ts, open}`. Treat a **missing** `open` key as closed - not
every entry has one.

Then write the answer into `~/.usher/settings.json` under `obsidian.vaults`, and do not ask again.

**Write it as read-modify-write on the whole file.** Load the existing JSON, change only the
`obsidian` key, write the whole object back. Never write a file containing just your own key: the
file is shared with every other skill, and replacing it wipes their settings — silently, and not in
a way this skill would ever notice. Store the path absolute; expand `~` before writing.

The registry says which vaults *exist*; the settings say which the user *wants searched*. They are
different questions, and only the second one is yours to honour. Never search a vault that is not
in settings, even if the registry lists it.

If the registry is absent too, ask for a path outright. Never guess one.

## Searching

Use ripgrep. A vault of a few thousand notes searches in well under a second, so there is no index
to build and none should be built.

Always exclude `Files/`, `Attachments/` and `.obsidian/` - attachments are the bulk of a vault's
size and none of its text.

| The question is about | Do this |
|---|---|
| A topic | `rg -il "<terms>"` for candidate notes, then `rg -n -C2 "<terms>" <file>` for the passage |
| A note the user names | match the filename first - notes are usually titled by their topic |
| What connects to something | follow `[[wikilinks]]` out of the best hit, one hop only |
| A time period | scope to the daily-notes folder, which nests year then month (`2024/04 April/`) |

Widen the terms once if the first search is empty. Two empty searches mean it is not written down.

## Answering

- **Quote, do not paraphrase.** These are the user's own words; showing them is the point.
- **Cite the note path and the heading** the passage sits under, so they can open it.
- **Cap at 20 notes.** A list of every file containing a word is not an answer.
- **Say which vault you searched.** With vaults configurable, a thin answer from one vault must be
  distinguishable from nothing being written anywhere.
- **End with exactly one line:** `Searched: obsidian (<n> results in <vault name>)` - including when
  nothing was found.
- A note may be old. If the question is about what is true now rather than what they once thought,
  say when the note was last modified.
