# ReproBoundary website

The benchmark homepage is a dependency-free static site suitable for GitHub
Pages. Serve this directory with any static HTTP server; loading `index.html`
directly will not load the JSON data in browsers that block local `fetch`.

```bash
python3 scripts/build_site_data.py
python3 -m http.server 8765 --directory website
```

`scripts/build_site_data.py` derives `data/tasks.json` from the frozen 47-task
inventory. Do not edit the generated task file by hand.

`data/leaderboard.json` is intentionally empty. Future rows must use the six
display fields already declared in `app.js`: `configuration`, `execution`,
`delivery`, `replay_agreement`, `strict_success`, and `pgap`. Publish only
aggregates derived from a frozen, provenance-checked cohort.

The Pages workflow is manual while the repository remains private. Run
`Deploy benchmark website` after Pages has been enabled for the repository.
