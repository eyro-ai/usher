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

### The settings file — rules, not suggestions

`~/.usher/settings.json` is shared by every skill. Five rules, because each is somewhere two skills
would otherwise disagree:

1. **One top-level key per source, named after the skill's suffix.** `usher-obsidian` owns
   `obsidian`. Not `obsidian_vaults`, not `vault`. Read and write only your own key.
2. **`version` is an integer at the top level.** A skill finding a version it does not recognise
   says so and stops; it does not assume a shape.
3. **Paths are absolute.** No `~`, no relative paths, no environment variables — expand when
   writing, store the result. Otherwise every skill must remember to expand, and the one that
   forgets fails looking exactly like "not found".
4. **Writing is read-modify-write on the whole object.** Load the file, change your key, write it
   all back. **Never write a file containing only your own key** — that destroys every other
   skill's settings, and yours will not be the skill that notices.
5. **A malformed file stops the skill.** Say the file is corrupt and where it is. Never overwrite to
   recover: it holds the only copy of decisions the user made.
