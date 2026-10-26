# License notes

No top-level license has been selected for the files written by the
ReproBoundary team. Add and review that license before making the repository
public.

A **license** states how other people may copy, change, and redistribute a
file. The ReproBoundary license will not replace the licenses of source papers,
datasets, models, source repositories, or original evaluators. Those materials
keep the terms set by their owners.

Review every included evaluation helper before public release. If its license
does not permit redistribution, keep only the public source URL, exact version,
command, and file hash in `EVALUATOR_INDEX.csv`. A **file hash** is a digital
fingerprint used to identify exact file contents.

## Included third-party evaluator files

- Task 017 includes an evaluator subset under the MIT License.
- Task 118 includes an evaluator subset under Creative Commons Attribution 4.0
  (CC BY 4.0). Its notice records attribution and the changes made to pin model
  and dataset versions.
- Task 019 includes only wrappers written for ReproBoundary and a list of item
  IDs without answers. The source SinkTrack evaluator has no declared license,
  so it is linked but not copied.

A **wrapper** is a small program that prepares inputs or calls another program.
Read the `NOTICE.md` file in each task directory and
[Where the evaluator files came from](EVALUATOR_PROVENANCE.md) before
redistributing these files.
