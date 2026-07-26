#!/bin/zsh

set -euo pipefail

if [[ "$#" -ne 1 || ("$1" != "full" && "$1" != "lite") ]]; then
    print -u2 "Использование: $0 full|lite"
    exit 1
fi

EDITION="$1"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="0.1.0"

if [[ "${EDITION}" == "full" ]]; then
    APP_NAME="Offline File Converter"
    VOLUME_NAME="Offline File Converter"
    APP_PATH="${ROOT_DIR}/build/macos-full/${APP_NAME}.app"
    APP_BUILDER="${ROOT_DIR}/packaging/macos/build_app_full.sh"
    INSTALLER_PATH="${ROOT_DIR}/dist/OfflineFileConverter-${VERSION}-full-macos-arm64.dmg"
else
    APP_NAME="Offline File Converter Lite"
    VOLUME_NAME="Offline File Converter Lite"
    APP_PATH="${ROOT_DIR}/build/macos-lite/${APP_NAME}.app"
    APP_BUILDER="${ROOT_DIR}/packaging/macos/build_app_lite.sh"
    INSTALLER_PATH="${ROOT_DIR}/dist/OfflineFileConverter-${VERSION}-lite-macos-arm64.dmg"
fi

STAGING_DIRECTORY="${ROOT_DIR}/build/installer-${EDITION}"

"${APP_BUILDER}"

rm -rf "${STAGING_DIRECTORY}"
mkdir -p "${STAGING_DIRECTORY}" "${ROOT_DIR}/dist"
ditto "${APP_PATH}" "${STAGING_DIRECTORY}/${APP_NAME}.app"
ln -s /Applications "${STAGING_DIRECTORY}/Applications"

rm -f "${INSTALLER_PATH}"
hdiutil create \
    -volname "${VOLUME_NAME}" \
    -srcfolder "${STAGING_DIRECTORY}" \
    -ov \
    -format UDZO \
    "${INSTALLER_PATH}"
hdiutil verify "${INSTALLER_PATH}"

print "Установщик собран: ${INSTALLER_PATH}"
du -sh "${INSTALLER_PATH}"
