# -*- coding: utf-8 -*-
"""
Модуль установки JavaScript runtime (deno).

Содержит:
- check_deno_installed - проверка наличия deno
- download_deno - автоматическая загрузка deno
"""

import os
import logging
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .utils import download_file

logger = logging.getLogger('UI-for-ytdlp.deno')


DENO_DOWNLOAD_URL = 'https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip'


def _deno_runs(deno_path: str) -> bool:
    """Проверить, что deno.exe действительно запускается."""
    try:
        result = subprocess.run(
            [deno_path, '--version'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def check_deno_installed(utilities_path: str) -> bool:
    """
    Проверить наличие рабочего deno.exe в utilities.

    Args:
        utilities_path: Путь к директории utilities

    Returns:
        True если deno установлен и запускается
    """
    deno_path = os.path.join(utilities_path, 'deno.exe')
    installed = os.path.exists(deno_path) and _deno_runs(deno_path)
    logger.debug(f"check_deno_installed: {deno_path} -> {installed}")
    return installed


def download_deno(utilities_path: str, callback: callable = None, cancel_event: callable = None) -> bool:
    """
    Скачать и установить deno.exe.

    Args:
        utilities_path: Путь к директории utilities
        callback: Функция обратного вызова для прогресса
        cancel_event: threading.Event для отмены загрузки

    Returns:
        True если загрузка успешна
    """
    deno_zip_path = os.path.join(utilities_path, 'deno.zip')
    deno_path = os.path.join(utilities_path, 'deno.exe')
    temp_dir = None

    try:
        logger.info(f"Загрузка deno из {DENO_DOWNLOAD_URL}")

        if callback:
            callback("Загрузка deno (JavaScript runtime)...")

        def _report_hook(downloaded, total):
            """Обратный вызов для отображения прогресса загрузки."""
            if total > 0:
                percent = downloaded * 100 // total
                downloaded_mb = downloaded // (1024 * 1024)
                total_mb = total // (1024 * 1024)
                if callback:
                    callback(f"Загрузка deno: {percent}% ({downloaded_mb}MB / {total_mb}MB)")

        if not download_file(DENO_DOWNLOAD_URL, deno_zip_path, _report_hook, cancel_event):
            if callback:
                callback("Установка deno отменена")
            return False

        if callback:
            callback("Распаковка deno...")

        temp_dir = tempfile.mkdtemp(prefix='.deno-', dir=utilities_path)
        with ZipFile(deno_zip_path, 'r') as zip_ref:
            zip_ref.extract('deno.exe', temp_dir)

        extracted_path = os.path.join(temp_dir, 'deno.exe')
        if not _deno_runs(extracted_path):
            raise OSError('deno.exe не запускается после распаковки')

        os.replace(extracted_path, deno_path)

        logger.info(f"deno успешно установлен: {deno_path}")

        if callback:
            callback("deno установлен!")

        return True

    except Exception as e:
        logger.error(f"Ошибка установки deno: {e}")
        if callback:
            callback(f"Ошибка установки deno: {e}")
        return False
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        if os.path.exists(deno_zip_path):
            try:
                os.remove(deno_zip_path)
            except OSError:
                pass


def ensure_deno_exists(utilities_path: str, callback: callable = None, cancel_event: callable = None) -> bool:
    """
    Убедиться что deno существует (проверка + загрузка если нужно).

    Args:
        utilities_path: Путь к директории utilities
        callback: Функция обратного вызова
        cancel_event: threading.Event для отмены загрузки

    Returns:
        True если deno доступен
    """
    if check_deno_installed(utilities_path):
        logger.debug("deno уже установлен")
        return True

    logger.info("deno не найден, попытка загрузки...")
    return download_deno(utilities_path, callback, cancel_event)
