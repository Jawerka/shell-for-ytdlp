# -*- coding: utf-8 -*-
"""
Модуль обновления утилит.

Содержит функции для:
- Обновления yt-dlp и ffmpeg
- Распаковки ffmpeg из ZIP-архива
"""

import os
import shutil
import logging
from typing import Callable, Optional, List
from zipfile import ZipFile, BadZipFile
from urllib.request import urlopen, urlretrieve
from urllib.error import HTTPError, URLError

# Логгер для отладки
logger = logging.getLogger('UI-for-ytdlp.updater')

FFMPEG_FILE_LIST = ['ffmpeg.exe', 'ffplay.exe', 'ffprobe.exe']


def _parse_content_length(response) -> Optional[int]:
    """Безопасно прочитать Content-Length из HTTP-ответа."""
    header = response.getheader('Content-Length')
    if header is None:
        return None
    try:
        return int(str(header).strip())
    except (ValueError, TypeError):
        return None


def _is_ffmpeg_zip(save_name: str) -> bool:
    return 'zip' in save_name and 'ffmpeg' in save_name


def ffmpeg_extracted(work_path: str) -> bool:
    """Проверить, что все бинарники ffmpeg распакованы в utilities."""
    return all(
        os.path.exists(os.path.join(work_path, ff_file))
        for ff_file in FFMPEG_FILE_LIST
    )


def unzipping_ffmpeg(archive_path: str, utilities_path: str) -> None:
    """
    Распаковать ffmpeg из ZIP-архива.

    Args:
        archive_path: Путь к ZIP-архиву
        utilities_path: Путь к директории утилит

    Raises:
        BadZipFile: Архив повреждён или не является zip-файлом
    """
    logger.debug(f"unzipping_ffmpeg: archive={archive_path}, utilities={utilities_path}")

    ffmpeg_folder_name = os.path.basename(archive_path).split('.')[0]
    ffmpeg_folder_path = os.path.join(utilities_path, ffmpeg_folder_name)
    bin_path = os.path.join(ffmpeg_folder_path, 'bin')

    # Удаление старых файлов
    for ff_file in FFMPEG_FILE_LIST:
        ff_file_path = os.path.join(utilities_path, ff_file)
        if os.path.exists(ff_file_path):
            logger.debug(f"unzipping_ffmpeg: Удаление старого {ff_file}")
            os.remove(ff_file_path)

    # Удаление старой папки
    if os.path.exists(ffmpeg_folder_path):
        logger.debug(f"unzipping_ffmpeg: Удаление папки {ffmpeg_folder_path}")
        shutil.rmtree(ffmpeg_folder_path)

    # Распаковка архива
    logger.debug("unzipping_ffmpeg: Распаковка архива")
    with ZipFile(archive_path, 'r') as zfile:
        bad_file = zfile.testzip()
        if bad_file is not None:
            raise BadZipFile(f"Повреждённый файл в архиве: {bad_file}")
        zfile.extractall(utilities_path)

    # Перемещение файлов
    for ff_file in FFMPEG_FILE_LIST:
        src = os.path.join(bin_path, ff_file)
        dst = os.path.join(utilities_path, ff_file)
        if os.path.exists(src):
            logger.debug(f"unzipping_ffmpeg: Перемещение {ff_file}")
            shutil.move(src, dst)

    # Удаление папки распаковки
    if os.path.exists(ffmpeg_folder_path):
        shutil.rmtree(ffmpeg_folder_path)

    logger.debug("unzipping_ffmpeg: Завершено")


def _try_unzip_ffmpeg(archive_path: str, work_path: str) -> bool:
    """
    Распаковать ffmpeg и проверить результат.

    Returns:
        True если все exe на месте после распаковки
    """
    try:
        unzipping_ffmpeg(archive_path, work_path)
    except BadZipFile as e:
        logger.error(f"_try_unzip_ffmpeg: Повреждённый архив {archive_path}: {e}")
        return False
    except OSError as e:
        logger.error(f"_try_unzip_ffmpeg: Ошибка распаковки {archive_path}: {e}")
        return False

    if not ffmpeg_extracted(work_path):
        missing = [
            ff_file for ff_file in FFMPEG_FILE_LIST
            if not os.path.exists(os.path.join(work_path, ff_file))
        ]
        logger.error(f"_try_unzip_ffmpeg: После распаковки отсутствуют: {missing}")
        return False

    return True


