# Getting started with Usher in Claude Cowork

Usher was built for Claude Code, which runs in a terminal. **Cowork is the version without a
terminal** — same Claude, same skills, but you work in a window instead of a command line.

Most of Usher works there. Which parts depends on one setting, so this guide starts by finding out
which one you have.

> **Read this first.** Everything below marked **`unverified`** is inferred from how Cowork is
> documented, not from someone having done it. If you are the first person through this guide, the
> checklist at the bottom is how you fix it for the next person.

---

## Step 0 — Which mode is your Cowork in?

Cowork can run your work in two places, and it decides what Usher can reach:

- **Cloud** — your session runs on Anthropic's servers. This is the default.
- **Local** — your session runs inside a protected space on your own Mac.

The difference matters for exactly one reason: **your Obsidian notes live on your Mac.** A cloud
session cannot see them. Nothing else about Usher depends on it.

Ask Cowork:

> Run: which gh rg && echo "---" && echo ${TWENTY_BASE_URL:-TWENTY_NOT_SET}

| What comes back | What it means |
|---|---|
| Paths for both, and your Twenty address | You are set up for everything. Go to Step 1. |
| Paths for both, `TWENTY_NOT_SET` | Everything except the CRM. Fine — Step 6 is optional. |
| `gh not found` or `rg not found` | Those tools are missing. See **If tools are missing** below. |
| It cannot run commands at all | You are in Claude Desktop, not Cowork. Usher needs Cowork or Claude Code. |

Keep that answer. It is the only thing that decides what to expect.

---

## Step 1 — Get access

Two things to ask for before anything else works:

| Ask | Who from |
|---|---|
| Access to the **eyro-ai** organisation on GitHub | whoever runs GitHub |
| An invite to our **Linear** workspace | your manager |

Usher lives in a private GitHub repository, so without the first one the install simply fails.

---

## Step 2 — Sign in to GitHub

Ask Cowork:

> Run: gh auth login — and walk me through it

It will need you to open a browser and paste a short code. Then confirm:

> Run: gh auth status

You want your username and a tick. If more than one account is listed, note which is **active** —
that decides which company's code Usher can see, and getting it wrong produces empty answers rather
than errors.

---

## Step 3 — Install Usher

> **`unverified`** — Cowork and Claude Code may install plugins differently. Claude Code uses a
> marketplace command; Cowork is documented as also accepting a plugin as a zip. Try the marketplace
> route first and fall back.

Ask Cowork:

> Install the plugin from eyro-ai/usher

If it asks for a marketplace command, this is the pair Claude Code uses:

```
/plugin marketplace add eyro-ai/usher
/plugin install usher@usher
```

If neither works, the fallback is to download the repository as a zip and install that — ask Cowork
to do it and it will know the current mechanism better than this document does.

To confirm it landed, ask:

> Which usher skills do you have?

You want **five**: the router plus Linear, GitHub, Obsidian and Twenty.

> **If you get `Repository not found`:** GitHub does not believe you have access. Either the eyro-ai
> invite has not arrived, or a different account is active. That message says "not found" rather
> than "no permission" deliberately — GitHub will not confirm a private repository exists to someone
> who cannot see it.

---

## Step 4 — Connect Linear

Linear is not reached through a command; it uses a connector you authorise once.

In Cowork, open your connector settings and connect **Linear**. **When it asks which workspace,
choose `eyro`.**

That step deserves care: it is the one place where choosing wrong gives you confident, correct-looking
answers about the wrong company, rather than an error.

---

## Step 5 — Your notes *(local mode only)*

**If your Cowork runs in the cloud, skip this.** Your vault is on your Mac and a cloud session cannot
reach it. Usher will simply say it found nothing, which is honest rather than broken.

**If you are in local mode**, there is nothing to configure. The first time you ask about your notes,
Usher lists the vaults it found and asks which to use, then remembers.

Your notes are never uploaded, copied or indexed. They are read where they sit.

> **`unverified`** — that Cowork's local mode can read a vault outside its working folder. It is
> documented as having broad read access, but nobody has confirmed it for Obsidian specifically.

---

## Step 6 — Twenty CRM *(optional)*

Only if someone has given you a Twenty address and API key.

> **`unverified`** — how environment values are set in Cowork. In a terminal they go in your shell
> profile; Cowork may offer its own settings for this. Ask Cowork where to put them.

**Treat the key like a password.** Do not paste it into a chat message, a ticket or a document.

---

## Ask your first question

No command, no prefix. Just ask:

> What is the status of the knowledge base project?

You should get real issues with identifiers like `EYR-56`, links you can open, and a final line:

```
Searched: linear (12 results)
```

**That line is the most useful part of any answer.** It says where Usher looked — and by omission,
where it did not. If a source you expected is missing from it, that is your answer about why the
reply looks thin.

More to try:

| Ask | Where it looks | Works in cloud mode? |
|---|---|---|
| *Why was the deploy gate made read-only?* | GitHub pull requests and their discussion | yes, once `gh` is signed in |
| *What do I know about Acme?* | Twenty CRM | yes, if the key is set |
| *What are my notes on positioning?* | Your Obsidian vault | **no** — local mode only |
| *What do we know about onboarding?* | Everywhere at once | partially |

---

## If tools are missing

If Step 0 said `gh not found` or `rg not found`, two of the sources cannot work — `usher-github`
needs `gh`, and `usher-obsidian` needs `rg` (ripgrep) to search your notes.

Ask Cowork:

> Install gh and ripgrep

It may be able to. If it cannot, Usher still works for Linear and Twenty, and will say plainly that
it found nothing for the others rather than guessing.

---

## When something does not work

| What you see | What it means |
|---|---|
| `Repository not found` | Wrong GitHub account, or the eyro-ai invite has not arrived. Check `gh auth status`. |
| Fewer than five usher skills | An older version is installed. Ask Cowork to update the plugin, then start a new session. |
| GitHub questions return nothing, no error | A different GitHub account is active. |
| Answers about the wrong company | Linear is connected to the wrong workspace. Reconnect it and choose `eyro`. It sometimes takes two attempts. |
| Notes questions always empty | Expected in cloud mode. Your vault is on your Mac. |

---

## What Usher cannot do

**Google Drive and Notion are not built.** Questions about meeting transcripts or documentation come
back empty by design, not by fault.

**It only reads.** It never creates, edits or deletes an issue, note, pull request or CRM record. It
cannot change your work by accident.

**It sees exactly what you see.** Every source is queried with your own account — so it can never
show you something you lack access to, and cannot see a project you were not invited to.

---

## For whoever tests this first

These are the claims this guide is guessing at. Confirming or correcting them turns this from
inference into instructions:

- [ ] Does `/plugin marketplace add eyro-ai/usher` work in Cowork, or is a zip the only route?
- [ ] Are `gh` and `rg` present by default? In cloud mode, in local mode, or neither?
- [ ] Can Cowork install them if missing?
- [ ] In local mode, can it read an Obsidian vault outside its working folder?
- [ ] Where do `TWENTY_BASE_URL` and `TWENTY_API_KEY` go in Cowork?
- [ ] Does `gh auth login` complete, given it needs a browser handoff?
- [ ] Do all five skills appear, and does the router dispatch to them as it does in Claude Code?
- [ ] In cloud mode, does `usher-obsidian` fail *cleanly* — saying it found nothing — or confusingly?

Delete this section once it is answered.
