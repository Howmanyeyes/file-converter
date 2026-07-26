#!/bin/zsh

set -euo pipefail

if [[ "$#" -ne 1 || ("$1" != "full" && "$1" != "lite") ]]; then
    print -u2 "Использование: $0 full|lite"
    exit 1
fi

EDITION="$1"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON="${ROOT_DIR}/.venv/bin/python"
EDITION_FILE="${ROOT_DIR}/packaging/macos/editions/${EDITION}.txt"
export NUITKA_CACHE_DIR="${ROOT_DIR}/.cache/nuitka"
export PYTHONPATH="${ROOT_DIR}/src"

if [[ "${EDITION}" == "full" ]]; then
    APP_NAME="Offline File Converter"
    BUNDLE_IDENTIFIER="com.offlinefileconverter.app.full"
    OUTPUT_DIRECTORY="${ROOT_DIR}/build/macos-full"
else
    APP_NAME="Offline File Converter Lite"
    BUNDLE_IDENTIFIER="com.offlinefileconverter.app.lite"
    OUTPUT_DIRECTORY="${ROOT_DIR}/build/macos-lite"
fi

APP_PATH="${OUTPUT_DIRECTORY}/${APP_NAME}.app"
GENERATED_APP_PATH="${OUTPUT_DIRECTORY}/main.app"

if [[ ! -x "${PYTHON}" ]]; then
    print -u2 "Сначала создайте .venv и установите requirements.txt."
    exit 1
fi

PYTHON_VERSION="$(
    "${PYTHON}" -c \
        'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
)"
if [[ "${PYTHON_VERSION}" != "3.13" ]]; then
    print -u2 "Сборка требует Python 3.13, сейчас в .venv: ${PYTHON_VERSION}."
    print -u2 "Пересоздайте окружение командами:"
    print -u2 "  mise install"
    print -u2 "  mise exec -- python -m venv --clear .venv"
    print -u2 "  source .venv/bin/activate"
    print -u2 "  python -m pip install -r requirements.txt"
    exit 1
fi

if [[ "${EDITION}" == "full" ]]; then
    "${ROOT_DIR}/packaging/macos/prepare_libreoffice.sh"
fi

mkdir -p "${NUITKA_CACHE_DIR}" "${OUTPUT_DIRECTORY}"
rm -rf "${GENERATED_APP_PATH}"

"${PYTHON}" -m nuitka \
    --standalone \
    --enable-plugin=pyside6 \
    --macos-create-app-bundle \
    --macos-target-arch=arm64 \
    --macos-app-icon="${ROOT_DIR}/assets/app-icon.icns" \
    --macos-app-name="${APP_NAME}" \
    --macos-signed-app-name="${BUNDLE_IDENTIFIER}" \
    --macos-app-version="0.1.0" \
    --output-filename="${APP_NAME}" \
    --assume-yes-for-downloads \
    --include-package=offline_file_converter \
    --include-data-dir="${ROOT_DIR}/src/offline_file_converter/resources=offline_file_converter/resources" \
    --include-data-files="${EDITION_FILE}=offline_file_converter/resources/edition.txt" \
    --output-dir="${OUTPUT_DIRECTORY}" \
    "${ROOT_DIR}/main.py"

if [[ ! -d "${GENERATED_APP_PATH}" ]]; then
    print -u2 "Nuitka не создал приложение: ${GENERATED_APP_PATH}"
    exit 1
fi

rm -rf "${APP_PATH}"
mv "${GENERATED_APP_PATH}" "${APP_PATH}"

if [[ "${EDITION}" == "full" ]]; then
    RUNTIME_SOURCE="${ROOT_DIR}/vendor/libreoffice/LibreOffice.app"
    RUNTIME_DESTINATION="${APP_PATH}/Contents/Frameworks/LibreOffice.app"

    mkdir -p "$(dirname "${RUNTIME_DESTINATION}")"
    ditto "${RUNTIME_SOURCE}" "${RUNTIME_DESTINATION}"

    if [[ ! -x "${RUNTIME_DESTINATION}/Contents/MacOS/soffice" ]]; then
        print -u2 "LibreOffice runtime не попал в полную сборку."
        exit 1
    fi

    codesign --force --deep --sign - "${RUNTIME_DESTINATION}"
    codesign --verify --deep --strict "${RUNTIME_DESTINATION}"
fi

codesign --force --deep --sign - "${APP_PATH}"
codesign --verify --deep --strict "${APP_PATH}"

print "Приложение собрано: ${APP_PATH}"
du -sh "${APP_PATH}"