def check_needs_update(url: str, save_path: str) -> bool:
    """
    Проверить, требуется ли обновление.
    Сравнивает размер файла с размером на сервере.

    Args:
        url: URL для проверки
        save_path: Путь к локальному файлу

    Returns:
        True если требуется обновление
    """
    save_name = os.path.basename(save_path)

    # Если файла нет - нужно скачивать
    if not os.path.exists(save_path):
        logger.debug(f"check_needs_update: {save_name} не найден, требуется загрузка")
        return True

    try:
        response = urlopen(url, timeout=10)
        remote_size = _parse_content_length(response)
        if remote_size is None:
            logger.warning(
                f"check_needs_update: Content-Length отсутствует для {save_name}, "
                "считаем что обновление не требуется"
            )
            return False

        local_size = os.path.getsize(save_path)
        needs_update = remote_size != local_size

        logger.debug(f"check_needs_update: {save_name}")
        logger.debug(f"  Локальный размер: {local_size:,} байт")
        logger.debug(f"  Удалённый размер: {remote_size:,} байт")
        logger.debug(f"  Требуется обновление: {needs_update}")

        return needs_update

    except (HTTPError, URLError, OSError) as e:
        logger.warning(f"check_needs_update: Ошибка проверки {save_name}: {e}")
        # При ошибке проверки считаем что обновление не требуется
        return False


def update_utilities(
    upd_url: str,
    work_path: str,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> bool:
    """
    Обновить/скачать утилиту.

    Args:
        upd_url: URL для скачивания
        work_path: Рабочая директория
        progress_callback: Функция обратного вызова прогресса

    Returns:
        True если файл был скачан/обновлён
    """
    save_name = os.path.basename(upd_url)
    save_path = os.path.join(work_path, save_name)

    logger.debug(f"update_utilities: Начало для {save_name}")

    try:
        # Получаем размер файла на сервере
        response = urlopen(upd_url, timeout=10)
        download_file_size = _parse_content_length(response)
        if download_file_size is not None:
            logger.debug(f"update_utilities: Размер на сервере: {download_file_size:,} байт")
        else:
            logger.debug("update_utilities: Content-Length отсутствует на сервере")

        # Проверка существующего файла
        if os.path.exists(save_path):
            local_size = os.path.getsize(save_path)
            logger.debug(f"update_utilities: Локальный размер: {local_size:,} байт")

            # Если это ffmpeg — проверяем наличие unpacked файлов
            if _is_ffmpeg_zip(save_name):
                if ffmpeg_extracted(work_path):
                    logger.debug("update_utilities: ffmpeg уже распакован, пропускаем")
                    return False

                logger.debug("update_utilities: ffmpeg архив найден, но не распакован")
                if _try_unzip_ffmpeg(save_path, work_path):
                    return True

                logger.warning("update_utilities: Не удалось распаковать ffmpeg, перекачиваем архив")
                os.remove(save_path)

            # Для yt-dlp — проверяем размер
            elif download_file_size is not None and local_size == download_file_size:
                logger.debug(f"update_utilities: {save_name} актуален, пропускаем")
                return False
            elif download_file_size is not None:
                logger.debug(f"update_utilities: {save_name} устарел, загружаем заново")
                os.remove(save_path)
        else:
            logger.debug(f"update_utilities: {save_name} не найден, загружаем")

        # Callback для прогресса
        def _progress_hook(uploaded, chunk, total):
            if progress_callback:
                progress_callback(uploaded * chunk, total)

        # Скачивание
        logger.debug(f"update_utilities: Начало загрузки {save_name}")
        urlretrieve(upd_url, save_path, reporthook=_progress_hook)
        logger.debug("update_utilities: Загрузка завершена")

        # Распаковка ffmpeg
        if _is_ffmpeg_zip(save_name):
            logger.debug("update_utilities: Распаковка ffmpeg")
            if not _try_unzip_ffmpeg(save_path, work_path):
                logger.error("update_utilities: Не удалось распаковать скачанный ffmpeg")
                return False

        logger.debug(f"update_utilities: {save_name} обновлён успешно")
        return True

    except (HTTPError, URLError, OSError, BadZipFile, ValueError, AttributeError) as e:
        logger.error(f"update_utilities: Ошибка загрузки {save_name}: {e}")
        return False
    except KeyboardInterrupt:
        logger.warning("update_utilities: Прервано пользователем")
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except OSError:
                pass
        raise


def update_loop(
    url_list: List[str],
    utilities_path: str,
    progress_callback: Optional[Callable[[str, int, int], None]] = None
) -> None:
    """
    Цикл обновления всех утилит.

    Args:
        url_list: Список URL для обновления
        utilities_path: Путь к директории утилит
        progress_callback: Функция обратного вызова прогресса
    """
    logger.debug(f"update_loop: Начало обновления, утилиты: {utilities_path}")
    os.makedirs(utilities_path, exist_ok=True)

    for url in url_list:
        save_name = os.path.basename(url)
        logger.debug(f"update_loop: Обработка {save_name}")

        def _progress_wrapper(uploaded, total, fn=save_name):
            if progress_callback:
                progress_callback(fn, uploaded, total)

        update_utilities(url, utilities_path, _progress_wrapper)

    logger.debug("update_loop: Завершено")
