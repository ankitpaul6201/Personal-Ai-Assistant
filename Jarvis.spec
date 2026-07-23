# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

# Assets and data files to bundle
datas = []
for folder in ['assets', 'config']:
    if os.path.exists(folder):
        datas.append((folder, folder))

if os.path.exists('face.png'):
    datas.append(('face.png', '.'))

if os.path.exists(os.path.join('core', 'prompt.txt')):
    datas.append((os.path.join('core', 'prompt.txt'), 'core'))

hiddenimports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PIL',
    'PIL.Image',
    'google.genai',
    'google.genai.types',
    'psutil',
    'sounddevice',
    'wmi',
    'win32com',
    'win32com.client',
    'cv2',
    'qrcode',
    'requests',
    'urllib.request',
    'json',
    'math',
    'subprocess',
    'threading',
    'asyncio',
    'xml.etree.ElementTree',
    'html',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'IPython', 'notebook', 'pytest'],
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
    name='Jarvis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Jarvis',
)
