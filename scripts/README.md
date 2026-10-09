# Artifact discovery and build tooling

`discover.py` identifies candidate upstream releases; `artifactctl.py` validates metadata, generates notices, and builds deterministic OCI payload inputs; `install-tools.sh` installs locked local prerequisites. Local review artifacts belong under ignored `.out/`.

Run `make validate`; use `make bundle` to inspect a local bootstrap bundle. Do not add private repository inputs or deployment credentials. A local build never proves that a public digest or attestation is available to consumers.
