#!/bin/zsh

set -euo pipefail

if [[ "$#" -ne 1 || ("$1" != "full" && "$1" != "lite") ]]; then
    print -u2 "Использование: $0 full|lite"
    exit 1
fi

EDITION="$1"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="$(<"${ROOT_DIR}/packaging/macos/version.txt")"
PYTHON="${ROOT_DIR}/.venv/bin/python"
BACKGROUND_SOURCE="${ROOT_DIR}/packaging/macos/dmg-background.png"
BACKGROUND_RENDERER="${ROOT_DIR}/packaging/macos/create_dmg_background.py"
LAYOUT_SCRIPT="${ROOT_DIR}/packaging/macos/layout_dmg.applescript"

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
READ_WRITE_IMAGE="${ROOT_DIR}/build/installer-${EDITION}-rw.dmg"
MOUNT_DIRECTORY="/Volumes/${VOLUME_NAME}"
ATTACHED_DEVICE=""

cleanup() {
    if [[ -n "${ATTACHED_DEVICE}" ]]; then
        hdiutil detach "${ATTACHED_DEVICE}" -force >/dev/null 2>&1 || true
    fi
    rm -f "${READ_WRITE_IMAGE}"
}

trap cleanup EXIT

"${APP_BUILDER}"
"${PYTHON}" "${BACKGROUND_RENDERER}" "${BACKGROUND_SOURCE}"

rm -rf "${STAGING_DIRECTORY}"
mkdir -p \
    "${STAGING_DIRECTORY}/.background" \
    "${ROOT_DIR}/dist"
ditto "${APP_PATH}" "${STAGING_DIRECTORY}/${APP_NAME}.app"
ln -s /Applications "${STAGING_DIRECTORY}/Applications"
cp "${BACKGROUND_SOURCE}" \
    "${STAGING_DIRECTORY}/.background/background.png"
chflags hidden "${STAGING_DIRECTORY}/.background"

rm -f "${INSTALLER_PATH}" "${READ_WRITE_IMAGE}"
hdiutil create \
    -volname "${VOLUME_NAME}" \
    -srcfolder "${STAGING_DIRECTORY}" \
    -fs HFS+ \
    -ov \
    -format UDRW \
    "${READ_WRITE_IMAGE}"

if [[ -e "${MOUNT_DIRECTORY}" ]]; then
    print -u2 "Сначала извлеките подключённый том: ${MOUNT_DIRECTORY}"
    exit 1
fi

hdiutil attach \
    -readwrite \
    -noverify \
    -noautoopen \
    "${READ_WRITE_IMAGE}"
ATTACHED_DEVICE="${MOUNT_DIRECTORY}"
if [[ ! -d "${MOUNT_DIRECTORY}" ]]; then
    print -u2 "Finder не видит подключённый том: ${MOUNT_DIRECTORY}"
    exit 1
fi

osascript "${LAYOUT_SCRIPT}" "${VOLUME_NAME}" "${APP_NAME}"
sync

if ! hdiutil detach "${ATTACHED_DEVICE}"; then
    hdiutil detach "${ATTACHED_DEVICE}" -force
fi
ATTACHED_DEVICE=""

hdiutil convert \
    "${READ_WRITE_IMAGE}" \
    -format UDZO \
    -imagekey zlib-level=9 \
    -o "${INSTALLER_PATH}"
hdiutil verify "${INSTALLER_PATH}"

print "Установщик собран: ${INSTALLER_PATH}"
du -sh "${INSTALLER_PATH}"

cleanup
trap - EXIT
