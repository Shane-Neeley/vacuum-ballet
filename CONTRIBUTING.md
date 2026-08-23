# Contributing

Vacuum Ballet has a deliberately small public surface. New capabilities should
follow the same progression:

1. Add a pure planner or parser first.
2. Make the output inspectable as JSON.
3. Add mocked/offline tests.
4. Add an explicit confirmation gate before connecting it to a physical write.
5. Document one copyable example and the device assumptions.

## Local development

```bash
uv sync
uv run pytest
uv run vacuum-ballet --help
```

Normal tests never contact Roborock. The live connection test requires
`RUN_ROBOROCK_LIVE_TEST=1` and exported credentials; never put credentials or
verification codes in a commit, issue, pull request, log, or test fixture.

The project currently targets the public V1 capability shape in
`python-roborock`. Keep transport-specific details inside
`src/roborock_agent.py`; keep geometry, intent parsing, and playground
behavior network-free and independently testable.

## Pull requests

Please include:

- the user-facing problem and one runnable example;
- the safety boundary for any physical command;
- offline tests and documentation updates;
- the result of `uv run pytest` and `git diff --check`.

Small, focused changes are easier to review and safer to try with a real
vacuum.
