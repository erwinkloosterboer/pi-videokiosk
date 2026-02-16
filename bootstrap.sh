#!/bin/bash
# Pi Video Player - Install/Update bootstrap
# Run with: curl -fsSL https://raw.githubusercontent.com/erwinkloosterboer/pi-videokiosk/main/bootstrap.sh | bash
# Or for a specific directory: curl -fsSL ... | INSTALL_DIR=/opt/pi-videokiosk bash

set -e

REPO_URL="https://github.com/erwinkloosterboer/pi-videokiosk.git"
INSTALL_DIR="${INSTALL_DIR:-$HOME/pi-videokiosk}"

echo "Pi Video Player - Install/Update"
echo "Target: $INSTALL_DIR"
echo ""

if [[ -d "$INSTALL_DIR/.git" ]]; then
  echo "Updating existing installation..."
  cd "$INSTALL_DIR"
  git pull --ff-only
else
  echo "Cloning repository..."
  git clone "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

echo ""
echo "Running install script..."
chmod +x install.sh
exec ./install.sh
