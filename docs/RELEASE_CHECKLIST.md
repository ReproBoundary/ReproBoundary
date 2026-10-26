# Checklist before public release

- [ ] Add a top-level license for metadata, scripts, and documentation written
  by the ReproBoundary team. A license states how others may reuse the files.
- [ ] Check the license of every included evaluation helper.
- [ ] Run `python3 scripts/verify_release.py` and save the successful output.
- [ ] Manually inspect a sample of logs with many redactions. Redaction means
  replacement of detected sensitive text.
- [ ] Publish compressed logs through Git LFS, Hugging Face Datasets, or Zenodo.
  Git LFS stores large files outside normal Git history; Zenodo is a research
  archive.
- [ ] Create a version tag and a DOI, then add the release URL to the paper. A
  DOI is a permanent identifier for a published research item.
- [ ] Confirm that the package contains no datasets, model weights, hidden
  labels, credentials, or private machine records.
- [ ] Confirm that the task list, evaluator index, website task data, and paper
  report the same task count and versions.
