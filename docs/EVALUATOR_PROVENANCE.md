# Evaluator provenance

Every task has a public, commit-pinned evaluator source URL and a frozen
`TARGET_EVALUATION.json`. This does not mean that every executable file was
copied verbatim from the corresponding paper repository.

- 46 of 47 evaluator source URLs use the same GitHub owner/repository recorded
  for the task. The former `luotianze666/SoFlow` URL redirects to
  `zlab-princeton/SoFlow`; both URLs resolve commit
  `cc47661a0b0843f8f1b6cff3a17107a052d18b21` to tree
  `da945571b04e4bf7cd22e7b7b90f2180ef2ca91b`, and both resolve
  `evaluator.py` to blob `1fb4a18bc5c5a0dcc9ab80e2d138eb3cb2e14133`.
- Task `2025.neurips.e323ebf7c91a4ca061612ba4a2f2164d` uses the external,
  standard EleutherAI `lm-evaluation-harness` ARC evaluator.
- Frozen execution directly invokes an upstream repository entrypoint for 11
  tasks, invokes a bundled `REDUCTION_PROTOCOL` helper for 35 tasks, and uses a
  benchmark-authored wrapper outside the paper repository for task `019`.

Bundled helpers pin inputs, validate completeness, adapt file formats, or
aggregate repetitions around the cited metric implementation. They are part
of the benchmark protocol and must not be described as original paper code
unless their per-file notice says so.

## Reliability evidence for the two apparent exceptions

For SoFlow, the URL difference was a repository transfer rather than an
evaluator substitution. The frozen evaluator is the exact content-addressed
file from the task repository commit. It uses the ADM Inception graph,
`pool_3:0` activations, and the repository's CIFAR-10 reference archive for
FID-50K.

For LinearPatch, the source paper, repository README, requirements, and
released `main_distill.py` all specify `lm-evaluation-harness` 0.4.4. The
released code invokes zero-shot `arc_easy` and reads `acc,none`. The frozen
task template preserves the upstream prompt, target mapping, choice order,
raw-accuracy aggregation, and all 2,376 test examples; its changes are limited
to the task name and a hash-verified local parquet binding.

These checks establish source authority, version identity, and protocol
equivalence. They do not constitute an independent numerical validation of
the third-party implementations. No separate cross-implementation regression
record was located in the release evidence. Before claiming independent
evaluator validation, add (1) an ADM/TTUR-versus-SoFlow FID regression on the
same fixed activations and (2) an upstream-versus-frozen ARC-Easy comparison
that asserts identical per-item choices and aggregate `acc`.
