#!/usr/bin/env bash
# build_qt563.sh — build Qt 5.6.3 (opensource) as Conan binary package(s).
#
# This is the Conan equivalent of core-app/scripts/setup_and_build*.sh for the
# qt563 presets: instead of building Qt from source into local_sdk/<preset>/,
# it produces a Conan package that epg later consumes (qt_from_conan=True).
#
# Only Qt is built here — its dependencies (zlib, opengl/system, …) come from
# the Conan remotes as binaries where available.
#
# Preset → Conan host-profile mapping (profiles live in ./profiles/):
#   linux-desktop-x86_64-qt563   → profiles/qt563-linux-x86_64
#   macos-desktop-arm64-qt563    → profiles/qt563-macos-armv8
#   macos-kirkstone-qt563        → profiles/qt563-rdk-kirkstone-armv7
#   linux-kirkstone-qt563        → profiles/qt563-rdk-kirkstone-armv7
#
# This script and its profiles live in the qt/5.6.3 recipe folder
#   conan-center-index/recipes/qt/5.6.3/
#
# The kirkstone presets cross-compile for RDK ARMv7 and require RDK_SDK_PATH to
# be exported (the host profile reads it to locate the cross toolchain/sysroot).
#
# Usage:
#   ./build_qt563.sh [--preset <name>]... [--export-only] [--dry-run] [-- <extra conan args>]
#
#   --preset <name>   Preset to build (repeatable). Default: the preset matching
#                     the host OS (macOS → macos-desktop-arm64-qt563,
#                     Linux → linux-desktop-x86_64-qt563).
#   --version <v>     Qt version to build (default: 5.6.3).
#   --build-profile   Conan build profile (default: default).
#   --export-only     Only `conan export` the recipe, do not build.
#   --dry-run         Resolve the graph (`conan graph info`) without building.
#   -h | --help       Show this help.
#
# Any arguments after `--` are forwarded verbatim to the conan command
# (e.g. `-- -r entos-iui-dev` or `-- --build=never`).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECIPE_DIR="${SCRIPT_DIR}"
PROFILES_DIR="${SCRIPT_DIR}/profiles"

QT_VERSION="5.6.3"
BUILD_PROFILE="default"
EXPORT_ONLY=0
DRY_RUN=0
REQUESTED_PRESETS=()
EXTRA_ARGS=()

# ---------------------------------------------------------------------------
# Preset → host profile mapping
# ---------------------------------------------------------------------------
profile_for_preset() {
    case "$1" in
        linux-desktop-x86_64-qt563) echo "${PROFILES_DIR}/qt563-linux-x86_64" ;;
        macos-desktop-arm64-qt563)  echo "${PROFILES_DIR}/qt563-macos-armv8" ;;
        macos-kirkstone-qt563|linux-kirkstone-qt563)
            echo "${PROFILES_DIR}/qt563-rdk-kirkstone-armv7" ;;
        *) return 1 ;;
    esac
}

default_preset_for_host() {
    case "$(uname -s)" in
        Darwin) echo "macos-desktop-arm64-qt563" ;;
        Linux)  echo "linux-desktop-x86_64-qt563" ;;
        *) return 1 ;;
    esac
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --preset)        REQUESTED_PRESETS+=("$2"); shift 2 ;;
        --preset=*)      REQUESTED_PRESETS+=("${1#*=}"); shift ;;
        --version)       QT_VERSION="$2"; shift 2 ;;
        --version=*)     QT_VERSION="${1#*=}"; shift ;;
        --build-profile) BUILD_PROFILE="$2"; shift 2 ;;
        --build-profile=*) BUILD_PROFILE="${1#*=}"; shift ;;
        --export-only)   EXPORT_ONLY=1; shift ;;
        --dry-run)       DRY_RUN=1; shift ;;
        --)              shift; EXTRA_ARGS=("$@"); break ;;
        -h|--help)
            awk 'NR>1 && /^[^#]/{exit} NR>1{sub(/^# ?/,""); print}' "$0"
            exit 0 ;;
        *) echo "Unknown argument: $1  (use --help)" >&2; exit 1 ;;
    esac
done

if [[ ${#REQUESTED_PRESETS[@]} -eq 0 ]]; then
    REQUESTED_PRESETS=("$(default_preset_for_host)")
fi

# ---------------------------------------------------------------------------
# Export recipe once (idempotent)
# ---------------------------------------------------------------------------
echo ">>> Exporting qt/${QT_VERSION} recipe …"
conan export "${RECIPE_DIR}" --version="${QT_VERSION}"

if [[ "${EXPORT_ONLY}" == "1" ]]; then
    echo ">>> Export-only requested; done."
    exit 0
fi

# ---------------------------------------------------------------------------
# Build each requested preset
# ---------------------------------------------------------------------------
for preset in "${REQUESTED_PRESETS[@]}"; do
    host_profile="$(profile_for_preset "${preset}")" \
        || { echo "ERROR: unknown preset '${preset}'." >&2; exit 1; }
    [[ -f "${host_profile}" ]] \
        || { echo "ERROR: profile not found: ${host_profile}" >&2; exit 1; }

    if [[ "${preset}" == *kirkstone* && -z "${RDK_SDK_PATH:-}" ]]; then
        echo "ERROR: preset '${preset}' cross-compiles for RDK; export RDK_SDK_PATH first." >&2
        exit 1
    fi

    echo ""
    echo "==================================================================="
    echo ">>> Preset        : ${preset}"
    echo ">>> Host profile  : ${host_profile}"
    echo ">>> Build profile : ${BUILD_PROFILE}"
    echo ">>> Qt version    : ${QT_VERSION}"
    echo "==================================================================="

    if [[ "${DRY_RUN}" == "1" ]]; then
        conan graph info --requires="qt/${QT_VERSION}" \
            -pr:h "${host_profile}" -pr:b "${BUILD_PROFILE}" \
            --build=missing "${EXTRA_ARGS[@]}"
        continue
    fi

    conan create "${RECIPE_DIR}" --version="${QT_VERSION}" \
        -pr:h "${host_profile}" -pr:b "${BUILD_PROFILE}" \
        --build=missing "${EXTRA_ARGS[@]}"

    echo ">>> Built qt/${QT_VERSION} for preset '${preset}'."
done

echo ""
echo ">>> All requested Qt ${QT_VERSION} builds complete."
