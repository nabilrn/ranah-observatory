# Ranah Observatory v0.1 deposit handoff

This directory binds the already-certified v0.1 PDF distribution to the already-frozen Zenodo metadata and makes the remaining human/external actions explicit.

The package is intentionally fail-closed: `external_publish_authorized=false`, `external_deposit_performed=false`, and `github_release_performed=false` until an explicit author instruction changes the publication state.

Use `deposit-handoff.json` as the machine-readable handoff, `CHECKLIST.md` before any external action, and `release-notes.md` as a candidate description only. The scientific authority remains the M29 claim ledger and the M34 canonical PDF distribution.
