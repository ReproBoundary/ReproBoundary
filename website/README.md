# Website

This folder contains the ReproBoundary benchmark website. It is a **static
site**, meaning that a web server can send the files directly without running a
database or server-side application.

The published site is expected at
<https://reproboundary.github.io/>.

## Preview the site

From the repository root, run:

```bash
python3 scripts/build_site_data.py
python3 -m http.server 8765 --directory website
```

Open `http://127.0.0.1:8765` in a browser. Do not open `index.html` directly;
some browsers block local pages from loading the JSON data files.

## Task data

`scripts/build_site_data.py` reads the main 47-task CSV table and writes
`data/tasks.json`. JSON is a text format used to store structured data. Rebuild
this file after changing the main task table. Do not edit it by hand.

## Leaderboard data

`data/leaderboard.json` contains the frozen aggregate for the 47-task by
9-configuration main experiment. The table ranks configurations by strict
reproduction success and keeps execution, delivery, evaluator replay, strict
success, and unresolved counts separate.

Each row uses these fields:

- `model` and `agent`: the evaluated configuration;
- `execution`: count that completed required stages;
- `delivery`: count that passed delivery checks;
- `replay_match`: count whose retained result matched evaluator replay;
- `strict_success`: count that passed the frozen strict conjunction; and
- `unresolved`: count without enough evidence for a strict terminal verdict.

The public provenance file is
`../results/LEADERBOARD_FROZEN_20261011.json`. Do not add PGap, runtime, or
token aggregates without a frozen end-to-end aggregation path.

## Manuscript-derived sections

The construction pipeline, benchmark comparison, failure taxonomy, workflow
stage analysis, and representative cases are adapted from the manuscript. The
web pipeline removes resource-scale labels and updates the release summary to
the verified public inventory. Numerical workflow counts use the post-freeze
stage ledger; they are not substituted for frozen strict results.

## Result submissions

The website does not accept file uploads. The Submit section specifies the six
required protocol deliverables, evidence directories, archive checksum, and
email metadata. The complete procedure is in `../docs/SUBMIT_A_RUN.md`.

## GitHub Pages

GitHub Pages hosts a static website from a GitHub repository. The workflow in
`.github/workflows/pages.yml` remains manual. Run `Deploy benchmark website`
only after Pages has been enabled for the repository.
