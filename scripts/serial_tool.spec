# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable,
    StringStruct, VarFileInfo, VarStruct
)

block_cipher = None

# 读取版本号（只读取第一行）
with open('VERSION', 'r', encoding='utf-8') as f:
    lines = f.read().strip().split('\n')
    version_str = lines[0].strip()

# 将版本号转换为四位数字格式 (例如: 1.7.1 -> 1.7.1.0)
version_parts = version_str.split('.')
while len(version_parts) < 4:
    version_parts.append('0')
version_tuple = tuple(int(x) for x in version_parts[:4])

# Windows版本信息
version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=version_tuple,
        prodvers=version_tuple,
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
    ),
    kids=[
        StringFileInfo([
            StringTable('040904B0', [
                StringStruct('CompanyName', 'Serial Tool Development'),
                StringStruct('FileDescription', 'Serial Monitor Tool - 串口监控工具'),
                StringStruct('FileVersion', version_str),
                StringStruct('InternalName', 'SerialMonitorTool'),
                StringStruct('LegalCopyright', '© 2025 Serial Tool Development Team'),
                StringStruct('OriginalFilename', 'SerialMonitorTool.exe'),
                StringStruct('ProductName', 'Serial Monitor Tool'),
                StringStruct('ProductVersion', version_str),
            ])
        ]),
        VarFileInfo([VarStruct('Translation', [1033, 1200])])
    ]
)

a = Analysis(
    ['gui_app.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[
        ('serial_monitor.py', '.'),
        ('VERSION', '.'),
    ],
    hiddenimports=[
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        'serial_monitor',
    ],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SerialMonitorTool',
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
    version=version_info,
    icon=None,
)