# Public artifact source catalog

`charts.yaml` and `bootstrap-bundle.yaml` record approved public upstream versions, URLs, checksums, metadata, and redistribution licenses. `THIRD_PARTY_NOTICES.md` at the repository root is generated from these catalogs. No institutional topology, private Git content, deployment values, or credentials belong in a published payload.

Run `make validate` after a catalog change. Review the fetched upstream bytes, checksum, license, and deterministic build before merging. Publication is a separate protected manual workflow, described in the [repository README](../README.md).
