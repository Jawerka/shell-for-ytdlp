# -*- coding: utf-8 -*-
"""
Тест кодировок для GUI.
"""

import sys
import os

# Добавляем корень проекта
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Устанавливаем кодировку UTF-8 для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import customtkinter as ctk
from core.logger import GUILogger
from core.theme import setup_theme

# Тестовый текст на русском
test_texts = [
    "Привет мир! Это тестовое сообщение.",
    "Загрузка файла: тест_видео.mp4",
    "Путь: D:\\Documents\\Projects\\python\\UI-for-ytdlp",
    "Ошибка: Файл не найден",
    "250 ПОЯСНЕНИЙ С ТВЕРДОЙ ТРОЙКИ ЗА 10 МИНУТ НА НОУТБУКЕ",
]

class EncodingTestWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        setup_theme()
        
        self.title("Тест кодировок")
        self.geometry("800x600")
        
        self.logger = GUILogger()
        
        # Создаём текстовое поле
        self.text_widget = ctk.CTkTextbox(self, width=750, height=500)
        self.text_widget.pack(padx=20, pady=20)
        
        # Тестируем разные подходы
        self.test_approaches()
    
    def test_approaches(self):
        """Тест разных подходов к кодировке."""
        
        self.text_widget.insert("1.0", "=" * 60 + "\n")
        self.text_widget.insert("end", "ТЕСТ КОДИРОВОК В GUI\n")
        self.text_widget.insert("end", "=" * 60 + "\n\n")
        
        # Подход 1: Прямой UTF-8 текст
        self.text_widget.insert("end", "1. Прямой UTF-8 текст:\n")
        self.text_widget.insert("end", "-" * 60 + "\n")
        for text in test_texts:
            self.text_widget.insert("end", f"  {text}\n")
        self.text_widget.insert("end", "\n")
        
        # Подход 2: Через logger (с encode/decode)
        self.text_widget.insert("end", "2. Через logger (encode/decode utf-8):\n")
        self.text_widget.insert("end", "-" * 60 + "\n")
        for text in test_texts:
            self.logger.info(text)
        for formatted, level in self.logger.get_logs():
            self.text_widget.insert("end", f"  [{level.value}] {formatted}\n")
        self.text_widget.insert("end", "\n")
        
        # Подход 3: Без encode/decode
        self.text_widget.insert("end", "3. Без encode/decode (чистый UTF-8):\n")
        self.text_widget.insert("end", "-" * 60 + "\n")
        logger2 = GUILogger()
        # Временно отключаем encode/decode в _log
        for text in test_texts:
            logger2._log(text, logger2.INFO)
        for formatted, level in logger2.get_logs():
            self.text_widget.insert("end", f"  {formatted}\n")
        self.text_widget.insert("end", "\n")
        
        # Подход 4: С явной кодировкой cp1251
        self.text_widget.insert("end", "4. С кодировкой cp1251:\n")
        self.text_widget.insert("end", "-" * 60 + "\n")
        for text in test_texts:
            try:
                cp1251_text = text.encode('cp1251', errors='replace').decode('cp1251')
                self.text_widget.insert("end", f"  cp1251: {cp1251_text}\n")
            except Exception as e:
                self.text_widget.insert("end", f"  Ошибка: {e}\n")
        self.text_widget.insert("end", "\n")
        
        self.text_widget.insert("end", "=" * 60 + "\n")
        self.text_widget.insert("end", "ТЕСТ ЗАВЕРШЁН\n")
        self.text_widget.insert("end", "=" * 60 + "\n")

if __name__ == '__main__':
    app = EncodingTestWindow()
    app.mainloop()
