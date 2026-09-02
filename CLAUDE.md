# Working in this repo

**This file never reaches a running skill.** The plugin ships `plugin.json` and the `SKILL.md`
files — nothing else. Skills execute from `~/.claude/plugins/cache/`, invoked from wherever the user
happens to be, which is usually not this repo.

So everything here is addressed to **you, writing a skill** — never to a skill at runtime. Any rule
a running skill must obey belongs in its own `SKILL.md`, repeated in every skill that needs it. That
repetition is deliberate; it is not duplication awaiting a tidy-up.

## Git

Private repo under `eyro-ai`. Pushes and pulls need the `yurysukhoverkhoveyro` account, and concurrent sessions flip `gh`'s active account — so scope credentials per command instead of switching:

```bash
TOKEN=$(gh auth token --user yurysukhoverkhoveyro)
git -c credential."https://github.com".helper= \
    -c credential.helper='!f(){ echo username=yurysukhoverkhoveyro; echo password='"$TOKEN"'; }; f' \
    push origin <branch>
```

Wrong account gives `Repository not found`. That is an identity error, not a bad remote — GitHub returns 404 rather than 403 so it doesn't leak the repo's existence.

A history rewrite strands the marketplace clone on a commit that no longer exists; it needs
`git reset --hard FETCH_HEAD`, not a pull.

## Shared state between sessions

Two things are global to the machine, not to a session, and a concurrently-running session for
another company will take them:

- **The `gh` active account** — hence the per-command recipe above.
- **The Linear MCP connector's workspace.** A session working on a different organisation can point
  it elsewhere, and re-authorising may take more than one attempt.

Verify before trusting anything you test by hand. A connector on the wrong workspace answers
confidently from it, cites correctly, and looks entirely normal.

## The eval

```bash
python3 evals/run_routing.py     # ~25 min: one claude session per fixture
claude plugin validate . --strict
```

Slow because each fixture is a real session. It asserts on which `Skill` tool call fired, never on
answer text — a skill can be told to print `Searched: linear`, but it cannot fake being invoked.

**It verifies routing only.** A skill fires whether or not its source can answer, and headless
sessions cannot reach the MCP connectors at all. Retrieval has to be checked interactively, every
time, for every source skill.

**One run is not a gate.** Three runs have produced three different flake patterns. A green result
is one sample of a variable process.

Two traps:

- **Never edit a fixture to match observed behaviour.** Fix the skill's `description` — that is what
  dispatch matches on. A fixture edited to pass measures nothing.
- A fixture can fail because a *different* skill won the question. The harness filters to `usher-*`,
  so that renders as `none` — check before assuming the router is broken.
- **Never commit while a background task is running.** A scoped eval run swaps `routing.tsv` and
  restores it afterwards; committing in between captured the truncated file and destroyed 13
  fixtures, which shipped in a merged PR.

`claude plugin eval` is early access and unavailable on this account; it silently produces nothing.

## Writing a source skill

Your job is to write a `SKILL.md` that carries its own rules. Each of these must appear **in the
skill file**, because none of this text will be there when it runs:

| The skill must state | Why it cannot be assumed |
|---|---|
| That it is read-only, naming the forbidden operations | Tokens grant write. Linear's OAuth includes it; a vault is ordinary files. The boundary exists only in the text. |
| Tool names without an MCP prefix | Both `mcp__plugin_linear_linear__*` and `mcp__claude_ai_Linear__*` occur depending on how a teammate installed the connector. |
| That every answer ends `Searched: <source> (<n> results)` | It is how a reader learns what was *not* looked at. |
| That an uninstalled source is invisible — not named, not apologised for | The model will otherwise explain what it could not reach. |
| The settings-write mechanic, if it writes settings | Copy it from `usher-obsidian`; see below for why it must be inline. |

Then add fixtures to `evals/routing.tsv`, including at least one **guard** proving a neighbouring
skill still wins the questions it should.

## Settings

`~/.usher/settings.json` is shared by every skill. The rule — read-modify-write the whole object,
never write a file containing only your own key — lives in `usher-obsidian`'s `SKILL.md`, because
that is the only copy a running skill can read. Copy it into any skill that writes settings.

Settings exist only where discovery cannot express intent, and there is no `usher-setup` skill: a
skill that needs a value asks on first use and writes it. See [`docs/decisions.md`](docs/decisions.md)
for why, and why that reversed twice.

## Known gap — source skills do not verify the account they reached

They check that a source is *reachable*, never *which* account or workspace answered. Pointed at the
wrong company a skill answers from it, cites correctly, and emits a normal `Searched:` line — a
wrong answer that looks right, which for a knowledge base spanning two companies on one machine is
the worst available failure mode.

`usher-github` mitigates it accidentally: scoping searches to a derived owner yields *empty* results
on a wrong account rather than another company's code. Safer, not the same as correct.

The fix, when someone takes it: assert the expected workspace or org and refuse on mismatch. It
applies to every source skill still unwritten, so it is cheaper as a pattern than as five retrofits.

## Layout

`docs/specs/` holds design; `docs/plans/` holds implementation plans; `docs/decisions.md` records
only the decisions that reversed or discarded a named alternative. Deliberately not namespaced by
whichever tool authored them — a plugin's name means nothing to someone reading this repo later.

**Read `docs/decisions.md` before proposing a settings file, a permission model, a stored index, or
a hardcoded org.** Each has been tried and rejected here, with reasons, and one was reversed twice.

## Releasing

Bump `version` in **both** `plugins/usher/.claude-plugin/plugin.json` and the marketplace entry in
`.claude-plugin/marketplace.json`. Without it `/plugin update` sees no change and installs nothing —
a skill PR is not self-contained without its bump. This has been missed twice.
