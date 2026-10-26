# Source and license notice

`reports/019-2026.iclr.10010470/evaluate_three_seeds.py` and
`dry_runs/019/audit/run_sinktrack_audit.py` are benchmark-authored wrappers.
The former validates full prediction coverage and aggregates the three frozen
seeds; the latter records auditable SinkTrack inference metadata. The ID file
contains the ordered identifiers for the full public M3CoT test split and no
answers or labels.

The wrappers call the original SinkTrack evaluator at commit
`b6ba69105904b77bee810eb324b20103cbc33b0f`. No license was present in the
frozen SinkTrack repository or returned by GitHub's repository-license API on
October 25, 2026. Consequently, the original `eval.py` is not redistributed;
obtain it from the pinned source URL in `EVALUATOR_INDEX.csv`.
