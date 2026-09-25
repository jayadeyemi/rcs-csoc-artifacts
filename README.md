# CSOC public artifacts

This repository publishes immutable, public mirrors of approved upstream
artifacts used by the CSOC bootstrap. It contains source URLs, versions,
checksums, deterministic builders, and publication workflows. It contains no
environment values, topology, rendered deployment manifests, credentials,
kubeconfigs, private keys, receipts, or private repository content.

Published OCI namespaces:

- `ghcr.io/rcs-csoc/csoc-bootstrap-bundle`
- `ghcr.io/rcs-csoc/csoc-charts/<chart>`

Updates begin with a pull request changing a catalog entry. After that change
is merged, a maintainer manually dispatches the corresponding publication
workflow. The workflow reads the merged catalog, verifies upstream bytes,
publishes once, attests the OCI manifest digest, verifies anonymous access by
digest, and emits a candidate consumer lock. It never changes a consumer.

GitHub creates new packages as private. The first publication therefore stops
at its anonymous-read gate. A package owner sets the package to public and
reruns the same workflow; the replay must prove that the existing package is
byte-identical before it emits a candidate lock.

Run `make validate` for catalog, deterministic bundle, and unit validation.
