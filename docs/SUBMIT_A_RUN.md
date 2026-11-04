# Submit a ReproBoundary run

A leaderboard submission is an evidence package, not a reported metric or an
email message alone. Use the frozen task contract and retain enough evidence
for an independent metric replay.

## Package layout

Name the archive `<project-id>-<model>-<agent>.tar.gz`. Its single top-level
directory must contain:

```text
<project-id>-<model>-<agent>/
├── TARGET_EVALUATION.json
├── DATASET_SELECTION.json
├── pipeline-execution.json
├── reproduction-report.md
├── audit.json
├── metrics.json
├── security-attestation.json
├── evidence/
│   ├── evaluator/
│   ├── logs/
│   ├── outputs/
│   └── intermediates/
├── source/
└── SHA256SUMS
```

`TARGET_EVALUATION.json` must be the exact assigned contract. The other six
top-level deliverables must follow its `required_agent_output` schema and file
names. Do not invent a replacement schema.

## Required contents

- `DATASET_SELECTION.json`: frozen data scopes, stage budgets, selected-ID
  manifests and hashes, and the exact contract hash.
- `pipeline-execution.json`: every required stage, exact command strings, exit
  codes, start and finish times, inputs, outputs, evidence paths, and any
  protocol deviations.
- `reproduction-report.md`: executed work, code changes, observed results,
  failures, completed scope, and limitations.
- `audit.json`: dependency resolutions and implementation fixes that preserve
  the protocol.
- `metrics.json`: target metric status, evaluation scope, evaluator identity,
  metric value when obtained, and its evidence path.
- `security-attestation.json`: copied policy identifiers and hashes, declared
  events, and notes.
- `evidence/evaluator/`: unedited official evaluator output.
- `evidence/logs/`: logs and exit evidence for the recorded commands.
- `evidence/outputs/`: predictions and other outputs required by the contract.
- `evidence/intermediates/`: artifacts proving that required stage outputs fed
  the downstream stages.
- `source/`: source commit identifier and a patch or diff for any code change.
- `SHA256SUMS`: SHA-256 for every submitted file except `SHA256SUMS` itself.

Every evidence path inside a deliverable must be relative, must not contain
`..`, and must resolve to a file inside the package. If no target metric was
obtained, preserve partial evidence and give a non-empty `no_metric_reason`;
do not report a published value as reproduced.

## Local checks

From the package root, check the JSON files and hashes before archiving:

```bash
python3 -m json.tool DATASET_SELECTION.json >/dev/null
python3 -m json.tool pipeline-execution.json >/dev/null
python3 -m json.tool audit.json >/dev/null
python3 -m json.tool metrics.json >/dev/null
python3 -m json.tool security-attestation.json >/dev/null
sha256sum -c SHA256SUMS
```

Remove credentials, authentication files, private host paths, datasets, model
weights, checkpoints, and unrelated files. Do not alter evaluator output or
discard evidence of failed stages.

## Send the submission

Upload the archive to a stable download link. Email
`endlesssalaxy@outlook.com` with:

- subject: `ReproBoundary submission: <project-id> / <model> / <agent>`;
- project ID, model, agent, and source commit;
- archive download URL;
- SHA-256 of the archive;
- a short note stating whether the run claims a complete reproduction, a
  partial result, or no metric.

We first check contract identity, configuration identity, package completeness,
hashes, stage order, and artifact lineage. A leaderboard entry is added only
after the target metric can be independently replayed and the strict verdict is
resolved. Delivery, replay match, and strict reproduction remain separate
verdicts.
