# Security policy

Report an unexpected payload, source or license change, credential finding, or
namespace/provenance mismatch privately to the repository owner. Do not include
secret values in an issue.

The public boundary contains only checksum-approved upstream software and its
source metadata. It excludes institutional or environment data, private source,
configuration values, topology, SOPS content, credentials, kubeconfigs, private
keys, deployment output, and receipts. Automated archive scans supplement
review; they do not make public visibility reversible.

Publication accepts an artifact identity only. Versions, URLs, allowlists,
checksums, expected metadata, and licenses come from the reviewed catalog. An
existing version succeeds only when its bytes are identical. Consumers verify
the OCI digest, publisher repository and commit, signer workflow, catalog
digest, and internal bundle checksums.

The owner uses phishing-resistant 2FA and protected recovery codes. The
`publish` environment requires a trusted reviewer with self-review disabled.
No publication secret exists: workflows use the short-lived repository
`GITHUB_TOKEN` and GitHub OIDC provenance. Replace a compromised artifact with
a new version, adopt it through reviewed consumer locks, verify adoption, and
only then consider the old version for retirement.
