<div align="center">
    <h1>UI-for-ytdlp</h1>
    <img src="https://raw.githubusercontent.com/Jawerka/shell-for-ytdlp/master/icon.png" alt="UI-for-ytdlp icon" width="200" height="200" />
</div>

**Modern GUI for yt-dlp built with customtkinter.**

![Version](https://img.shields.io/badge/version-1.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

### Основные возможности:
- 📥 Загрузка видео с YouTube и других поддерживаемых сайтов
- 📊 Загрузка плейлистов
- 🛡️ Автоматическое удаление спонсорских вставок (SponsorBlock)
- ⏭️ Продолжение прерванных загрузок
- 🍪 Поддержка cookies.txt
- 📋 Авто-определение URL из буфера обмена (интервал ~2 с, главный поток Tk)
- 🔔 Звуковые уведомления (начало/завершение загрузки)
- 🖼️ Сворачивание в системный трей (кнопка «Свернуть»; крестик — выход)
- 🎨 Современный тёмный интерфейс
- 💾 Сохранение позиции окон между запусками

### Системный трей:
- **Свернуть** — окно скрывается, иконка в области уведомлений
- **ЛКМ / «Показать окно»** — восстановление окна
- **ПКМ** — меню: перехват буфера, звуки, вставить и скачать, настройки, выход
- **Крестик (X)** — полное закрытие приложения (иконка удаляется из трея)

---

## 📦 Установка

### Готовый exe-файл:
- Скачать [последнюю версию](https://github.com/Jawerka/shell-for-ytdlp/releases/latest/download/UI-for-ytdlp.exe)
- Разместить в удобной папке
- Запустить

При первом запуске `yt-dlp` и `ffmpeg` будут загружены в папку `./utilities`.

---

## 🍪 Cookies

Для получения cookies из браузера используйте расширения:
- [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) для Chrome
- [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) для Firefox

Поместите полученный `cookies.txt` в папку `utilities` — приложение автоматически начнёт его использовать.

---

## 💻 Использование скрипта

### Требования:
- [Python 3.10+](https://www.python.org/downloads/)

### Установка зависимостей:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Запуск:
```bash
python main.py
```

Подробное логирование: `UI_FOR_YTDLP_DEBUG=1 python main.py` (Windows: `set UI_FOR_YTDLP_DEBUG=1`).

### Буфер обмена:
Включите «Перехват ссылок из буфера» в настройках. При копировании поддерживаемого URL приложение автоматически начнёт загрузку.

---

## 🏗️ Сборка exe-файла

### Через build.py:
```bash
python build.py
```

### Через PyInstaller вручную:
```bash
python -m venv venv
venv/Scripts\activate
python -m pip install -r requirements.txt --no-cache-dir

pyinstaller --clean --noconfirm UI-for-ytdlp.spec
```

Готовый файл: `dist/UI-for-ytdlp.exe`

---

## 📁 Структура проекта

```
UI-for-ytdlp/
├── main.py                 # Точка входа
├── build.py                # Скрипт сборки
├── UI-for-ytdlp.spec       # Spec-файл PyInstaller
├── requirements.txt        # Зависимости Python
├── README.md               # Документация
├── .gitignore              # Git ignore
├── icon.ico                # Иконка приложения (окно + трей)
├── icon.png                # Баннер README
├── core/                   # Ядро приложения
│   ├── theme.py            # Дизайн-система и цвета
│   ├── icons.py            # Менеджер иконок
│   ├── utils.py            # Утилиты (URL, буфер обмена)
│   ├── logger.py           # Логгер для GUI
│   ├── config.py           # Менеджер конфигурации
│   ├── downloader.py       # Загрузчик через yt-dlp
│   ├── updater.py          # Обновление утилит
│   ├── notifications.py    # Системные уведомления
│   ├── sound_manager.py    # Звуковые эффекты
│   ├── clipboard_monitor.py # Мониторинг буфера обмена
│   ├── tray_manager.py     # Системный трей
│   └── deno_installer.py   # Установка deno (опционально)
├── ui/                     # Пользовательский интерфейс
│   ├── main_window.py      # Главное окно
│   ├── layout_config.py    # Настройки разметки UI
│   ├── tooltip.py          # Всплывающие подсказки
│   ├── sfx/                # Звуковые файлы (start/end)
│   └── components/         # UI компоненты
│       ├── url_input.py
│       ├── log_viewer.py
│       ├── progress_bar.py
│       └── settings_dialog.py
├── utilities/              # Утилиты (загружаются автоматически)
│   ├── yt-dlp.exe
│   ├── ffmpeg.exe
│   └── cookies.txt         # опционально
└── tests/                  # Тесты
    ├── conftest.py
    └── unit/
```

---

## 🎨 Дизайн-система

### Цветовая палитра:
| Цвет | Значение | Hex |
|------|----------|-----|
| Primary | Основной акцент | `#00A8E8` |
| Primary Hover | При наведении | `#0096D0` |
| Background | Фон окна | `#141517` |
| Card | Фон карточек | `#1E1F22` |
| Border | Обводка | `#3A3D42` |
| Text | Основной текст | `#E3E5E8` |
| Text Muted | Приглушённый текст | `#9CA0A6` |

### Размеры элементов:
| Элемент | Размер |
|---------|--------|
| Кнопки | 42×40 px |
| Поле URL | 340×42 px |
| Поле пути | 380×28 px |
| Прогресс-бар | 50 px высота |

### Скругления:
- Все элементы: **14px**

### Отступы (Spacing):
- XS: 4px, SM: 8px, MD: 11px, LG: 16px, XL: 24px, XXL: 32px

---

## ⚠️ Известные проблемы:
- При загрузке в папку с пробелами в пути могут возникнуть проблемы (планируется исправление)

---

## 🧪 Тестирование

### Запуск тестов:
```bash
# Unit-тесты (без yt-dlp.exe)
pytest tests/ -v -m "not integration"

# С покрытием
pytest tests/ -v -m "not integration" --cov=core --cov=ui

# Integration (нужен utilities/yt-dlp.exe)
pytest tests/ -v -m integration
```

### Покрытие тестами:
- `test_config.py` — конфигурация
- `test_utils.py` — URL, `extract_video_url`, буфер обмена
- `test_clipboard_monitor.py` — мониторинг буфера
- `test_tray_manager.py` — lifecycle трея
- `test_tray_minimize.py` — логика сворачивания
- `test_encoding.py` — кодировка (integration, требует yt-dlp)
- `test_sound_manager.py` — звуки
- `test_downloader.py` — загрузчик
- `test_updater.py` — обновления

---

## 🔗 Используемые ресурсы:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://github.com/FFmpeg/FFmpeg)
- [SponsorBlock](https://wiki.sponsor.ajay.app/)
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter)
- [pygame](https://github.com/pygame-community/pygame-ce) — звуковые уведомления
- [pystray](https://github.com/moses-palmer/pystray) — системный трей
- [pyperclip](https://github.com/asweigart/pyperclip) — буфер обмена

---

## 📝 Changelog

### v1.1 (2026-06-29)
- 🖼️ Стабильный системный трей: один lifecycle pystray, safe exit, надёжное сворачивание
- 📋 Надёжный мониторинг буфера: polling в главном потоке, `extract_video_url`, retry
- 🧹 Аудит кода: удалён мёртвый код, исправлены тесты, pytest в CI
- 📝 Обновлена документация

### v1.0 (2026-03-06)
- 💾 Сохранение позиции окон между запусками
- 🔧 Тултипы с задержкой 3000мс
- 🎨 Компактная секция автоматизации в настройках
- 🛠️ Улучшена инициализация размеров окон
- 📝 Обновлена документация

### v1.0 (2026-03-01)
- ✨ Мониторинг буфера обмена с автозагрузкой
- 🔔 Звуковые уведомления (начало/завершение загрузки)
- 🛡️ Защита от повторной загрузки URL
- 🔧 Улучшена обработка ошибок ffmpeg
- 🐛 Исправлено зависание при некорректных данных в буфере
- 🐛 Исправлена кодировка вывода yt-dlp
- 📝 Обновлена документация

### v0.9 (2026-02-23)
- ✨ Полный рефакторинг архитектуры
- 🎨 Дизайн-система с голубыми акцентами
- 🔤 Unicode-иконки вместо PNG
- 📦 Модульная структура (core/, ui/)
- 📏 Система отступов Spacing
- 🛠️ Улучшена обработка ошибок
