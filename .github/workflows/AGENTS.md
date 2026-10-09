# Artifact publication workflow agent rules

Discovery can propose candidates but cannot publish. Publication requires reviewed protected `main`, exact commit manual dispatch, the `publish` environment and `PUBLICATION_ENABLED` gate. It uses the short-lived workflow token and GitHub.com public GHCR; the GHE registry is not the current publisher. Keep SHA-pinned actions and verify private payload, public visibility, anonymous pull, and provenance before emitting a consumer lock. A successful validation workflow never authorizes publication.

This is the GitHub.com production checkout. Verify the exact deployed revision before applying any live change.
