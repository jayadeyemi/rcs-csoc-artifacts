#!/usr/bin/env bash
set -euo pipefail

destination="${1:?tool destination required}"
mkdir -p "${destination}"

curl -fsSL https://github.com/mikefarah/yq/releases/download/v4.53.3/yq_linux_amd64 -o "${destination}/yq"
echo "fa52a4e758c63d38299163fbdd1edfb4c4963247918bf9c1c5d31d84789eded4  ${destination}/yq" | sha256sum -c -

curl -fsSL https://get.helm.sh/helm-v3.17.3-linux-amd64.tar.gz -o "${destination}/helm.tgz"
echo "ee88b3c851ae6466a3de507f7be73fe94d54cbf2987cbaa3d1a3832ea331f2cd  ${destination}/helm.tgz" | sha256sum -c -
tar -xzf "${destination}/helm.tgz" -C "${destination}" linux-amd64/helm
mv "${destination}/linux-amd64/helm" "${destination}/helm"
rmdir "${destination}/linux-amd64"

curl -fsSL https://github.com/oras-project/oras/releases/download/v1.3.4/oras_1.3.4_linux_amd64.tar.gz -o "${destination}/oras.tgz"
echo "f27adb935022d94df8dc77719c322dda592c78a0d57a6f7dcdd8d900b248c454  ${destination}/oras.tgz" | sha256sum -c -
tar -xzf "${destination}/oras.tgz" -C "${destination}" oras

chmod 0755 "${destination}/yq" "${destination}/helm" "${destination}/oras"
