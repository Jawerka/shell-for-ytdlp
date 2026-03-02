# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec-файл для UI-for-ytdlp.

Сборка:
    pyinstaller --clean --noconfirm UI-for-ytdlp.spec

Результат:
    dist/UI-for-ytdlp.exe
"""

import os
from PyInstaller.utils.hooks import collect_data_files

# Базовые настройки
block_cipher = None
app_name = 'UI-for-ytdlp'
# Абсолютный путь к иконке для корректной встройки в exe
# Используем getcwd(), т.к. __file__ недоступен в spec-файле при сборке
icon_path = os.path.join(os.getcwd(), 'icon.ico')

# Собираем данные из модулей
# resources/ директория не существует - убираем collect_data_files('resources')
datas = (
    collect_data_files('core') +
    collect_data_files('ui') +  # Включая sfx/*.wav если существуют
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
    # Явные импорты для новых модулей
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
]

# Анализ исходного кода
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

# Создание PYZ архива
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Создание EXE файла
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=app_name,
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
    icon=icon_path,
)
