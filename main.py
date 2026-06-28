# -*- coding: utf-8 -*-
"""
UI-for-ytdlp — Современный GUI для yt-dlp.

Рефакторированная версия с модульной архитектурой.
"""

import os
import sys
import logging
from datetime import datetime

# ============================================================================
# НАСТРОЙКА DEBUG РЕЖИМА
# ============================================================================
# Установите True или env UI_FOR_YTDLP_DEBUG=1 для подробного логирования в консоль
DEBUG_MODE = os.environ.get('UI_FOR_YTDLP_DEBUG', '').lower() in ('1', 'true', 'yes')


# ============================================================================
# НАСТРОЙКА ЛОГГЕРА
# ============================================================================
def setup_debug_logging():
    """Настроить подробное логирование в консоль."""
    if not DEBUG_MODE:
        return
    
    # Создаём форматтер с временем, уровнем, модулем и сообщением
    formatter = logging.Formatter(
        fmt='[%(asctime)s.%(msecs)03d] [%(levelname)-8s] [%(name)s:%(lineno)d] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Создаём консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    
    # Логгер для приложения
    app_logger = logging.getLogger('UI-for-ytdlp')
    app_logger.setLevel(logging.DEBUG)
    
    app_logger.debug("=" * 80)
    app_logger.debug("ЗАПУСК ПРИЛОЖЕНИЯ UI-for-ytdlp")
    app_logger.debug(f"Версия Python: {sys.version}")
    app_logger.debug(f"Платформа: {sys.platform}")
    app_logger.debug(f"Путь к скрипту: {os.path.abspath(__file__)}")
    app_logger.debug(f"Рабочая директория: {os.getcwd()}")
    app_logger.debug("=" * 80)


# ============================================================================
# ИНИЦИАЛИЗАЦИЯ PYINSTALLER
# ============================================================================
if hasattr(sys, '_MEIPASS'):
    # Запуск из exe
    _MEIPASS_PATH = sys._MEIPASS
    os.chdir(os.path.dirname(sys.executable))
    project_root = os.path.dirname(sys.executable)
    print(f"[DEBUG] PyInstaller mode: {_MEIPASS_PATH}", file=sys.stdout)
else:
    # Запуск из исходного кода
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    print(f"[DEBUG] Development mode: {project_root}", file=sys.stdout)


# ============================================================================
# НАСТРОЙКА DEBUG ЛОГИРОВАНИЯ
# ============================================================================
setup_debug_logging()
logger = logging.getLogger('UI-for-ytdlp.main')


# ============================================================================
# ДИАГНОСТИКА ОКРУЖЕНИЯ
# ============================================================================
def diagnose_environment():
    """Диагностика окружения перед запуском."""
    if not DEBUG_MODE:
        return
    
    logger.debug("-" * 60)
    logger.debug("ДИАГНОСТИКА ОКРУЖЕНИЯ")
    logger.debug("-" * 60)
    
    # Пути
    logger.debug(f"sys.executable: {sys.executable}")
    logger.debug(f"sys.path ({len(sys.path)} entries):")
    for i, path in enumerate(sys.path[:10]):  # Первые 10 путей
        logger.debug(f"  [{i}] {path}")
    if len(sys.path) > 10:
        logger.debug(f"  ... и ещё {len(sys.path) - 10} путей")
    
    # Переменные окружения
    logger.debug("Переменные окружения:")
    for key in ['PYTHONPATH', 'PYTHONHOME', 'TEMP', 'TMP']:
        value = os.environ.get(key, 'не установлена')
        logger.debug(f"  {key}: {value}")
    
    # Проверка импортов
    logger.debug("Проверка обязательных импортов:")
    required_modules = [
        'customtkinter',
        'tkinter',
        'pyperclip',
        'PIL',
        'darkdetect',
        'pystray',
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            mod = sys.modules[module]
            version = getattr(mod, '__version__', 'версия неизвестна')
            logger.debug(f"  [OK] {module} (версия: {version})")
        except ImportError as e:
            logger.debug(f"  [FAIL] {module}: {e}")
    
    # Проверка файлов проекта
    logger.debug("Проверка файлов проекта:")
    project_files = [
        'core/__init__.py',
        'core/theme.py',
        'core/icons.py',
        'ui/__init__.py',
        'ui/main_window.py',
        'utilities/yt-dlp.exe',
        'utilities/ffmpeg.exe',
    ]
    
    for filepath in project_files:
        full_path = os.path.join(project_root, filepath)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            if size > 1024 * 1024:  # > 1 MB
                size_str = f"{size / 1024 / 1024:.1f} MB"
            else:
                size_str = f"{size / 1024:.1f} KB"
            logger.debug(f"  [OK] {filepath} ({size_str})")
        else:
            logger.debug(f"  [MISSING] {filepath}")
    
    logger.debug("-" * 60)


# ============================================================================
# МОНИТОРИНГ ПАМЯТИ
# ============================================================================
def log_memory_usage(stage: str):
    """Логирование использования памяти."""
    if not DEBUG_MODE:
        return
    
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        logger.debug(
            f"[MEMORY] {stage}: "
            f"RSS={memory_info.rss / 1024 / 1024:.1f} MB, "
            f"VMS={memory_info.vms / 1024 / 1024:.1f} MB"
        )
    except ImportError:
        # psutil не установлен - пропускаем
        pass


# ============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# ============================================================================
def main():
    """Точка входа приложения."""
    logger.debug("Вызов main()")
    
    # Диагностика окружения
    diagnose_environment()
    
    # Логирование перед импортом
    logger.debug("Импорт MainWindow из ui.main_window")
    log_memory_usage("перед импортом MainWindow")
    
    try:
        from ui import MainWindow
        logger.debug("MainWindow успешно импортирован")
    except Exception as e:
        logger.error(f"Ошибка импорта MainWindow: {e}", exc_info=True)
        raise
    
    log_memory_usage("после импорта MainWindow")
    
    # Создание приложения
    logger.debug("Создание экземпляра MainWindow")
    log_memory_usage("перед созданием MainWindow")
    
    try:
        app = MainWindow()
        logger.debug("MainWindow успешно создан")
        logger.debug(f"Размер окна: {app.geometry()}")
        logger.debug(f"Заголовок: {app.title()}")
    except Exception as e:
        logger.error(f"Ошибка создания MainWindow: {e}", exc_info=True)
        raise
    
    log_memory_usage("после создания MainWindow")
    
    # Запуск главного цикла
    logger.debug("Запуск mainloop()")
    logger.debug("=" * 80)
    logger.debug("ПРИЛОЖЕНИЕ ЗАПУЩЕНО")
    logger.debug("=" * 80)
    
    try:
        app.mainloop()
    except Exception as e:
        logger.error(f"Ошибка в mainloop: {e}", exc_info=True)
        raise
    finally:
        logger.debug("=" * 80)
        logger.debug("ПРИЛОЖЕНИЕ ЗАВЕРШЕНО")
        logger.debug("=" * 80)
        log_memory_usage("после завершения")


if __name__ == "__main__":
    main()
