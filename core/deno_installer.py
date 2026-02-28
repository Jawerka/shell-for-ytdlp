# -*- coding: utf-8 -*-
"""
Модуль установки JavaScript runtime (deno).

Содержит:
- check_deno_installed - проверка наличия deno
- download_deno - автоматическая загрузка deno
"""

import os
import logging
from urllib.request import urlretrieve
from zipfile import ZipFile

logger = logging.getLogger('UI-for-ytdlp.deno')


DENO_DOWNLOAD_URL = 'https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip'


def check_deno_installed(utilities_path: str) -> bool:
    """
    Проверить наличие deno.exe в utilities.

    Args:
        utilities_path: Путь к директории utilities

    Returns:
        True если deno установлен
    """
    deno_path = os.path.join(utilities_path, 'deno.exe')
    exists = os.path.exists(deno_path)
    logger.debug(f"check_deno_installed: {deno_path} -> {exists}")
    return exists


def download_deno(utilities_path: str, callback: callable = None) -> bool:
    """
    Скачать и установить deno.exe.

    Args:
        utilities_path: Путь к директории utilities
        callback: Функция обратного вызова для прогресса

    Returns:
        True если загрузка успешна
    """
    deno_zip_path = os.path.join(utilities_path, 'deno.zip')
    deno_path = os.path.join(utilities_path, 'deno.exe')

    try:
        logger.info(f"Загрузка deno из {DENO_DOWNLOAD_URL}")

        if callback:
            callback("Загрузка deno (JavaScript runtime)...")

        # Загрузка ZIP-архива
        urlretrieve(DENO_DOWNLOAD_URL, deno_zip_path)

        if callback:
            callback("Распаковка deno...")

        # Распаковка
        with ZipFile(deno_zip_path, 'r') as zip_ref:
            zip_ref.extract('deno.exe', utilities_path)

        # Переименование (извлекается как deno.exe)
        extracted_path = os.path.join(utilities_path, 'deno.exe')
        if extracted_path != deno_path:
            os.rename(extracted_path, deno_path)

        # Удаление ZIP
        os.remove(deno_zip_path)

        logger.info(f"deno успешно установлен: {deno_path}")

        if callback:
            callback("deno установлен!")

        return True

    except Exception as e:
        logger.error(f"Ошибка установки deno: {e}")
        if callback:
            callback(f"Ошибка установки deno: {e}")
        return False


def ensure_deno_exists(utilities_path: str, callback: callable = None) -> bool:
    """
    Убедиться что deno существует (проверка + загрузка если нужно).

    Args:
        utilities_path: Путь к директории utilities
        callback: Функция обратного вызова

    Returns:
        True если deno доступен
    """
    if check_deno_installed(utilities_path):
        logger.debug("deno уже установлен")
        return True

    logger.info("deno не найден, попытка загрузки...")
    return download_deno(utilities_path, callback)
