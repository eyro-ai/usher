# Getting started with Usher

You ask a question in plain English. Usher works out which of our systems holds the answer, looks
there, and tells you what it found with links you can check.

No jargon needed. You will type a few commands, and each one is explained. Budget **30 minutes**,
most of it waiting for downloads.

---

## Before you start — three things to ask for

You cannot finish without these, so ask now and carry on reading while you wait.

| Ask | Who from | Why |
|---|---|---|
| Access to the **eyro-ai** GitHub organisation | whoever runs GitHub | Usher itself lives in a private repository there |
| An invite to our **Linear** workspace | your manager | So it can answer questions about work |
| The **Twenty CRM** address and an API key | whoever set up Twenty | Optional. Skip it and everything else still works |

If you only have the first one, keep going. Usher works with whatever it can reach and stays quiet
about the rest.

---

## Step 1 — Install Claude Code

Usher is not an app you open. It runs inside **Claude Code**, which is a chat window in your
terminal.

Open **Terminal** (press `⌘ Space`, type `terminal`, hit return). Paste this and press return:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

When it finishes, close Terminal completely (`⌘ Q`) and open it again. Then check it worked:

```bash
claude --version
```

You should see a version number. If you see `command not found`, close and reopen Terminal once more —
the installer adds Claude to your path and that only takes effect in a fresh window.

Now start it:

```bash
claude
```

It will ask you to sign in through your browser. Do that, and you will land in a chat prompt. **Leave
this window open** — the rest of the steps happen either here or in a second Terminal tab.

---

## Step 2 — Sign in to GitHub

**Do this before installing Usher.** Usher lives in a private repository, and the install will fail
with a confusing error if GitHub does not know who you are yet.

Open a second Terminal tab (`⌘ T`) and install the GitHub command-line tool:

```bash
brew install gh
```

If that says `command not found: brew`, install Homebrew first — it is the standard way Macs install
developer tools:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow its final instructions (it will print two commands to run), then try `brew install gh` again.

Now sign in:

```bash
gh auth login
```

Choose **GitHub.com**, then **HTTPS**, then **Login with a web browser**. Copy the code it shows,
press return, and paste the code in the browser page that opens.

Check it worked:

```bash
gh auth status
```

You want to see your username and a tick. If it lists more than one account, note which is active —
that matters later.

---

## Step 3 — Install Usher

Back in your **Claude Code** window, type these two, one at a time:

```
/plugin marketplace add eyro-ai/usher
```

```
/plugin install usher@usher
```

Then restart Claude Code — press `⌘ Q`, open Terminal, run `claude` again.

To check it landed, type `/` and scroll the list. You should see several entries beginning `usher`.
There should be **five**: `usher`, and one each for Linear, GitHub, Obsidian and Twenty.

> **If you got `Repository not found`:** GitHub does not think you have access. Either your invite to
> the eyro-ai organisation has not arrived, or a different GitHub account is signed in. Run
> `gh auth status` and check. That error says "not found" rather than "no permission" on purpose —
> GitHub will not confirm a private repository exists to someone who cannot see it.

---

## Step 4 — Connect Linear

In Claude Code, type:

```
/mcp
```

Pick **Linear** from the list and follow the browser prompts. **When it asks which workspace, choose
`eyro`** — this is the one step where picking wrong gives you confidently wrong answers rather than
an error, so read that screen properly.

---

## Step 5 — Point it at your notes *(skip if you do not use Obsidian)*

If you keep notes in [Obsidian](https://obsidian.md), Usher can search them. Nothing to configure —
the first time you ask about your notes it will list the vaults it found and ask which to use. It
remembers your answer.

Your notes stay on your Mac. Nothing is uploaded, copied or indexed anywhere.

---

## Step 6 — Twenty CRM *(optional)*

If you were given a Twenty address and key, add them to your shell so Usher can find them:

```bash
echo 'export TWENTY_BASE_URL="the-address-you-were-given"' >> ~/.zshrc
echo 'export TWENTY_API_KEY="the-key-you-were-given"' >> ~/.zshrc
```

Close and reopen Terminal. **Treat the key like a password** — do not paste it into chat, a ticket or
a document.

---

## Ask your first question

In Claude Code, just ask. No command, no prefix:

> What is the status of the knowledge base project?

You should get real issues with identifiers like `EYR-56`, links you can click, and a last line such
as:

```
Searched: linear (12 results)
```

**That last line matters.** It tells you where the answer came from — and, more usefully, where it
did *not* look. If a source you expected is missing from it, that is your clue.

A few more to try:

| Ask | Where it looks |
|---|---|
| *Why was the deploy gate made read-only?* | GitHub — pull requests and the discussion in them |
| *What are my notes on positioning?* | Your Obsidian vault |
| *What do I know about Acme?* | Twenty CRM |
| *What do we know about onboarding?* | Everywhere at once |

Ask follow-ups in plain language. It keeps the thread.

---

## When something does not work

| What you see | What it means |
|---|---|
| `Repository not found` | Wrong GitHub account, or your eyro-ai invite has not arrived. Run `gh auth status`. |
| Fewer than five `usher` entries | An older version is installed. Run `/plugin marketplace update usher` then `/plugin update usher`, and restart. |
| GitHub questions return nothing, no error | A different GitHub account is active. `gh auth status` will show which. |
| Answers about the wrong company's work | Linear is connected to the wrong workspace. Run `/mcp`, reconnect Linear, choose `eyro`. It sometimes takes two attempts. |
| "Nothing found" for something you know exists | Try naming it more specifically. Two vague searches usually mean it is somewhere Usher cannot reach yet. |

If a question gets no useful answer twice, the source may simply not be connected yet. Check the
`Searched:` line.

---

## What it cannot do yet

**Google Drive and Notion are not built.** Questions about meeting transcripts or documentation in
those places will come back empty. That is not a fault, and Usher will not pretend otherwise.

**It only reads.** Usher never creates, edits or deletes anything — no issues, no notes, no
pull requests, no CRM records. It cannot change your work by accident.

**It sees exactly what you see.** Every source is queried with your own account, so Usher can never
show you something you would not have access to yourself. Equally, it cannot see a project you have
not been invited to.

---

## Two habits worth forming

**Read the `Searched:` line.** It is the difference between "there is nothing" and "it did not look
there".

**Ask in your own words.** It is not a search box. *"What did we decide about pricing and why?"*
works better than `pricing decision`, because the reasoning usually lives in a discussion rather
than a title.
