# -*- coding: utf-8 -*-
"""
Менеджер иконок приложения.

Использует Unicode-символы вместо PNG-файлов для:
- Быстродействия (нет загрузки файлов)
- Масштабируемости (векторное качество)
- Консистентности (единый стиль)
"""

from typing import Optional, Tuple
import customtkinter as ctk

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = None


# ============================================================================
# UNICODE-ИКОНКИ
# ============================================================================
ICONS = {
    # Основные действия
    "download": "⭳",       # Стрелка вниз
    "upload": "⭱",         # Стрелка вверх
    "refresh": "↻",        # Обновление
    "search": "🔍",        # Поиск
    
    # Навигация
    "folder": "📂",        # Папка открытая
    "folder_closed": "📁", # Папка закрытая
    "file": "📄",          # Файл
    "clipboard": "📋",     # Буфер обмена
    
    # Действия
    "paste": "📋",         # Вставить (планшет с зажимом)
    "copy": "🗐",          # Копировать
    "cut": "✂",           # Вырезать
    "clear": "✕",         # Закрыть/очистить
    "check": "✓",         # Подтвердить
    "cancel": "✗",        # Отменить
    "save": "💾",         # Сохранить
    "delete": "🗑",        # Удалить
    "edit": "✎",          # Редактировать
    "settings": "⚙",      # Настройки
    
    # Статусы
    "success": "✓",        # Успех
    "warning": "⚠",        # Предупреждение
    "error": "✕",          # Ошибка
    "info": "ℹ",           # Информация
    
    # SponsorBlock
    "sponsorblock": "🛡",  # Щит
    "shield": "🛡",        # Щит (алиас)

    # Cookies
    "cookies": "🍪",      # Печенье
    "cookie": "🍪",       # Печенье (алиас)

    # Медиа
    "play": "▶",          # Воспроизвести
    "pause": "⏸",         # Пауза
    "stop": "⏹",          # Стоп
    "record": "⏺",        # Запись
    
    # Стрелки
    "arrow_up": "↑",
    "arrow_down": "↓",
    "arrow_left": "←",
    "arrow_right": "→",
    "arrow_expand": "⤢",   # Развернуть
    "arrow_collapse": "⤡", # Свернуть
}


# ============================================================================
# МЕНЕДЖЕР ИКОНОК
# ============================================================================
class IconManager:
    """Менеджер иконок для приложения."""
    
    # Кэш для CTkImage
    _image_cache = {}
    
    @staticmethod
    def get(name: str, default: str = "•") -> str:
        """
        Получить Unicode-символ иконки.
        
        Args:
            name: Имя иконки
            default: Символ по умолчанию если иконка не найдена
            
        Returns:
            Unicode-символ
        """
        return ICONS.get(name, default)
    
    @staticmethod
    def get_aliased(name: str, default: str = "•") -> str:
        """
        Получить иконку с учётом алиасов.
        
        Args:
            name: Имя иконки
            default: Символ по умолчанию
            
        Returns:
            Unicode-символ
        """
        # Проверка алиасов
        aliases = {
            "sponsorblock": "shield",
            "close": "clear",
            "exit": "clear",
            "confirm": "check",
            "done": "check",
        }
        
        if name in ICONS:
            return ICONS[name]
        elif name in aliases:
            return ICONS.get(aliases[name], default)
        else:
            return default
    
    @staticmethod
    def create_ctk_image(
        name: str,
        size: Tuple[int, int] = (20, 20),
        color: str = "#E3E5E8",
        bg_color: str = "transparent"
    ) -> Optional[ctk.CTkImage]:
        """
        Создать CTkImage из Unicode-символа.
        
        Args:
            name: Имя иконки
            size: Размер (ширина, высота)
            color: Цвет иконки
            bg_color: Цвет фона
            
        Returns:
            CTkImage или None если PIL недоступен
        """
        if not PIL_AVAILABLE:
            return None
        
        cache_key = f"{name}_{size}_{color}_{bg_color}"
        if cache_key in IconManager._image_cache:
            return IconManager._image_cache[cache_key]
        
        try:
            # Создание изображения
            img = Image.new('RGBA', size, (0, 0, 0, 0) if bg_color == "transparent" else tuple(int(bg_color[i:i+2], 16) for i in (1, 3, 5)))
            draw = ImageDraw.Draw(img)
            
            # Получение символа
            symbol = IconManager.get(name, "•")
            
            # Попытка использовать шрифт
            try:
                # Пробуем разные размеры шрифта
                for font_size in range(24, 8, -2):
                    try:
                        font = ImageFont.truetype("seguiemj.ttf", font_size)  # Emoji шрифт Windows
                        break
                    except:
                        try:
                            font = ImageFont.truetype("arial.ttf", font_size)
                            break
                        except:
                            font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # Центрирование текста
            bbox = draw.textbbox((0, 0), symbol, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (size[0] - text_width) // 2 - bbox[0]
            y = (size[1] - text_height) // 2 - bbox[1]
            
            # Отрисовка
            draw.text((x, y), symbol, fill=tuple(int(color[i:i+2], 16) for i in (1, 3, 5)) + (255,), font=font)
            
            # Создание CTkImage
            ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=size)
            IconManager._image_cache[cache_key] = ctk_image
            
            return ctk_image
            
        except Exception as e:
            print(f"Error creating icon {name}: {e}")
            return None
    
    @staticmethod
    def clear_cache() -> None:
        """Очистить кэш изображений."""
        IconManager._image_cache.clear()


# ============================================================================
# УПРОЩЁННЫЕ ФУНКЦИИ
# ============================================================================
def icon(name: str, default: str = "•") -> str:
    """Краткая форма для получения иконки."""
    return IconManager.get(name, default)


def icon_button_text(name: str) -> str:
    """Получить текст для кнопки-иконки."""
    return IconManager.get_aliased(name, "")
