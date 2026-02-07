# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\CODE\\QTS\\Projects\\AVDownloader\\AVDownloaderWithQTCpp\\AVDownloader\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('video_downloader.py', '.'), ('video_detector.py', '.'), ('ts_merger.py', '.'), ('browser_simulator.py', '.'), ('utils.py', '.'), ('decrypt_existing.py', '.'), ('download_state_manager.py', '.')],
    hiddenimports=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtGui', 'requests', 'beautifulsoup4', 'selenium', 'tqdm', 'pycryptodome', 'Crypto', 'Crypto.Cipher', 'Crypto.Cipher.AES', 'Crypto.Util.Padding', 'configparser'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AVDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
