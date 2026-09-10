# Getting started with Usher

You ask a question in plain English. Usher works out which of our systems holds the answer, looks
there, and tells you what it found with links you can check.

No jargon needed. This guide uses **Claude Desktop** — the Mac app — so most of it is clicking.
There are a few commands, and each one is explained. Budget **30 minutes**, most of it waiting for
downloads.

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

## Step 1 — Install Claude

Download **[Claude for Mac](https://claude.ai/api/desktop/darwin/universal/dmg/latest/redirect)**.
One download works on every Mac, old or new.

Open the downloaded file, drag Claude into your Applications folder, and launch it. Sign in with your
account.

Then click the **Code** tab. That is Claude Code — the part that can reach our systems. Everything
below happens there.

---

## Step 2 — Set up your first session

Before you type anything, there are four settings in the prompt area. They matter more than they
look.

| Setting | Choose | Why |
|---|---|---|
| **Environment** | `Local` | Runs on your Mac, using your own accounts |
| **Project folder** | see below | Decides which GitHub organisation questions are scoped to |
| **Model** | the default | You can change it mid-conversation |
| **Permission mode** | `Manual` to start | Claude asks before running anything. Move to `Accept edits` once you are comfortable |

**The project folder is not cosmetic.** When you ask a question about code, Usher works out which
GitHub organisation to search from the folder you picked. Choose a folder containing one of our
repositories and it searches ours. Choose an unrelated folder and GitHub questions come back
**empty rather than wrong** — which is safer, but still not what you wanted.

If you have no repository checked out yet, pick any folder for now and name the repository in your
question instead: *"what changed in the usher repo recently?"*

---

## Step 3 — Sign in to GitHub

**Do this before installing Usher.** Usher lives in a private repository, and the install fails with
a confusing error if GitHub does not know who you are yet.

You need a terminal for this part. Claude Desktop has one built in — open the **Terminal panel**
beside the chat. (The macOS Terminal app works just as well: press `⌘ Space`, type `terminal`, hit
return.)

Install the GitHub command-line tool:

```bash
brew install gh
```

If that says `command not found: brew`, install Homebrew first — it is the standard way Macs install
developer tools:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow its final instructions (it prints two commands to run), then try `brew install gh` again.

Now sign in:

```bash
gh auth login
```

Choose **GitHub.com**, then **HTTPS**, then **Login with a web browser**. Copy the code it shows,
press return, and paste the code in the browser page that opens.

Then hand those credentials to git itself:

```bash
gh auth setup-git
```

Skipping this line mostly works — until Usher tries to update itself in the background, cannot prove
who you are, and quietly stops updating.

Check it worked:

```bash
gh auth status
```

You want to see your username and a tick. If it lists more than one account, note which is
**active** — that matters later.

---

## Step 4 — Install Usher

> **Do not use `/plugin`.** In the Mac app it answers `/plugin isn't available in this environment`.
> That command works only in the terminal version of Claude Code. Use one of the routes below
> instead.

**Route A — two commands.** You are already in the terminal from Step 3, so this is the short way:

```bash
claude plugin marketplace add eyro-ai/usher
```

```bash
claude plugin install usher@usher
```

`eyro-ai/usher` is the whole address — Claude finds the marketplace file inside the repository. The
`usher@usher` in the second command is *plugin@marketplace*: both happen to be called `usher`.

**Route A′ — the same thing from the plugin manager.** Click **+** next to the prompt box and choose
**Plugins**. You can add `eyro-ai/usher` and install from there without touching a terminal, if you
prefer clicking.

**Route B — paste it into your settings once.** Useful if you are setting up several machines. Open
`~/.claude/settings.json` and add these two keys alongside whatever is already there — do not replace
the file:

```json
"extraKnownMarketplaces": {
  "usher": { "source": { "source": "github", "repo": "eyro-ai/usher" } }
},
"enabledPlugins": {
  "usher@usher": true
}
```

Either way, **restart Claude** afterwards — quit with `⌘ Q` and open it again. Plugins only load at
startup.

To check it landed, type `/` in the prompt box (or click **+** → **Slash commands**) and look for
entries beginning `usher`. There should be **six**: `usher`, and one each for Linear, GitHub,
Obsidian, Twenty and Google Drive.

> **If you got `Repository not found`:** GitHub does not think you have access. Either your invite to
> the eyro-ai organisation has not arrived, or a different GitHub account is signed in. Run
> `gh auth status` and check. That error says "not found" rather than "no permission" on purpose —
> GitHub will not confirm a private repository exists to someone who cannot see it.

---

## Step 5 — Connect Linear

Click the **+** button next to the prompt box, choose **Connectors**, and pick **Linear** from the
list. Follow the browser prompts.

**When it asks which workspace, choose `eyro`.** This is the one step where picking wrong gives you
confidently wrong answers rather than an error, so read that screen properly.

You can review or disconnect it later under **Settings → Connectors**.

> Typing `/mcp` will not do this for you — in the Mac app, connectors are the **+** button.

---

## Step 6 — Connect Google Drive

Same place: **+** → **Connectors** → **Google Drive**. This is what answers questions about meetings,
recordings, and any document, sheet or slide deck kept in Drive.

**Sign in with the account that actually holds our files.** Meeting recordings often land in a
*personal* Drive rather than a work one, so if you have both signed in on this Mac, read the account
picker properly. The first time you ask a Drive question, Usher tells you which account it reached
and asks whether that is the one to use — say no if it names the wrong one, and reconnect.

Like Linear, the wrong account here does not produce an error. It produces real files from the wrong
place, cited correctly.

---

## Step 7 — Point it at your notes *(skip if you do not use Obsidian)*

If you keep notes in [Obsidian](https://obsidian.md), Usher can search them. Nothing to configure —
the first time you ask about your notes it will list the vaults it found and ask which to use. It
remembers your answer.

Your notes stay on your Mac. Nothing is uploaded, copied or indexed anywhere.

---

## Step 8 — Twenty CRM *(optional)*

If you were given a Twenty address and key, put them in a file called `.env` in your home folder:

```bash
echo 'TWENTY_BASE_URL=the-address-you-were-given' >> ~/.env
echo 'TWENTY_API_KEY=the-key-you-were-given' >> ~/.env
```

The first time you ask a question about people or customers, Usher will find that file and ask
whether to use it. Say yes and it remembers.

It stores **where the key lives, never the key itself** — Twenty's keys expire, and a stale copy
would fail in a way that looks like the server being down.

**Treat the key like a password.** Do not paste it into chat, a ticket or a document.

---

## Ask your first question

In the Code tab, just ask. No command, no prefix:

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
| *What did we decide on the partner call?* | Google Drive — meeting transcripts |
| *What do I know about Acme?* | Twenty CRM |
| *What do we know about onboarding?* | Everywhere at once |

Ask follow-ups in plain language. It keeps the thread.

---

## When something does not work

| What you see | What it means |
|---|---|
| `/plugin isn't available in this environment` | Expected in the Mac app. Use Route A or B in Step 4. |
| `Repository not found` | Wrong GitHub account, or your eyro-ai invite has not arrived. Run `gh auth status`. |
| Fewer than six `usher` entries | An older version is installed, or Claude has not restarted. Run `claude plugin update usher`, then quit with `⌘ Q` and reopen. |
| No `usher` entries at all | The plugin did not load. Check Step 4 ran without an error, then restart Claude. |
| GitHub questions return nothing, no error | Either a different GitHub account is active — `gh auth status` shows which — or your project folder points somewhere unrelated. See Step 2. |
| Answers about the wrong company's work | Linear is connected to the wrong workspace. **Settings → Connectors**, reconnect Linear, choose `eyro`. It sometimes takes two attempts. |
| "Nothing found" for something you know exists | Try naming it more specifically. Two vague searches usually mean it is somewhere Usher cannot reach yet. |

If a question gets no useful answer twice, the source may simply not be connected yet. Check the
`Searched:` line.

---

## What it cannot do yet

**Notion is not built.** Questions about the handbook or written-up documentation will come back
empty. That is not a fault, and Usher will not pretend otherwise.

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
