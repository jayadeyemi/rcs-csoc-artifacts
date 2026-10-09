# Agent instructions

This production repository publishes the public upstream chart and bootstrap-bundle mirrors currently used by CSOC. The private GHE copy under `../../ghe-migration/rcs-csoc-artifacts` is validation-only for the present cutover.

## Publication rules

- Publish only approved public upstream software with verified checksums and licenses. Never include institutional topology, private Git content, deployment values, credentials, kubeconfigs, receipts, or rendered environment output.
- Preserve immutable artifact versions, exact digests, publisher commits, catalog hashes, and signed provenance. Consumer lock changes require a separately reviewed publisher result and anonymous pull verification.
- The GHE container registry is unavailable, and no bastion-hosted replacement is running. Do not repoint publication or consumer locks to either endpoint without a separate reviewed migration.
- Do not dispatch publication from a validation-only workflow or claim GHE publication succeeded from an offline build.

## Validate

Run `make validate`, checksum and license checks, secret scans, and deterministic build checks before publishing. Verify the resulting artifacts from a clean consumer context.
