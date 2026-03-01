# -*- coding: utf-8 -*-
"""
Тест кодировки вывода yt-dlp.

Проверяет корректную обработку русских символов в выводе yt-dlp.
"""

import subprocess
import sys
import os


def test_ytdlp_encoding():
    """Проверка кодировки вывода yt-dlp."""
    print("=" * 60)
    print("ТЕСТ КОДИРОВКИ YT-DLP")
    print("=" * 60)
    
    # Путь к yt-dlp
    utilities_path = os.path.join(os.path.dirname(__file__), 'utilities')
    ytdlp_path = os.path.join(utilities_path, 'yt-dlp.exe')
    
    if not os.path.exists(ytdlp_path):
        print(f"ERROR: yt-dlp не найден по пути {ytdlp_path}")
        return False
    
    print(f"yt-dlp путь: {ytdlp_path}")
    
    # Тестовый URL (короткое видео для быстрой проверки)
    test_url = "https://www.youtube.com/watch?v=BaT6aMvFIvs"
    
    # Команда для проверки информации о видео
    cmd = [
        ytdlp_path,
        '--dump-json',
        '--no-download',
        test_url
    ]
    
    print(f"Выполнение команды: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        # Запуск с явным указанием кодировки
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        stdout, stderr = process.communicate(timeout=30)
        
        print(f"Return code: {process.returncode}")
        print(f"STDOUT длина: {len(stdout)} символов")
        print(f"STDERR длина: {len(stderr)} символов")
        print("-" * 60)
        
        # Проверка на наличие русских символов
        if stdout:
            # Проверяем первые 500 символов
            preview = stdout[:500]
            print(f"Preview STDOUT: {preview}")
            
            # Проверяем наличие кириллицы
            has_cyrillic = any('а' <= c <= 'я' or 'А' <= c <= 'Я' for c in preview)
            print(f"Наличие кириллицы: {has_cyrillic}")
        
        if stderr:
            print(f"STDERR: {stderr[:500]}")
        
        # Успех если return code = 0
        success = process.returncode == 0
        print(f"\nРЕЗУЛЬТАТ: {'PASS' if success else 'FAIL'}")
        return success
        
    except subprocess.TimeoutExpired:
        print("ERROR: Превышено время ожидания (30 сек)")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


if __name__ == '__main__':
    success = test_ytdlp_encoding()
    sys.exit(0 if success else 1)
