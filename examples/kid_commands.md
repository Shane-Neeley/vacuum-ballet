# Kid and agent command examples

Run these from the repository with `uv run vacuum-ballet`. The first group is
offline and safe to try while authentication is cooling down.

## Pretend performances

```bash
vacuum-ballet play failure
vacuum-ballet play too_fast
vacuum-ballet play confused
vacuum-ballet play victory
vacuum-ballet ask "make it go too fast"
vacuum-ballet ask "pretend you are stuck on a sock"
```

The last two are parsed into the local playground. No account, map, or device
connection is needed.

## Plan a real performance

```bash
vacuum-ballet preview circle 300 700 --center-x 0 --center-y 0
vacuum-ballet ask "do a figure eight dance 300 mm 700 ms"
```

`ask` prints a plan and a preview. A parent or agent can then choose whether to
execute the bounded request:

```bash
vacuum-ballet ask "do a figure eight dance 300 mm 700 ms" --execute --confirm
```

The real dance uses map-frame coordinates. Previewing around `(0, 0)` shows the
shape only; an actual run uses the vacuum's current map position unless an
explicit centre is configured.

## Room cleaning

```bash
vacuum-ballet --json rooms
vacuum-ballet clean-rooms 3 --confirm
```

Use the numeric `segment_id` returned by `rooms`. This avoids guessing which
map segment a spoken room name refers to.

## Structured agent requests

Read-only and simulator requests can be sent as JSON:

```bash
vacuum-ballet --json intent '{"action":"status"}'
vacuum-ballet --json intent '{"action":"play","scenario":"failure"}'
vacuum-ballet --json intent '{"action":"preview","pattern":"square","size":300,"beat_ms":500}'
```

Physical JSON requests must carry `"confirm": true`; the CLI applies the same
physical-action confirmation gate as the named commands.
