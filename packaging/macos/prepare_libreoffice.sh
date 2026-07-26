#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="26.2.4"
ARCHIVE_NAME="LibreOffice_${VERSION}_MacOS_aarch64.dmg"
ARCHIVE_URL="https://download.documentfoundation.org/libreoffice/stable/${VERSION}/mac/aarch64/${ARCHIVE_NAME}"
ARCHIVE_SHA256="64e0ad05564554eeee639d49b08b20908a38d4722ec95f1620d05c99bcbe9fb1"
CACHE_DIR="${ROOT_DIR}/.cache/libreoffice"
ARCHIVE_PATH="${CACHE_DIR}/${ARCHIVE_NAME}"
RUNTIME_DIR="${ROOT_DIR}/vendor/libreoffice"
RUNTIME_APP="${RUNTIME_DIR}/LibreOffice.app"

if [[ "$(uname -m)" != "arm64" ]]; then
    print -u2 "Подготовка macOS runtime поддерживается только на Apple Silicon."
    exit 1
fi

if [[ -x "${RUNTIME_APP}/Contents/MacOS/soffice" ]]; then
    codesign --force --deep --sign - "${RUNTIME_APP}"
    codesign --verify --deep --strict "${RUNTIME_APP}"
    print "LibreOffice ${VERSION} уже подготовлен: ${RUNTIME_APP}"
    exit 0
fi

mkdir -p "${CACHE_DIR}"
if [[ ! -f "${ARCHIVE_PATH}" ]]; then
    print "Загрузка LibreOffice ${VERSION} для Apple Silicon…"
    curl \
        --fail \
        --location \
        --continue-at - \
        --output "${ARCHIVE_PATH}" \
        "${ARCHIVE_URL}"
fi

ACTUAL_SHA256="$(shasum -a 256 "${ARCHIVE_PATH}" | awk '{print $1}')"
if [[ "${ACTUAL_SHA256}" != "${ARCHIVE_SHA256}" ]]; then
    print -u2 "Контрольная сумма LibreOffice не совпала."
    print -u2 "Ожидалось: ${ARCHIVE_SHA256}"
    print -u2 "Получено:  ${ACTUAL_SHA256}"
    exit 1
fi

TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/offline-file-converter-lo.XXXXXX")"
MOUNT_POINT="${TEMP_DIR}/mount"
MOUNTED=0

cleanup() {
    if [[ "${MOUNTED}" == "1" ]]; then
        hdiutil detach "${MOUNT_POINT}" >/dev/null
    fi
    rm -rf "${TEMP_DIR}"
}
trap cleanup EXIT

mkdir -p "${MOUNT_POINT}"
hdiutil attach \
    "${ARCHIVE_PATH}" \
    -nobrowse \
    -readonly \
    -mountpoint "${MOUNT_POINT}" \
    >/dev/null
MOUNTED=1

rm -rf "${RUNTIME_DIR}"
mkdir -p "${RUNTIME_DIR}"
ditto "${MOUNT_POINT}/LibreOffice.app" "${RUNTIME_APP}"

hdiutil detach "${MOUNT_POINT}" >/dev/null
MOUNTED=0

codesign --force --deep --sign - "${RUNTIME_APP}"
codesign --verify --deep --strict "${RUNTIME_APP}"
print "LibreOffice runtime подготовлен: ${RUNTIME_APP}"
