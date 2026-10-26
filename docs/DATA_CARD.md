# Data card

## Scope

The release covers 47 tasks and nine model--framework configurations, producing 423 logical assignments. The frozen source archive contains 418 terminal evidence bundles, four unresolved raw trajectories, and one running-task snapshot. These states are preserved rather than converted into inferred outcomes.

## Task records

Each task record identifies the source paper, screening domain, target claim, metric, paper-reported reference, original and frozen scales, complete target evaluation set, resource envelope, repository URL and pinned revision, and task-contract hash. Twenty-seven tasks use a prespecified resource-bounded protocol while retaining the complete target evaluation set.

## Trajectories

The trajectory release contains one redacted `agent.log.gz` for every assignment and a central index mapping logs to tasks and configurations. It omits per-run metadata files, raw host security telemetry, provider payloads, machine identifiers, absolute internal paths, and credentials. A released log therefore supports qualitative and tool-use analysis but is not a byte-identical copy of the protected internal archive. Source and released SHA-256 values are listed separately in the index.

## Evaluation code

`evaluators/EVALUATOR_INDEX.csv` identifies the metric source, pinned upstream version, frozen command, and bundled helper files for every task. The release now includes evaluator-code subsets for tasks 017 and 118 under their upstream licenses and benchmark-authored wrappers for task 019. It does not redistribute the unlicensed SinkTrack evaluator, complete third-party repositories, datasets, weights, or gated assets. See `docs/EVALUATOR_PROVENANCE.md` for the distinction between original code and benchmark wrappers.

The evaluator bundle is kept lightweight and contains no models, datasets,
checkpoints, or predictions. Release verification rejects an evaluator file
larger than 1 MiB or a total evaluator bundle larger than 10 MiB.
Migration to a different filesystem, scheduler, or machine is documented in
`docs/PORTABILITY.md`; migration does not relax the frozen scientific
contract.
