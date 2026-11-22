#!/usr/bin/env bash
# ==============================================================================
# ⚖️ AegisAI - Official Release Builder & Desktop DMG Packager (v1.0.0)
# ==============================================================================
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo -e "${CYAN}${BOLD}"
echo "========================================================================"
echo "  ⚖️  AEGISAI ENTERPRISE RELEASE BUILDER (v1.0.0) "
echo "========================================================================"
echo -e "${NC}"

# ------------------------------------------------------------------------------
# Phase 1: Toolchain & Dependency Verification
# ------------------------------------------------------------------------------
echo -e "${BOLD}[Phase 1/6]${NC} Verifying system build toolchains..."

if ! command -v node &>/dev/null; then
    echo -e "${RED}[ERROR] Node.js is required but not installed.${NC}"
    exit 1
fi

if ! command -v npm &>/dev/null; then
    echo -e "${RED}[ERROR] npm is required but not installed.${NC}"
    exit 1
fi

PYTHON_EXEC=""
if [ -f "$ROOT_DIR/venv/bin/python" ]; then
    PYTHON_EXEC="$ROOT_DIR/venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_EXEC="python3"
else
    echo -e "${RED}[ERROR] Python 3.11+ is required but not found.${NC}"
    exit 1
fi

PYINSTALLER_EXEC=""
if [ -f "$ROOT_DIR/venv/bin/pyinstaller" ]; then
    PYINSTALLER_EXEC="$ROOT_DIR/venv/bin/pyinstaller"
elif command -v pyinstaller &>/dev/null; then
    PYINSTALLER_EXEC="pyinstaller"
else
    echo -e "${YELLOW}[*] Installing pyinstaller in virtual environment...${NC}"
    "$PYTHON_EXEC" -m pip install pyinstaller
    PYINSTALLER_EXEC="$ROOT_DIR/venv/bin/pyinstaller"
fi

echo -e "  ${GREEN}✔ Node.js:${NC} $(node --version)"
echo -e "  ${GREEN}✔ Python:${NC} $("$PYTHON_EXEC" --version)"
echo -e "  ${GREEN}✔ PyInstaller:${NC} $("$PYINSTALLER_EXEC" --version)"

# ------------------------------------------------------------------------------
# Phase 2: Run Automated Regression Tests
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[Phase 2/6]${NC} Running automated regression test suite..."
if [ -f "$ROOT_DIR/venv/bin/pytest" ]; then
    PYTHONPATH="$ROOT_DIR" "$ROOT_DIR/venv/bin/pytest" tests/test_unit.py -q --disable-warnings
    echo -e "  ${GREEN}✔ All unit test assertions passed.${NC}"
else
    echo -e "  ${YELLOW}⚠ Pytest not found, skipping unit test validation.${NC}"
fi

# ------------------------------------------------------------------------------
# Phase 3: Compile Next.js Static Export
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[Phase 3/6]${NC} Compiling Next.js frontend to static production export..."
cd "$ROOT_DIR/aegis_frontend"
npm install --silent
npm run build
cd "$ROOT_DIR"

if [ ! -d "$ROOT_DIR/aegis_frontend/out" ]; then
    echo -e "${RED}[ERROR] Frontend build did not produce aegis_frontend/out directory.${NC}"
    exit 1
fi
echo -e "  ${GREEN}✔ Next.js static assets built successfully.${NC}"

# ------------------------------------------------------------------------------
# Phase 4: Sync Assets to Desktop Shell
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[Phase 4/6]${NC} Syncing static frontend assets to Electron desktop wrapper..."
rm -rf "$ROOT_DIR/aegis_desktop/out"
cp -R "$ROOT_DIR/aegis_frontend/out" "$ROOT_DIR/aegis_desktop/out"
echo -e "  ${GREEN}✔ Synchronized $(find "$ROOT_DIR/aegis_desktop/out" -type f | wc -l | tr -d ' ') files to aegis_desktop/out.${NC}"

# ------------------------------------------------------------------------------
# Phase 5: Compile Standalone Backend Binary with PyInstaller
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[Phase 5/6]${NC} Compiling FastAPI backend binary with PyInstaller..."
rm -rf "$ROOT_DIR/dist/aegis_backend" "$ROOT_DIR/build/aegis_backend"

"$PYINSTALLER_EXEC" "$ROOT_DIR/aegis_backend.spec" --clean --noconfirm

if [ ! -f "$ROOT_DIR/dist/aegis_backend/aegis_backend" ]; then
    echo -e "${RED}[ERROR] PyInstaller compilation failed: dist/aegis_backend/aegis_backend not found.${NC}"
    exit 1
fi
echo -e "  ${GREEN}✔ Standalone backend executable compiled.${NC}"

# ------------------------------------------------------------------------------
# Phase 6: Package Electron Desktop DMG Application
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[Phase 6/6]${NC} Packaging macOS Electron application and DMG installer..."
cd "$ROOT_DIR/aegis_desktop"
npm install --silent

# Strip IDE environment variable if present so electron-builder executes in clean runtime
unset ELECTRON_RUN_AS_NODE 2>/dev/null || true
npm run dist
cd "$ROOT_DIR"

# ------------------------------------------------------------------------------
# Summary & Checksum Generation
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}${BOLD}========================================================================${NC}"
echo -e "${GREEN}${BOLD}  ✨ RELEASE 1.0.0 BUILD SUCCEEDED!                                     ${NC}"
echo -e "${GREEN}${BOLD}========================================================================${NC}"

cd "$ROOT_DIR/dist_desktop"
for dmg_file in *.dmg; do
    if [ -f "$dmg_file" ]; then
        shasum -a 256 "$dmg_file" > "${dmg_file}.sha256"
        echo -e "  ${BOLD}Artifact:${NC}  dist_desktop/$dmg_file ($(du -h "$dmg_file" | cut -f1))"
        echo -e "  ${BOLD}SHA-256:${NC}   $(cat "${dmg_file}.sha256" | cut -d' ' -f1)"
        echo -e "  ${BOLD}Checksum:${NC}  dist_desktop/${dmg_file}.sha256"
    fi
done
cd "$ROOT_DIR"

echo -e "\n${CYAN}Ready for distribution. Mount the DMG or publish to GitHub Releases.${NC}\n"
