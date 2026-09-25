#!/usr/bin/env python3
"""Validate approved sources and build deterministic public CSOC artifacts."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
CHARTS = ROOT / "catalog/charts.yaml"
BUNDLE = ROOT / "catalog/bootstrap-bundle.yaml"
SHA = re.compile(r"[0-9a-f]{64}")
VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")
SAFE_PATH = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._/-]*")
DISALLOWED_NAMES = {"clouds.yaml", "keys.txt", "kubeconfig", "id_rsa", "id_ed25519"}
SECRET_PATTERNS = {
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "OpenStack credential": re.compile(
        rb"application_credential_secret\s*:\s*['\"]?[A-Za-z0-9_+/=-]{16,}"),
    "Kubernetes private key": re.compile(rb"client-key-data\s*:\s*[A-Za-z0-9+/=]{80,}"),
}


class ArtifactError(RuntimeError):
    pass


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
        value = yaml.safe_load(path.read_text())
    except ImportError:
        output = subprocess.check_output(["yq", "-o=json", ".", str(path)], text=True)
        value = json.loads(output)
    if not isinstance(value, dict):
        raise ArtifactError(f"{path.relative_to(ROOT)} must contain a mapping")
    return value


def load_yaml_text(content: str) -> dict:
    try:
        import yaml  # type: ignore
        value = yaml.safe_load(content)
    except ImportError:
        output = subprocess.check_output(
            ["yq", "-o=json", "."], input=content, text=True)
        value = json.loads(output)
    if not isinstance(value, dict):
        raise ArtifactError("expected YAML mapping")
    return value


def catalog_sha(path: Path) -> str:
    return sha256_file(path)


def approved_url(url: str, allowed_hosts: set[str], schemes: set[str], *, allow_query=False) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in schemes or parsed.hostname not in allowed_hosts:
        raise ArtifactError(f"unapproved source URL: {url}")
    if parsed.username or parsed.password or (parsed.query and not allow_query) or parsed.fragment:
        raise ArtifactError(f"source URL contains unsupported components: {url}")


def validate_catalogs(charts_path: Path = CHARTS, bundle_path: Path = BUNDLE) -> None:
    charts = load_yaml(charts_path)
    bundle = load_yaml(bundle_path)
    if charts.get("schema_version") != 1 or bundle.get("schema_version") != 1:
        raise ArtifactError("unsupported catalog schema")
    chart_hosts = set(charts.get("allowed_hosts", []))
    bundle_hosts = set(bundle.get("allowed_hosts", []))
    redirect_hosts = set(charts.get("allowed_redirect_hosts", [])) | set(
        bundle.get("allowed_redirect_hosts", []))
    if not chart_hosts or not bundle_hosts:
        raise ArtifactError("catalog requires an explicit host allowlist")
    if not redirect_hosts or not all(re.fullmatch(r"[a-z0-9.-]+", host)
                                     for host in redirect_hosts):
        raise ArtifactError("catalog requires an explicit redirect host allowlist")
    seen_sources: set[tuple[str, str]] = set()
    for name, item in charts.get("charts", {}).items():
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
            raise ArtifactError(f"invalid chart identity: {name}")
        if not VERSION.fullmatch(str(item.get("version", ""))):
            raise ArtifactError(f"invalid chart version: {name}")
        url = item.get("source_url", "")
        approved_url(url, chart_hosts, {"https", "oci"})
        digest = item.get("source_sha256", "")
        if not SHA.fullmatch(digest):
            raise ArtifactError(f"invalid chart checksum: {name}")
        if item.get("expected_name") != name or not VERSION.fullmatch(
                str(item.get("expected_version", ""))):
            raise ArtifactError(f"invalid expected chart metadata: {name}")
        identity = (url, str(item["version"]))
        if identity in seen_sources:
            raise ArtifactError(f"duplicate chart source identity: {name}")
        seen_sources.add(identity)
    if set(charts.get("charts", {})) != {
            "argo-cd", "external-secrets", "ingress-nginx", "kro",
            "kube-prometheus-stack", "kyverno", "velero"}:
        raise ArtifactError("chart catalog differs from the approved set")
    version = str(bundle.get("bundle", {}).get("version", ""))
    if not re.fullmatch(r"[0-9]{4}\.[0-9]{2}\.[1-9][0-9]*", version):
        raise ArtifactError("invalid bundle version")
    destinations: set[str] = set()
    for name, item in bundle.get("sources", {}).items():
        url, destination = item.get("url", ""), item.get("file", "")
        approved_url(url, bundle_hosts, {"https"})
        if not SHA.fullmatch(item.get("sha256", "")):
            raise ArtifactError(f"invalid bundle checksum: {name}")
        if not VERSION.fullmatch(str(item.get("version", ""))):
            raise ArtifactError(f"invalid bundle source version: {name}")
        path = PurePosixPath(destination)
        if (not SAFE_PATH.fullmatch(destination) or path.is_absolute() or ".." in path.parts or
                destination in destinations):
            raise ArtifactError(f"unsafe or duplicate bundle destination: {name}")
        destinations.add(destination)
    if not destinations:
        raise ArtifactError("bundle has no sources")


class CheckedRedirects(HTTPRedirectHandler):
    def __init__(self, redirect_hosts: set[str]):
        self.redirect_hosts = redirect_hosts
        super().__init__()

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        approved_url(newurl, self.redirect_hosts, {"https"}, allow_query=True)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_https(url: str, allowed_hosts: set[str], redirect_hosts: set[str]) -> bytes:
    approved_url(url, allowed_hosts, {"https"})
    opener = build_opener(CheckedRedirects(redirect_hosts))
    request = Request(url, headers={"User-Agent": "rcs-csoc-artifacts/1"})
    with opener.open(request, timeout=90) as response:
        if urlsplit(response.geturl()).hostname not in allowed_hosts | redirect_hosts:
            raise ArtifactError("source resolved to an unapproved host")
        return response.read()


def scan_content(label: str, content: bytes) -> None:
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(content):
            raise ArtifactError(f"{label} contains a credential-shaped value ({name})")
    if re.search(rb"\b10\.100\.[0-9]{1,3}\.[0-9]{1,3}\b", content):
        raise ArtifactError(f"{label} contains an environment network address")


def scan_archive(path: Path) -> None:
    try:
        with tarfile.open(path, "r:gz") as archive:
            for member in archive.getmembers():
                relative = PurePosixPath(member.name)
                if relative.is_absolute() or ".." in relative.parts or member.issym() or member.islnk():
                    raise ArtifactError(f"archive contains unsafe member: {member.name}")
                if relative.name.lower() in DISALLOWED_NAMES or relative.name.endswith(".sops.yaml"):
                    raise ArtifactError(f"archive contains forbidden input: {member.name}")
                if member.isfile():
                    stream = archive.extractfile(member)
                    if stream is not None:
                        scan_content(member.name, stream.read())
    except tarfile.TarError as exc:
        raise ArtifactError("invalid gzip tar archive") from exc


def fetch_chart(name: str, output: Path) -> dict:
    validate_catalogs()
    catalog = load_yaml(CHARTS)
    try:
        item = catalog["charts"][name]
    except KeyError as exc:
        raise ArtifactError(f"unknown chart: {name}") from exc
    url = item["source_url"]
    output.parent.mkdir(parents=True, exist_ok=True)
    if url.startswith("https://"):
        content = download_https(url, set(catalog["allowed_hosts"]),
                                 set(catalog["allowed_redirect_hosts"]))
        output.write_bytes(content)
    else:
        with tempfile.TemporaryDirectory(prefix="rcs-chart-") as directory:
            subprocess.run(["helm", "pull", url, "--version",
                item.get("source_tag", str(item["version"])), "--destination", directory], check=True)
            pulled = next(Path(directory).glob("*.tgz"), None)
            if pulled is None:
                raise ArtifactError("OCI source produced no chart archive")
            shutil.copyfile(pulled, output)
    if sha256_file(output) != item["source_sha256"]:
        raise ArtifactError(f"upstream checksum differs for {name}")
    metadata = load_yaml_text(subprocess.check_output(
        ["helm", "show", "chart", str(output)], text=True))
    if (metadata.get("name") != item["expected_name"] or
            str(metadata.get("version")) != item["expected_version"]):
        raise ArtifactError(f"upstream chart metadata differs for {name}")
    scan_archive(output)
    return item


def normalized_tar(directory: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path in sorted(directory.rglob("*")):
                    if not path.is_file():
                        continue
                    relative = path.relative_to(directory).as_posix()
                    content = path.read_bytes()
                    info = tarfile.TarInfo(relative)
                    info.size, info.mtime = len(content), 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mode = 0o644
                    archive.addfile(info, io.BytesIO(content))


def build_bundle(output: Path) -> dict:
    validate_catalogs()
    catalog = load_yaml(BUNDLE)
    hosts = set(catalog["allowed_hosts"])
    redirects = set(catalog["allowed_redirect_hosts"])
    with tempfile.TemporaryDirectory(prefix="rcs-bundle-") as directory:
        root = Path(directory)
        for name, item in sorted(catalog["sources"].items()):
            content = download_https(item["url"], hosts, redirects)
            if sha256_bytes(content) != item["sha256"]:
                raise ArtifactError(f"upstream checksum differs for {name}")
            scan_content(name, content)
            destination = root / item["file"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            if destination.suffix == ".tgz":
                scan_archive(destination)
        shutil.copyfile(BUNDLE, root / "sources.yaml")
        files = []
        for path in sorted(root.rglob("*")):
            if path.is_file():
                files.append({"path": path.relative_to(root).as_posix(),
                              "sha256": sha256_file(path)})
        manifest = {"schema_version": 1, "version": catalog["bundle"]["version"],
                    "source_catalog_sha256": catalog_sha(BUNDLE), "files": files}
        # JSON is valid YAML and removes serializer-dependent output.
        (root / "manifest.yaml").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        normalized_tar(root, output)
    scan_archive(output)
    return catalog


def candidate(kind: str, name: str | None, digest: str, output: Path) -> None:
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ArtifactError("invalid OCI manifest digest")
    commit = os.environ.get("GITHUB_SHA", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ArtifactError("exact publisher commit required")
    if kind == "chart":
        if not name:
            raise ArtifactError("chart name required")
        item = load_yaml(CHARTS)["charts"].get(name)
        if not item:
            raise ArtifactError("unknown chart")
        document = {name: {"version": item["version"],
            "repository": f"oci://ghcr.io/rcs-csoc/csoc-charts/{name}", "digest": digest,
            "publisher_repository": "rcs-csoc/rcs-csoc-artifacts",
            "publisher_revision": commit, "source_catalog": "catalog/charts.yaml",
            "source_catalog_sha256": catalog_sha(CHARTS)}}
    else:
        item = load_yaml(BUNDLE)
        document = {"bootstrap_bundle": {"version": item["bundle"]["version"],
            "repository": "ghcr.io/rcs-csoc/csoc-bootstrap-bundle", "digest": digest,
            "publisher_repository": "rcs-csoc/rcs-csoc-artifacts",
            "publisher_revision": commit, "source_catalog": "catalog/bootstrap-bundle.yaml",
            "source_catalog_sha256": catalog_sha(BUNDLE)}}
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    chart = sub.add_parser("fetch-chart")
    chart.add_argument("--name", required=True)
    chart.add_argument("--output", type=Path, required=True)
    bundle = sub.add_parser("build-bundle")
    bundle.add_argument("--output", type=Path, required=True)
    lock = sub.add_parser("candidate")
    lock.add_argument("--kind", choices=("chart", "bundle"), required=True)
    lock.add_argument("--name")
    lock.add_argument("--digest", required=True)
    lock.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            validate_catalogs()
            print("artifact catalogs: PASS")
        elif args.command == "fetch-chart":
            fetch_chart(args.name, args.output)
        elif args.command == "build-bundle":
            build_bundle(args.output)
        else:
            candidate(args.kind, args.name, args.digest, args.output)
    except (ArtifactError, OSError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
