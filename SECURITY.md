# Security boundary

These packages contain unmodified public upstream charts and provider assets.
Deployment intent and secrets belong in the private consumer repositories.

Publication accepts an artifact name only. Versions, locations, allowed hosts,
and SHA-256 values come from the reviewed catalog. Existing versions cannot be
replaced with different bytes. Consumers authorize an exact OCI digest and the
publisher commit, and verify GitHub build provenance before a fresh download.

Report an unexpected payload, source change, namespace change, or credential
finding privately to the repository owner. Do not include secret values in an
issue. Compromised versions are retired by publishing a new version, updating
consumer locks, verifying adoption, and only then removing the old version.
