# -*- coding: utf-8 -*-
"""
Тест вывода yt-dlp с разными кодировками.
"""

import subprocess
import sys
import os

# Тестовый URL (короткий)
TEST_URL = "https://www.youtube.com/watch?v=YODP2a9TS2I"

def test_ytdlp_encodings():
    """Тест разных подходов к кодировке вывода yt-dlp."""
    
    print("=" * 60)
    print("ТЕСТ КОДИРОВОК YT-DLP")
    print("=" * 60)
    
    # Находим yt-dlp
    ytdlp_path = r".\utilities\yt-dlp.exe"
    if not os.path.exists(ytdlp_path):
        print(f"yt-dlp не найден: {ytdlp_path}")
        return
    
    print(f"\nyt-dlp путь: {ytdlp_path}")
    print(f"sys.stdout.encoding: {sys.stdout.encoding}")
    print(f"sys.getdefaultencoding(): {sys.getdefaultencoding()}")
    
    # Тест 1: UTF-8 с errors='replace'
    print("\n" + "=" * 60)
    print("ТЕСТ 1: UTF-8 с errors='replace' (как сейчас в коде)")
    print("=" * 60)
    try:
        cmd = [
            ytdlp_path,
            "--simulate",  # Не скачивать
            "--print", "title",  # Только название
            TEST_URL
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    # Тест 2: UTF-8 с errors='ignore'
    print("\n" + "=" * 60)
    print("ТЕСТ 2: UTF-8 с errors='ignore'")
    print("=" * 60)
    try:
        cmd = [
            ytdlp_path,
            "--simulate",
            "--print", "title",
            TEST_URL
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    # Тест 3: Без указания encoding (по умолчанию)
    print("\n" + "=" * 60)
    print("ТЕСТ 3: Без указания encoding (по умолчанию)")
    print("=" * 60)
    try:
        cmd = [
            ytdlp_path,
            "--simulate",
            "--print", "title",
            TEST_URL
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    # Тест 4: cp866 (OEM кодировка Windows)
    print("\n" + "=" * 60)
    print("ТЕСТ 4: cp866 (OEM кодировка консоли)")
    print("=" * 60)
    try:
        cmd = [
            ytdlp_path,
            "--simulate",
            "--print", "title",
            TEST_URL
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='cp866',
            errors='replace'
        )
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    # Тест 5: cp1251 (Windows Cyrillic)
    print("\n" + "=" * 60)
    print("ТЕСТ 5: cp1251 (Windows Cyrillic)")
    print("=" * 60)
    try:
        cmd = [
            ytdlp_path,
            "--simulate",
            "--print", "title",
            TEST_URL
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='cp1251',
            errors='replace'
        )
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    # Тест 6: binary decode
    print("\n" + "=" * 60)
    print("ТЕСТ 6: Binary + decode utf-8")
    print("=" * 60)
    try:
        cmd = [
            ytdlp_path,
            "--simulate",
            "--print", "title",
            TEST_URL
        ]
        result = subprocess.run(
            cmd,
            capture_output=True
        )
        # Пробуем декодировать как UTF-8
        try:
            text = result.stdout.decode('utf-8')
            print(f"UTF-8 decode:\n{text}")
        except UnicodeDecodeError as e:
            print(f"UTF-8 decode error: {e}")
            # Пробуем cp1251
            try:
                text = result.stdout.decode('cp1251')
                print(f"cp1251 decode:\n{text}")
            except Exception as e2:
                print(f"cp1251 decode error: {e2}")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    print("\n" + "=" * 60)
    print("ТЕСТ ЗАВЕРШЁН")
    print("=" * 60)

if __name__ == '__main__':
    test_ytdlp_encodings()
