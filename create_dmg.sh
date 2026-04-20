#!/bin/bash
# create_dmg.sh — Package YapClean.app into a signed .dmg
# Usage: ./create_dmg.sh [version] [signing_identity]
# Requires: create-dmg (brew install create-dmg)

APP_NAME="YapClean"
VERSION="${1:-1.0.0}"
SIGNING_IDENTITY="${2:-}"
APP_PATH="dist/${APP_NAME}.app"
DMG_PATH="dist/${APP_NAME}-${VERSION}.dmg"

echo "Creating DMG: ${DMG_PATH}"

create-dmg \
  --volname "${APP_NAME}" \
  --volicon "NONE" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "${APP_NAME}.app" 150 200 \
  --app-drop-link 450 200 \
  "${DMG_PATH}" \
  "${APP_PATH}"

if [ -n "${SIGNING_IDENTITY}" ]; then
  echo "Signing DMG..."
  codesign --sign "${SIGNING_IDENTITY}" "${DMG_PATH}"
fi

echo "DMG created: ${DMG_PATH}"
echo ""
echo "To notarize:"
echo "  xcrun notarytool submit ${DMG_PATH} \\"
echo "    --apple-id YOUR_APPLE_ID \\"
echo "    --team-id YOUR_TEAM_ID \\"
echo "    --password YOUR_APP_SPECIFIC_PASSWORD \\"
echo "    --wait"
echo "  xcrun stapler staple ${DMG_PATH}"
