<div align="center">
    <h1>UI-for-ytdlp</h1>
    <img src="https://github.com/Jawerka/shell-for-ytdlp/blob/master/icon.png?raw=true" alt="UI-for-ytdlp icon" width="200" height="200" />
</div>

**Modern GUI for yt-dlp built with customtkinter.**

---

## ✨ Features

### Основные возможности:
- 📥 Загрузка видео с YouTube и других поддерживаемых сайтов
- 📊 Загрузка плейлистов
- 🛡️ Автоматическое удаление спонсорских вставок (SponsorBlock)
- ⏭️ Продолжение прерванных загрузок
- 🍪 Поддержка cookies.txt
- 📋 Авто-определение URL из буфера обмена
- 🎨 Современный тёмный интерфейс

### 🎯 Улучшения (v2.0):
- **Дизайн-система**: Единый стиль скруглений (8px), обводки (1px, #3A3D42)
- **Цветовая палитра**: Голубые акценты (#00A8E8) вместо синих
- **Векторные иконки**: Unicode-символы вместо PNG-файлов
- **Модульная архитектура**: Разделение на `core/` и `ui/` модули
- **Система отступов**: Все отступы кратны 4px

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
├── core/                   # Ядро приложения
│   ├── theme.py           # Дизайн-система
│   ├── icons.py           # Менеджер иконок
│   ├── utils.py           # Утилиты
│   ├── logger.py          # Логгер
│   ├── config.py          # Конфигурация
│   ├── downloader.py      # Загрузчик
│   └── updater.py         # Обновления
├── ui/                     # Пользовательский интерфейс
│   ├── main_window.py     # Главное окно
│   └── components/        # UI компоненты
├── resources/              # Ресурсы
└── utilities/              # Утилиты (yt-dlp, ffmpeg)
```

---

## 🎨 Дизайн-система

### Цветовая палитра:
| Цвет | Значение | Описание |
|------|----------|----------|
| Primary | `#00A8E8` | Голубой акцент |
| Primary Hover | `#0096D0` | При наведении |
| Background | `#141517` | Основной фон |
| Card | `#1E1F22` | Фон карточек |
| Border | `#3A3D42` | Обводка |
| Text | `#E3E5E8` | Основной текст |

### Скругления:
- Все элементы: **8px**

### Отступы:
- XS: 4px, SM: 8px, MD: 12px, LG: 16px, XL: 24px, XXL: 32px

---

## ⚠️ Известные проблемы:
- Нет поддержки пробелов в пути запуска (будет исправлено)

---

## 🔗 Используемые ресурсы:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://github.com/FFmpeg/FFmpeg)
- [SponsorBlock](https://wiki.sponsor.ajay.app/)
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter)

---

## 📝 Changelog

### v2.0 (2026-02-23)
- ✨ Полный рефакторинг архитектуры
- 🎨 Новая дизайн-система с голубыми акцентами
- 🔤 Unicode-иконки вместо PNG
- 📦 Модульная структура (core/, ui/)
- 📏 Система отступов Spacing
- 🛠️ Улучшена обработка ошибок

### v1.0
- Базовая версия
