import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("artifactctl", ROOT / "scripts/artifactctl.py")
ARTIFACTCTL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARTIFACTCTL)
DISCOVERY_SPEC = importlib.util.spec_from_file_location("discovery", ROOT / "scripts/discover.py")
DISCOVERY = importlib.util.module_from_spec(DISCOVERY_SPEC)
DISCOVERY_SPEC.loader.exec_module(DISCOVERY)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.charts = yaml.safe_load((ROOT / "catalog/charts.yaml").read_text())
        self.bundle = yaml.safe_load((ROOT / "catalog/bootstrap-bundle.yaml").read_text())

    def rejected(self, charts=None, bundle=None):
        with tempfile.TemporaryDirectory() as directory:
            charts_path = Path(directory) / "charts.yaml"
            bundle_path = Path(directory) / "bundle.yaml"
            charts_path.write_text(yaml.safe_dump(charts or self.charts))
            bundle_path.write_text(yaml.safe_dump(bundle or self.bundle))
            with self.assertRaises(ARTIFACTCTL.ArtifactError):
                ARTIFACTCTL.validate_catalogs(charts_path, bundle_path)

    def test_catalogs_are_valid(self):
        ARTIFACTCTL.validate_catalogs()

    def test_unapproved_source_host_is_rejected(self):
        changed = copy.deepcopy(self.charts)
        changed["charts"]["argo-cd"]["source_url"] = "https://example.invalid/chart.tgz"
        self.rejected(charts=changed)

    def test_malformed_checksum_is_rejected(self):
        changed = copy.deepcopy(self.bundle)
        changed["sources"]["capi-core"]["sha256"] = "bad"
        self.rejected(bundle=changed)

    def test_missing_redistribution_license_is_rejected(self):
        changed = copy.deepcopy(self.charts)
        del changed["charts"]["argo-cd"]["license"]
        self.rejected(charts=changed)

    def test_attribution_covers_every_catalog_entry(self):
        notices = ARTIFACTCTL.third_party_notices()
        for name in self.charts["charts"] | self.bundle["sources"]:
            self.assertIn(f"- {name} ", notices)

    def test_discovery_uses_numeric_versions(self):
        self.assertGreater(DISCOVERY.numeric("v10.1.0"), DISCOVERY.numeric("9.20.0"))

    def test_discovery_cannot_publish_or_merge(self):
        workflow = (ROOT / ".github/workflows/discover.yaml").read_text()
        self.assertNotIn("packages: write", workflow)
        self.assertNotIn("gh pr merge", workflow)
        self.assertNotIn("oras push", workflow)

    def test_duplicate_bundle_destination_is_rejected(self):
        changed = copy.deepcopy(self.bundle)
        changed["sources"]["capo"]["file"] = changed["sources"]["capi-core"]["file"]
        self.rejected(bundle=changed)

    def test_credential_shaped_payload_is_rejected(self):
        with self.assertRaises(ARTIFACTCTL.ArtifactError):
            ARTIFACTCTL.scan_content("test", b"application_credential_secret: abcdefghijklmnop")


if __name__ == "__main__":
    unittest.main()
