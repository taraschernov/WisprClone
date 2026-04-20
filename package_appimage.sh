#!/bin/bash
# package_appimage.sh — Wrap YapClean dist into an AppImage
# Requires: appimagetool (https://github.com/AppImage/AppImageKit/releases)
# Usage: ./package_appimage.sh [version]

APP_NAME="YapClean"
VERSION="${1:-1.0.0}"
DIST_DIR="dist/${APP_NAME}"
APPDIR="AppDir"

echo "Creating AppImage for ${APP_NAME} ${VERSION}..."

# Create AppDir structure
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/share/applications"
mkdir -p "${APPDIR}/usr/share/icons/hicolor/256x256/apps"

# Copy dist files
cp -r "${DIST_DIR}/." "${APPDIR}/usr/bin/"

# Create .desktop file
cat > "${APPDIR}/${APP_NAME}.desktop" << EOF
[Desktop Entry]
Name=${APP_NAME}
Exec=${APP_NAME}
Icon=${APP_NAME}
Type=Application
Categories=Utility;AudioVideo;
Comment=Voice input, cleaned by AI
EOF

cp "${APPDIR}/${APP_NAME}.desktop" "${APPDIR}/usr/share/applications/"

# AppRun entry point
cat > "${APPDIR}/AppRun" << 'APPRUN'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE="${SELF%/*}"
export PATH="${HERE}/usr/bin:${PATH}"
exec "${HERE}/usr/bin/YapClean" "$@"
APPRUN
chmod +x "${APPDIR}/AppRun"

# Build AppImage
OUTPUT="dist/${APP_NAME}-${VERSION}-x86_64.AppImage"
appimagetool "${APPDIR}" "${OUTPUT}"

echo "AppImage created: ${OUTPUT}"
