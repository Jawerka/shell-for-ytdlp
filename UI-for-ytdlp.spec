# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec-файл для UI-for-ytdlp.

Сборка:
    pyinstaller --clean --noconfirm UI-for-ytdlp.spec

Результат:
    dist/UI-for-ytdlp/UI-for-ytdlp.exe
"""

import os
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

# Базовые настройки
block_cipher = None
app_name = 'UI-for-ytdlp'
# Абсолютный путь к иконке для корректной встройки в exe
# Используем getcwd(), т.к. __file__ недоступен в spec-файле при сборке
icon_path = os.path.join(os.getcwd(), 'icon.ico')

with open(os.path.join(os.getcwd(), 'VERSION'), encoding='utf-8') as _version_file:
    _app_version = _version_file.read().strip()
_version_parts = _app_version.split('.')
while len(_version_parts) < 4:
    _version_parts.append('0')
_ver_major, _ver_minor, _ver_patch, _ver_build = (int(p) for p in _version_parts[:4])

version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(_ver_major, _ver_minor, _ver_patch, _ver_build),
        prodvers=(_ver_major, _ver_minor, _ver_patch, _ver_build),
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    '040904B0',
                    [
                        StringStruct('CompanyName', 'Jawerka'),
                        StringStruct('FileDescription', 'UI-for-ytdlp'),
                        StringStruct('FileVersion', _app_version),
                        StringStruct('InternalName', 'UI-for-ytdlp'),
                        StringStruct('LegalCopyright', 'MIT License'),
                        StringStruct('OriginalFilename', 'UI-for-ytdlp.exe'),
                        StringStruct('ProductName', 'UI-for-ytdlp'),
                        StringStruct('ProductVersion', _app_version),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct('Translation', [1033, 1200])]),
    ],
)

# Собираем данные из модулей
datas = (
    collect_data_files('core') +
    collect_data_files('ui') +
    [('icon.ico', 'icon.ico')]
)

# Скрытые импорты
hiddenimports = [
    'pyperclip',
    'customtkinter',
    'PIL',
    'PIL.Image',
    'darkdetect',
    'tkinter',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'core',
    'core.theme',
    'core.icons',
    'core.utils',
    'core.logger',
    'core.config',
    'core.downloader',
    'core.updater',
    'ui',
    'ui.main_window',
    'ui.components',
    'ui.components.url_input',
    'ui.components.log_viewer',
    'ui.components.progress_bar',
    'ui.components.settings_dialog',
    'pystray',
    'core.tray_manager',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
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
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
    version=version_info,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name,
)
