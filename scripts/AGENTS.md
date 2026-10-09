# Artifact tooling agent rules

`artifactctl.py` validates catalogs and builds deterministic chart/bundle payloads; `discover.py` proposes upstream candidates; `install-tools.sh` installs locked local tools. Preserve checksum and license verification, deterministic output, and ignored `.out/` paths. Do not add authenticated access to private deployment repositories. Run `make validate`; use `make bundle` only for local review.

This is the GitHub.com production checkout. Verify the exact deployed revision before applying any live change.
