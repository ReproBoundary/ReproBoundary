# Checklist before public release

- [ ] Add a top-level license for metadata, scripts, and documentation written
  by the ReproBoundary team. A license states how others may reuse the files.
- [ ] Check the license of every included evaluation helper.
- [ ] Run `python3 scripts/verify_release.py` and save the successful output.
- [ ] Manually inspect a sample of logs with many redactions. Redaction means
  replacement of detected sensitive text.
- [ ] Make the verified Hugging Face trajectory dataset public after its
  license is approved. Before publication, confirm that all 423 remote LFS
  SHA-256 values match `TRAJECTORY_INDEX.csv`.
- [ ] Create a version tag and a DOI, then add the release URL to the paper. A
  DOI is a permanent identifier for a published research item.
- [ ] Confirm that the package contains no datasets, model weights, hidden
  labels, credentials, or private machine records.
- [ ] Confirm that the task list, evaluator index, website task data, and paper
  report the same task count and versions.
