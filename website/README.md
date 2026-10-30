# Website

This folder contains the ReproBoundary benchmark website. It is a **static
site**, meaning that a web server can send the files directly without running a
database or server-side application.

The published site is expected at
<https://endlesssalaxy.github.io/ReproBoundary/>.

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

`data/leaderboard.json` is empty until checked aggregate results are ready. An
**aggregate result** combines results from a fixed set of runs, for example the
success rate of one model-agent setting across all tasks.

Each future row uses these fields:

- `configuration`: model-agent setting;
- `execution`: number or rate of runs that completed required stages;
- `delivery`: number or rate of runs that submitted the required files;
- `replay_agreement`: number or rate whose submitted metric matched an
  independent evaluator rerun;
- `strict_success`: number or rate that passed all required checks; and
- `pgap`: the performance gap between a reproduced metric and the value
  reported by the source paper.

Publish only values derived from a fixed set of runs whose source records have
been checked.

## Result submissions

The website does not accept file uploads. The Submit section opens an email to
`fanjinz@ruc.edu.cn` with the subject `ReproBoundary Result Submission`.
Change the address in `index.html` if the project contact changes.

## GitHub Pages

GitHub Pages hosts a static website from a GitHub repository. The workflow in
`.github/workflows/pages.yml` remains manual. Run `Deploy benchmark website`
only after Pages has been enabled for the repository.
