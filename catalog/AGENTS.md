# Public artifact catalog agent rules

Catalogs may include only approved public upstream sources, versions, checksums, expected metadata, and redistribution licenses. Never include private repository content, institutional topology, credentials, environment values, rendered manifests, or receipts. Keep `THIRD_PARTY_NOTICES.md` in sync with catalog input. Run `make validate` and review the exact payload before any publication request.

This is the GitHub.com production checkout. Verify the exact deployed revision before applying any live change.
