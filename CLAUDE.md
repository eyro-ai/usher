# Working in this repo

## Git

Private repo under `eyro-ai`. Pushes and pulls need the `yurysukhoverkhoveyro` account, and concurrent sessions flip `gh`'s active account — so scope credentials per command instead of switching:

```bash
TOKEN=$(gh auth token --user yurysukhoverkhoveyro)
git -c credential."https://github.com".helper= \
    -c credential.helper='!f(){ echo username=yurysukhoverkhoveyro; echo password='"$TOKEN"'; }; f' \
    push origin <branch>
```

Wrong account gives `Repository not found`. That is an identity error, not a bad remote — GitHub returns 404 rather than 403 so it doesn't leak the repo's existence.

## Shared state between sessions

Two things are global to the machine, not to a session, and a concurrently-running session for
another company will take them:

- **The `gh` active account** — hence the per-command recipe above.
- **The Linear MCP connector's workspace.** It is machine-global, so a session working on a
  different organisation can point it elsewhere. **Always call `get_workspace` and check the
  name before trusting a Linear answer** — a connector on the wrong workspace answers
  confidently from it, cites correctly, and emits a normal `Searched:` line.

## The eval

```bash
python3 evals/run_routing.py     # ~25 min: one claude session per fixture
claude plugin validate . --strict
```

Run it once. It is slow because each fixture is a real session.

It asserts on which `Skill` tool call fired, never on answer text — a skill can be told to print `Searched: linear`, but it cannot fake being invoked.

**It verifies routing only.** A skill fires whether or not its source can answer, and headless sessions cannot reach the MCP connectors at all (a probe with Linear's tools allow-listed returns no tools). Retrieval has to be checked interactively.

Two traps:

- **Never edit a fixture to match observed behaviour.** Fix the skill's `description` — that is what dispatch matches on. A fixture edited to pass measures nothing.
- A fixture can fail because a *different* skill won the question — another skill installed on the machine may trigger on the same unscoped phrasings as `usher`. The harness filters to `usher-*`, so that case renders as `none` — check before assuming the router is broken.

`claude plugin eval` is early access and unavailable on this account; it silently produces nothing.

## Writing a source skill

- **Read-only, always.** Never call a mutating tool. Linear's OAuth grant includes write access — the boundary exists only in the skill's text.
- **Never hardcode an MCP tool prefix.** Both `mcp__plugin_linear_linear__*` and `mcp__claude_ai_Linear__*` occur, depending on how a teammate installed the connector. Name tools bare: `list_issues`, `get_workspace`.
- End every answer with `Searched: <source> (<n> results)`, including when nothing was found.
- A source that isn't installed is **invisible** — not named, not apologised for.

## Known gap — `usher-linear` does not verify the workspace

The skill calls `get_workspace` before answering, but only to check Linear is *reachable*. It never
checks *which* workspace it reached.

With a connector pointed at the wrong company — which happens, see above — the skill answers from
that company, cites its issues correctly, and ends with a normal `Searched: linear (n results)`.
Nothing in the output reveals the mistake. Not an error: a wrong answer that looks right, which for
a knowledge base spanning two companies on one machine is the worst available failure mode.

Fix when picking this up: have each source skill assert its expected workspace/org and refuse if it
does not match, rather than only checking reachability. The same applies to every source skill still
to be written.

## Layout

`docs/specs/` holds design; `docs/plans/` holds implementation plans; `docs/decisions.md` records
only the decisions that reversed or discarded a named alternative. Deliberately not namespaced by
whichever tool authored them — a plugin's name means nothing to someone reading this repo later.

**Read `docs/decisions.md` before proposing a settings file, a permission model, a stored index, or
a hardcoded org.** Each has been tried and rejected here, with reasons, and one of them was
reversed twice.

## Decided against — don't reintroduce without reading why

No `usher-setup` skill: whichever skill needs a value asks for it on first use and writes it to
`~/.usher/settings.json` itself. Nothing to run before a first question.

Settings exist only where discovery cannot express intent — see
[`docs/decisions.md`](docs/decisions.md) for why, and why that reversed twice.

### This file is not loaded at runtime

The plugin ships `plugin.json` and the `SKILL.md` files — nothing else. Skills run from
`~/.claude/plugins/cache/`, invoked from wherever the user happens to be, which is usually not this
repo. **So this file is for whoever writes a skill; it never reaches a running one.**

Any rule a *running* skill must obey has to be in its own `SKILL.md`. Read-only, the `Searched:`
line, and the settings-write mechanic below are all repeated in each skill that needs them, and that
duplication is deliberate.

### Touching the settings file

`~/.usher/settings.json` is shared by every skill. Load it, change your own key, write the whole
object back — **never write a file containing only your own key**, or you wipe another skill's
settings and yours will not be the one that notices. Store paths absolute.
