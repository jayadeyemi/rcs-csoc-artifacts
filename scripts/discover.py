#!/usr/bin/env python3
"""Prepare a reviewed chart-catalog update from official Helm indexes."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifactctl

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog/charts.yaml"
NOTICES = ROOT / "THIRD_PARTY_NOTICES.md"
SUMMARY = ROOT / ".out/discovery-summary.md"
INDEXES = {
    "argo-cd": "https://argoproj.github.io/argo-helm/index.yaml",
    "external-secrets": "https://charts.external-secrets.io/index.yaml",
    "ingress-nginx": "https://kubernetes.github.io/ingress-nginx/index.yaml",
    "kube-prometheus-stack": "https://prometheus-community.github.io/helm-charts/index.yaml",
    "kyverno": "https://kyverno.github.io/kyverno/index.yaml",
    "velero": "https://vmware-tanzu.github.io/helm-charts/index.yaml",
}


def get(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "rcs-csoc-artifacts-discovery/1"})
    with urlopen(request, timeout=90) as response:
        return response.read()


def numeric(version: str) -> tuple[int, ...]:
    match = re.fullmatch(r"v?(\d+(?:\.\d+)+)", version)
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def rendered_count(archive: Path) -> str:
    try:
        output = subprocess.check_output(
            ["helm", "template", "discovery", str(archive), "--include-crds"],
            text=True, stderr=subprocess.STDOUT)
        return str(sum(1 for item in yaml.safe_load_all(output) if item))
    except (subprocess.CalledProcessError, yaml.YAMLError):
        return "not-renderable-with-defaults"


def main() -> None:
    artifactctl.validate_catalogs()
    catalog = artifactctl.load_yaml(CATALOG)
    changes = []
    with tempfile.TemporaryDirectory(prefix="rcs-discovery-") as directory:
        temporary = Path(directory)
        kro = catalog["charts"]["kro"]
        tags = yaml.safe_load(subprocess.check_output(
            ["oras", "repo", "tags", "registry.k8s.io/kro/charts/kro", "--format", "json"],
            text=True))["tags"]
        latest_tag = max((tag for tag in tags if numeric(tag)), key=numeric)
        if numeric(latest_tag) > numeric(str(kro["version"])):
            subprocess.run(["helm", "pull", kro["source_url"], "--version", latest_tag,
                            "--destination", str(temporary)], check=True)
            archive = next(temporary.glob("kro-*.tgz"))
            artifactctl.scan_archive(archive)
            metadata = artifactctl.load_yaml_text(subprocess.check_output(
                ["helm", "show", "chart", str(archive)], text=True))
            if metadata.get("name") != "kro":
                raise artifactctl.ArtifactError("discovered metadata differs for kro")
            old_version, old_sha = str(kro["version"]), kro["source_sha256"]
            kro.update(version=latest_tag.removeprefix("v"), source_tag=latest_tag,
                       publish_tag=str(metadata["version"]),
                       source_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                       expected_version=str(metadata["version"]))
            changes.append(("kro", old_version, kro["version"], old_sha,
                            kro["source_sha256"], rendered_count(archive)))
        for name, index_url in INDEXES.items():
            index = yaml.safe_load(get(index_url))
            candidates = [entry for entry in index.get("entries", {}).get(name, [])
                          if numeric(str(entry.get("version", "")))]
            if not candidates:
                raise artifactctl.ArtifactError(f"no discoverable releases for {name}")
            latest = max(candidates, key=lambda item: numeric(str(item["version"])))
            item = catalog["charts"][name]
            if numeric(str(latest["version"])) <= numeric(str(item["version"])):
                continue
            source = urljoin(index_url, latest["urls"][0])
            content = get(source)
            archive = temporary / f"{name}.tgz"
            archive.write_bytes(content)
            artifactctl.scan_archive(archive)
            metadata = artifactctl.load_yaml_text(subprocess.check_output(
                ["helm", "show", "chart", str(archive)], text=True))
            if metadata.get("name") != name or str(metadata.get("version")) != str(latest["version"]):
                raise artifactctl.ArtifactError(f"discovered metadata differs for {name}")
            old_version, old_sha = str(item["version"]), item["source_sha256"]
            item.update(version=str(latest["version"]), source_url=source,
                        source_sha256=hashlib.sha256(content).hexdigest(),
                        expected_version=str(metadata["version"]))
            changes.append((name, old_version, item["version"], old_sha,
                            item["source_sha256"], rendered_count(archive)))
    if not changes:
        print("No chart updates discovered")
        return
    CATALOG.write_text(yaml.safe_dump(catalog, sort_keys=False))
    NOTICES.write_text(artifactctl.third_party_notices())
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Upstream discovery candidate", "", "| Chart | From | To | SHA-256 | Default render |",
             "|---|---:|---:|---|---:|"]
    for name, old, new, _old_sha, new_sha, count in changes:
        lines.append(f"| {name} | {old} | {new} | `{new_sha}` | {count} objects |")
    lines += ["", "Bundle provider compatibility remains a manual reviewed update.", ""]
    SUMMARY.write_text("\n".join(lines))
    artifactctl.validate_catalogs()
    print(SUMMARY.read_text(), end="")


if __name__ == "__main__":
    main()
