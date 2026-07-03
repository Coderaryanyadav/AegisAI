#!/bin/bash
set -e

echo "========================================"
echo " AegisAI - Local Deployment Builder     "
echo "========================================"

# 1. Build Frontend
echo ">>> Building Next.js Frontend..."
cd aegis_frontend
npm install
npm run build
cd ..

# 2. Copy Frontend export to desktop wrapper
echo ">>> Copying frontend assets to Desktop App..."
rm -rf aegis_desktop/out
cp -R aegis_frontend/out aegis_desktop/out

# 3. Build Backend
echo ">>> Building Python Backend with PyInstaller..."
rm -rf dist/aegis_backend
if [ -d "venv" ]; then
    source venv/bin/activate
fi
pip install pyinstaller
pyinstaller aegis_backend.spec --clean --noconfirm

# 4. Build Electron Desktop App
echo ">>> Packaging Desktop App with Electron Builder..."
cd aegis_desktop
npm install
npm run dist
cd ..

echo "========================================"
echo " Build Complete! Artifacts in dist_desktop/ "
echo "========================================"
