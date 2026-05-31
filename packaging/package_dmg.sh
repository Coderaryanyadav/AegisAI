#!/bin/bash
# Script to package compiled macOS AegisLegalAI.app into a double-clickable .dmg installer

set -e

# Determine project root (one level up from packaging/)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

APP_PATH="dist/AegisLegalAI.app"
DMG_PATH="dist/AegisLegalAI.dmg"
VOL_NAME="Aegis Legal AI"

echo "[*] Packaging macOS standalone app into disk image..."

if [ ! -d "$APP_PATH" ]; then
    echo "[!] Error: Compiled app bundle '$APP_PATH' does not exist."
    echo "[*] Please run 'python packaging/build_desktop.py' first to compile the app."
    exit 1
fi

# Remove existing DMG if it exists
if [ -f "$DMG_PATH" ]; then
    echo "[*] Removing existing DMG file..."
    rm -f "$DMG_PATH"
fi

# Create a DMG from the folder containing the app
echo "[*] Compiling disk image (hdiutil)..."
hdiutil create \
    -volname "$VOL_NAME" \
    -srcfolder "$APP_PATH" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

echo "[*] Successfully created standalone disk installer: $DMG_PATH"
echo "[*] You can distribute this DMG file directly to your clients!"
