# ReproBoundary open-source materials

This release contains the frozen inventory for 47 paper-reproduction tasks, redacted Agent trajectories for all 423 primary task--configuration assignments, and the task contracts and evaluation helpers needed to reconstruct benchmark scoring. It separates paper-reported references, candidate metrics, protocol compliance, and replay-based verdicts. The package excludes datasets, model weights, hidden host-only records, raw security telemetry, credentials, and third-party repositories; obtain upstream artifacts from the pinned URLs and revisions in the task and evaluator indexes. Resource-bounded tasks reproduce a frozen target claim under the stated budget and must not be interpreted as reproducing every conclusion of the source paper.

## Contents

- `task_pool/`: the 47-paper inventory, exact task-paper BibTeX entries, and public membership manifest.
- `trajectories/`: one redacted `agent.log.gz` for each of 423 assignments, plus a central index that maps logs to tasks and configurations and records their hashes.
- `evaluators/`: 47 frozen task contracts, bundled evaluation helpers or licensed evaluator subsets, and pinned upstream evaluator links. See `docs/EVALUATOR_PROVENANCE.md` before describing bundled helpers as original paper code.
- `protocol/`: public prompt and task-specification templates.
- `docs/`: release scope, evaluator provenance and migration, redaction policy, licensing notes, and publication checklist. Start with `docs/PORTABILITY.md` when moving an evaluator to another machine.

Verify the package with `python3 scripts/verify_release.py`. Large trajectory files should be published with Git LFS or an archival data host rather than ordinary Git blobs.

The evaluator bundle is intentionally lightweight: it contains contracts,
small scripts, configurations, and answer-free membership manifests, but no
model weights, datasets, checkpoints, predictions, or complete third-party
repositories. The verifier enforces a 1 MiB per-file and 10 MiB total limit.
