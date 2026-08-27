#!/usr/bin/env python3
"""Routing eval - does each question dispatch to the expected skill?

Asserts on the Skill tool calls Claude actually makes, read from the
stream-json event log, rather than on any text a skill was told to print.
A skill can be instructed to claim it searched Linear; it cannot fake
having been invoked.
"""
import csv
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PLUGIN = HERE.parent / "plugins" / "usher"
FIXTURES = HERE / "routing.tsv"
TIMEOUT_SECONDS = 300


def skills_invoked(stream: str) -> set:
    """Skill names fired during the run, with the plugin prefix stripped."""
    fired = set()
    for line in stream.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == "Skill":
                name = block.get("input", {}).get("skill", "")
                fired.add(name.split(":")[-1])
    return fired


def ask(question: str) -> str:
    result = subprocess.run(
        [
            "claude",
            "--plugin-dir", str(PLUGIN),
            "-p", question,
            "--output-format", "stream-json",
            "--verbose",
        ],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    return result.stdout


def load_fixtures():
    rows = []
    with FIXTURES.open() as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if not row or row[0].startswith("#"):
                continue
            expected = row[1].strip()
            rows.append((row[0].strip(), set() if expected == "none" else {expected}))
    return rows


def main() -> int:
    failures = []
    fixtures = load_fixtures()

    for question, expected in fixtures:
        fired = skills_invoked(ask(question))
        # Only judge usher skills; an unrelated skill firing is not a routing error.
        fired = {s for s in fired if s == "usher" or s.startswith("usher-")}
        fired.discard("usher")  # the router itself is not a destination

        if fired == expected:
            print("PASS  " + question[:58])
        else:
            failures.append((question, sorted(expected), sorted(fired)))
            print("FAIL  " + question[:58])

    print("\n%d/%d routed correctly" % (len(fixtures) - len(failures), len(fixtures)))
    for question, expected, got in failures:
        print("\n  %s\n    expected: %s\n    fired:    %s"
              % (question, expected or ["none"], got or ["none"]))

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
