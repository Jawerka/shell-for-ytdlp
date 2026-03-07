<div align="center">
    <h1>UI-for-ytdlp</h1>
    <img src="https://raw.githubusercontent.com/Jawerka/UI-for-ytdlp/main/icon.png" alt="UI-for-ytdlp icon" width="200" height="200" />
</div>

**Modern GUI for yt-dlp built with customtkinter.**

![Version](https://img.shields.io/badge/version-1.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

### Основные возможности:
- 📥 Загрузка видео с YouTube и других поддерживаемых сайтов
- 📊 Загрузка плейлистов
- 🛡️ Автоматическое удаление спонсорских вставок (SponsorBlock)
- ⏭️ Продолжение прерванных загрузок
- 🍪 Поддержка cookies.txt
- 📋 Авто-определение URL из буфера обмена
- 🔔 Звуковые уведомления (начало/завершение загрузки)
- 🎨 Современный тёмный интерфейс
- 💾 Сохранение позиции окон между запусками

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
├── README.md              # Документация
├── .gitignore             # Git ignore
├── icon.ico               # Иконка приложения
├── core/                  # Ядро приложения
│   ├── theme.py           # Дизайн-система и цвета
│   ├── icons.py           # Менеджер иконок
│   ├── utils.py           # Утилиты (валидация URL, буфер обмена)
│   ├── logger.py          # Логгер для GUI
│   ├── config.py          # Менеджер конфигурации
│   ├── downloader.py      # Загрузчик через yt-dlp
│   ├── updater.py         # Обновление утилит
│   ├── notifications.py   # Системные уведомления
│   ├── sound_manager.py   # Звуковые эффекты
│   ├── clipboard_monitor.py # Мониторинг буфера обмена
│   └── deno_installer.py  # Установка deno (опционально)
├── ui/                    # Пользовательский интерфейс
│   ├── main_window.py     # Главное окно
│   ├── layout_config.py   # Настройки разметки UI
│   ├── tooltip.py         # Всплывающие подсказки
│   └── components/        # UI компоненты
│       ├── url_input.py   # Поле ввода URL
│       ├── log_viewer.py  # Просмотр логов
│       ├── progress_bar.py # Прогресс-бар
│       └── settings_dialog.py # Диалог настроек
├── utilities/             # Утилиты (загружаются автоматически)
│   ├── yt-dlp.exe        # yt-dlp
│   ├── ffmpeg.exe        # ffmpeg
│   └── cookies.txt       # Cookies (опционально)
└── tests/                 # Тесты
    ├── conftest.py       # Конфигурация pytest
    └── unit/             # Модульные тесты
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
# Запустить все тесты
pytest tests/ -v

# Запустить тесты с покрытием
pytest tests/ -v --cov=core --cov=ui

# Запустить конкретный тест
pytest tests/unit/test_encoding.py -v
```

### Покрытие тестами:
- `test_config.py` — тесты конфигурации
- `test_utils.py` — тесты утилит (валидация URL, буфер обмена)
- `test_encoding.py` — тесты кодировки
- `test_clipboard_monitor.py` — тесты мониторинга буфера
- `test_sound_manager.py` — тесты звукового менеджера
- `test_downloader.py` — тесты загрузчика
- `test_updater.py` — тесты обновлений

---

## 🔗 Используемые ресурсы:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://github.com/FFmpeg/FFmpeg)
- [SponsorBlock](https://wiki.sponsor.ajay.app/)
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter)
- [pygame](https://github.com/pygame-community/pygame-ce) — звуковые уведомления

---

## 📝 Changelog

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
