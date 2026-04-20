#!/bin/bash
# package_deb.sh — Create a .deb package for YapClean
# Usage: ./package_deb.sh [version]

APP_NAME="yapclean"
APP_DISPLAY="YapClean"
VERSION="${1:-1.0.0}"
ARCH="amd64"
DIST_DIR="dist/YapClean"
PKG_DIR="deb_pkg"
INSTALL_DIR="${PKG_DIR}/opt/${APP_NAME}"

echo "Creating .deb package for ${APP_DISPLAY} ${VERSION}..."

rm -rf "${PKG_DIR}"
mkdir -p "${INSTALL_DIR}"
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/usr/bin"
mkdir -p "${PKG_DIR}/DEBIAN"

# Copy dist files
cp -r "${DIST_DIR}/." "${INSTALL_DIR}/"
chmod +x "${INSTALL_DIR}/YapClean"

# Symlink to /usr/bin
ln -sf "/opt/${APP_NAME}/YapClean" "${PKG_DIR}/usr/bin/${APP_NAME}"

# .desktop file
cat > "${PKG_DIR}/usr/share/applications/${APP_NAME}.desktop" << EOF
[Desktop Entry]
Name=${APP_DISPLAY}
Exec=/opt/${APP_NAME}/YapClean
Icon=${APP_NAME}
Type=Application
Categories=Utility;AudioVideo;
Comment=Voice input, cleaned by AI
StartupNotify=false
EOF

# DEBIAN/control
cat > "${PKG_DIR}/DEBIAN/control" << EOF
Package: ${APP_NAME}
Version: ${VERSION}
Architecture: ${ARCH}
Maintainer: yapclean.tech <hello@yapclean.tech>
Description: YapClean — Voice input, cleaned by AI
 Desktop utility for fast voice input with AI-powered text formatting.
 Supports multiple STT and LLM providers.
Homepage: https://yapclean.tech
Depends: libportaudio2, python3
EOF

# Build .deb
OUTPUT="dist/${APP_DISPLAY}-${VERSION}-${ARCH}.deb"
dpkg-deb --build "${PKG_DIR}" "${OUTPUT}"

echo ".deb created: ${OUTPUT}"
