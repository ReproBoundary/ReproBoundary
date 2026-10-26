# Public release checklist

- [ ] Select and add a top-level license for project-authored metadata, scripts, and documentation.
- [ ] Review each bundled evaluation helper for third-party license compatibility.
- [ ] Run `python3 scripts/verify_release.py` and retain its clean output.
- [ ] Independently inspect a sample of logs with high redaction counts.
- [ ] Publish `.gz` trajectories through Git LFS, Hugging Face Datasets, or Zenodo.
- [ ] Create a version tag and archival DOI, then add the release URL to the paper.
- [ ] Confirm that no data, weights, hidden labels, credentials, or private host records are included.
