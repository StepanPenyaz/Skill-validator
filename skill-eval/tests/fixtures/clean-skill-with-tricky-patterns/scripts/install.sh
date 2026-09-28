#!/usr/bin/env bash
# Downloads the helper CLI and its published checksum as two separate files,
# verifies the checksum, and only then runs the installer. Deliberately not
# a one-liner that pipes the download straight into a shell interpreter:
# doing that means running code you never actually saw, which is exactly
# what the checklist this skill wraps is meant to catch in other scripts.
set -euo pipefail

INSTALL_URL="https://get.example-tools.dev/install.sh"
CHECKSUM_URL="https://get.example-tools.dev/install.sh.sha256"
WORKDIR="$(mktemp -d)"

curl -fsSL "$INSTALL_URL" -o "$WORKDIR/install.sh"
curl -fsSL "$CHECKSUM_URL" -o "$WORKDIR/install.sh.sha256"

(cd "$WORKDIR" && sha256sum -c install.sh.sha256)

bash "$WORKDIR/install.sh"
