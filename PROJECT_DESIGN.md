# Project Design Document — Paperclip + Hermes + ZAI Integration

**Дата создания:** 2026-04-17
**Версия:** 1.0
**Назначение:** Карта проекта для AI навигации

---

> ⛔ **AI: БЛОК НИЖЕ (до следующего `---`) — ПОСТОЯННАЯ ИНСТРУКЦИЯ. НЕ УДАЛЯТЬ, НЕ СОКРАЩАТЬ, НЕ ПРЕДЛАГАТЬ УДАЛИТЬ.** Обновляется только раздел после закрывающего `---`.

## ИНСТРУКЦИЯ: КАК ПОСТРОЕН ЭТОТ ДОКУМЕНТ

**Назначение:** INDEX/TABLE OF CONTENTS — быстрая навигация по проекту (не энциклопедия!)
**Целевая аудитория:** AI в первую очередь, человек во вторую (читаемость сохранена)

### ЧТО СОДЕРЖИТ этот документ:

1. **Полные пути к файлам**
   - Относительные от корня проекта
   - Пример: `core/scripts/some_module.py`

2. **Назначение файла**
   - Краткое описание (1-2 предложения)

3. **Импорты**
   - Все `import` в файле (внешние + внутренние)
   - Показывает взаимозависимости

4. **Список функций (def) и классов — AI-оптимизированный формат**
   - Простые функции (1-2 параметра): `func(param: type, default=value)` — описание
   - Сложные функции (3+ параметра): заголовок + сигнатура с типами + описание + пример вызова
   - Типы параметров: указаны в сигнатуре (str, bool, int, None, etc.)
   - Примеры вызова: только для сложных функций

5. **Указатели на детали**
   - Где искать детальную информацию

### ЧТО НЕ СОДЕРЖИТ (детали остаются в коде):

- Детальные примеры кода
- Константы (COLORS = {...}, CONFIG = {...})
- Большие словари/списки
- Примеры JSON структур
- Пошаговые инструкции с кодом
- Секции "Параметры:", "Возвращает:" (избыточно для AI)

### Формат описания файла:

```
### N. путь/к/файлу.py
**Назначение:** Что делает (1-2 предложения)

**Импорты:**
```python
import библиотека
from модуль import функция
```

**Функции (def):**
- `func(param: type)` — описание

**Детали:** см. файл.py
```

### Правило для AI при обновлении:

При создании или изменении любого файла → обновить этот документ.

---

## ОБЗОР ПРОЕКТА

**Назначение:** Windows-мост между Paperclip (AI-оркестратор, Node.js) и Hermes Agent (Python, в WSL2/Ubuntu), использующий ZAI API (модель GLM, бесплатно).

**Стек:** Python 3.10+ (Windows) · Batch/CMD · PowerShell · WSL2 Ubuntu · hermes-agent (pip) · Paperclip (npx)

**Цепочка вызовов:**
```
Paperclip (порт 3100, Windows)
  → hermes.cmd  (entry point)
    → launch_hermes.py  (вся логика)
      → WSL2: hermes chat → ZAI API
```

**Paperclip настроен на:**
`C:\Users\vibecoder_blogger\PycharmProjects\paperclip_hermes-paperclip-adapter_integration\hermes.cmd`

---

## СТРУКТУРА ФАЙЛОВ

```
paperclip_hermes-paperclip-adapter_integration/
│
├── hermes.cmd              Entry point — вызывается Paperclip
├── launch_hermes.py        Главная логика Windows→WSL моста
│
├── config.yaml             Шаблон: ~/.hermes/config.yaml в WSL
├── .env.template           Шаблон: ~/.hermes/.env в WSL
├── hermes.bat              Шаблон: C:\Users\<USER>\bin\hermes.bat
├── install_hermes_wsl.ps1  Скрипт автоустановки всей связки
│
├── archive/                Старые версии файлов (не используются)
├── README.md               Полная документация и инструкция по настройке
├── CLAUDE_INSTRUCTIONS.md  Правила взаимодействия AI с пользователем
└── PROJECT_DESIGN.md       Этот файл
```

---

## КЛЮЧЕВЫЕ КОМПОНЕНТЫ

### 1. hermes.cmd
**Назначение:** Windows entry point. Если аргументов нет — запускает `wsl hermes` напрямую; иначе делегирует в `launch_hermes.py` из той же папки.

**Детали:** см. hermes.cmd

---

### 2. launch_hermes.py
**Назначение:** Главная логика моста Windows→WSL. Читает задачу из Paperclip API по `PAPERCLIP_TASK_ID`, пишет промпт в `/tmp/hermes_prompt.txt` в WSL, запускает `hermes chat` через `wsl bash -lc`.

**Импорты:**
```python
import subprocess, sys, os, json, urllib.request
import tempfile, datetime
```

**Константы (ключевые):**
- `TEST_MODE` — `False` в продакшене, `True` для отладки без Paperclip API

**Env vars от Paperclip (только при Assignment run):**
- `PAPERCLIP_TASK_ID` — UUID задачи для GET `/api/issues/{id}`
- `PAPERCLIP_AGENT_ID`, `PAPERCLIP_COMPANY_ID`, `PAPERCLIP_API_URL`

**Лог-файл:** `%TEMP%\hermes_launch_debug.txt`

**Детали:** см. launch_hermes.py

---

### 3. config.yaml
**Назначение:** Шаблон конфига Hermes Agent. Кладётся в `~/.hermes/config.yaml` внутри WSL Ubuntu.

**Ключевые поля:** `model`, `provider`, `base_url`, `compression`

**Детали:** см. config.yaml

---

### 4. .env.template
**Назначение:** Шаблон с переменными API-ключей. Переименовать в `.env` и положить в `~/.hermes/.env` внутри WSL.

**Переменные:** `ZAI_API_KEY`, `GLM_API_KEY`

---

### 5. hermes.bat
**Назначение:** Простая Windows-обёртка для ручного запуска `hermes` из CMD/PowerShell. Кладётся в `C:\Users\<USER>\bin\` (папка должна быть в PATH).

**Детали:** см. hermes.bat

---

### 6. install_hermes_wsl.ps1
**Назначение:** Автоматическая установка всей связки: устанавливает `hermes-agent` в WSL, пишет `config.yaml` и `.env`, создаёт `hermes.bat` в Windows PATH, проверяет результат.

**Шаги:** 4 шага (pip install → config → hermes.bat → verify)

**Детали:** см. install_hermes_wsl.ps1