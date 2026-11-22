# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

hidden_imports = [
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan.on",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "sqlalchemy.sql.default_comparator",
    "chromadb.api.segment",
    "chromadb.api.rust",
    "chromadb.telemetry.opentelemetry",
    "chromadb.telemetry.product.posthog",
    "chromadb.db.impl.sqlite",
    "chromadb.migrations",
    "chromadb.migrations.embeddings",
    "sentence_transformers",
    "pdfplumber",
    "pypdf",
    "email_validator",
    "bcrypt",
    "cryptography",
    "fitz",
    "pytesseract",
    "pg8000",
    "asyncpg",
    "sqlalchemy.dialects.postgresql.pg8000",
    "sqlalchemy.dialects.postgresql.asyncpg",
    "aiosqlite",
    "sqlalchemy.dialects.sqlite.aiosqlite",
    "keyring",
    "pyotp",
    "qrcode",
    "pythonjsonlogger"
]

datas = [
    ('aegis_backend/model_bundle', 'aegis_backend/model_bundle'),
    ('aegis_backend/legal_mappings.json', 'aegis_backend'),
]

a = Analysis(
    ['aegis_backend/main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtimehooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='aegis_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='aegis_backend',
)
