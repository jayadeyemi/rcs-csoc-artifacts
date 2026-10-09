# Public artifact workflows

`discover.yaml` may propose a catalog update. `validate.yaml` checks it. `publish-chart.yaml` and `publish-bundle.yaml` require manual dispatch from reviewed protected `main`, the `publish` environment, and `PUBLICATION_ENABLED`. The GitHub.com publisher produces public GHCR artifacts consumed by exact digest; the GHE copy is a validation candidate, not the current publisher.

Review action pins, token permissions, checksum and license gates, payload contents, provenance, and anonymous pull before accepting a consumer lock. A discovery or validation result cannot publish by itself.
