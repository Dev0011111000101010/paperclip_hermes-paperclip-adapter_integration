# Hermes Agent + Paperclip + ZAI — Интеграция и настройка

Эта инструкция описывает полную рабочую связку:
**Paperclip** (оркестратор AI-агентов) → **hermes.cmd** (Windows-мост) → **WSL2/Ubuntu** → **Hermes Agent** → **ZAI API** (модель `zai/glm-4.6`, бесплатно).

## Официальные ссылки

| Что | Ссылка |
|-----|--------|
| Paperclip — репозиторий | https://github.com/paperclipai/paperclip |
| Hermes Paperclip Adapter | https://github.com/NousResearch/hermes-paperclip-adapter |
| ZAI — получить API ключ | https://z.ai/manage-apikey/apikey-list |
| Paperclip — управление агентами | http://127.0.0.1:3100/MYA/agents/ |

---

## Требования

- Windows 10/11 с WSL2 (Ubuntu)
- Node.js 20+ (для Paperclip)
- Python 3.10+ (Windows, для launch_hermes.py)
- Python 3.10+ (WSL Ubuntu, для hermes-agent)
- Аккаунт на [z.ai](https://z.ai) для бесплатного API ключа

---

## Архитектура: полная цепочка вызовов

```
Paperclip (Node.js, Windows, порт 3100)
    │
    │  resolveSpawnTarget → вызывает hermes.cmd напрямую:
    │  cmd.exe /d /s /c "C:\Users\...\PycharmProjects\...\hermes.cmd" chat -q "..."
    ▼
C:\Users\vibecoder_blogger\PycharmProjects\
  paperclip_hermes-paperclip-adapter_integration\hermes.cmd   ← ГЛАВНЫЙ ENTRY POINT
    │
    │  python "%~dp0launch_hermes.py" %*
    ▼
C:\Users\vibecoder_blogger\PycharmProjects\
  paperclip_hermes-paperclip-adapter_integration\launch_hermes.py   ← ВСЯ ЛОГИКА ЗДЕСЬ
    │
    │  1. Читает env vars: PAPERCLIP_TASK_ID, PAPERCLIP_API_URL, ...
    │  2. Обновляет модель в ~/.hermes/config.yaml через sed
    │  3. Пишет промпт в /tmp/hermes_prompt.txt (через WSL stdin-pipe)
    │  4. Пишет runner-скрипт в /tmp/run_hermes.py (через WSL stdin-pipe)
    │  5. Запускает: wsl bash -lc 'python3 /tmp/run_hermes.py'
    ▼
WSL2 Ubuntu — hermes chat
    │
    │  ~/.hermes/config.yaml (модель zai/glm-4.6, провайдер zai)
    │  ~/.hermes/.env (ZAI_API_KEY)
    ▼
ZAI API (https://api.z.ai/api/paas/v4) — модель zai/glm-4.6
```

---

## Внешние файлы (вне репозитория)

Часть файлов живёт **вне этого репозитория** — в домашней папке Windows и в WSL.
Без них интеграция не заработает.

📁 Смотри: **[external_files/README.md](external_files/README.md)**

Там описаны:
- `~/.wslconfig` — WSL2 mirrored networking (без него ZAI не видит Paperclip API)
- `~/.hermes/config.yaml` — конфиг hermes с моделью ZAI
- заглушка `hermes.cmd` для Windows PATH
- **почему Hermes нельзя установить через AI CLI** (инсталлятор интерактивный — агент зависнет)

---

## Файлы в этом репозитории

### Исполняемые файлы (вся логика живёт здесь)

| Файл | Что делает |
|------|-----------|
| `launch_hermes.py` | **Главный Python-мост** Windows→WSL. Читает задачу из Paperclip API, пишет промпт в WSL-файл, запускает hermes. |
| `hermes.cmd` | **Windows entry point** для этой папки. Вызывает `launch_hermes.py` из той же директории. |

### Вспомогательные файлы

| Файл | Куда класть | Что делает |
|------|-------------|-----------|
| `hermes.bat` | `C:\Users\<USER>\bin\hermes.bat` | Простая обёртка для ручного CLI-вызова hermes из Windows |
| `config.yaml` | `~/.hermes/config.yaml` (в WSL) | Конфиг hermes: модель zai/glm-4.6, провайдер zai |
| `.env.template` | `~/.hermes/.env` (в WSL, переименовать) | Шаблон для API ключей ZAI |
| `install_hermes_wsl.ps1` | Любая папка Windows | Автоматическая установка всей связки |

---

## Содержимое ключевых файлов

### `launch_hermes.py` — главная логика

**Путь:** `C:\Users\vibecoder_blogger\PycharmProjects\paperclip_hermes-paperclip-adapter_integration\launch_hermes.py`

**Почему промпт передаётся через файл, а не как аргумент:**

Промпт от Paperclip содержит `"` (двойные кавычки). Если передать их напрямую
через аргумент `wsl python3 -c "код с кавычками"`, WSL внутри пробрасывает
команду через bash — и bash падает с `unexpected EOF while looking for matching '"'`.

**Итоговое решение (без проблем с кавычками):**

```
1. Промпт → /tmp/hermes_prompt.txt   через wsl bash -c 'cat > ...'  (stdin-pipe, нет кавычек)
2. Runner-скрипт → /tmp/run_hermes.py  через wsl bash -c 'cat > ...'  (stdin-pipe, нет кавычек)
3. Запуск: wsl bash -lc 'python3 /tmp/run_hermes.py'
   Runner читает промпт из файла и вызывает hermes через subprocess list (без shell=True)
```

Runner-скрипт формируется динамически и включает все флаги Paperclip кроме
`-m` и `--provider` (модель берётся из WSL конфига `~/.hermes/config.yaml`).

### `ZIA\hermes.cmd` — заглушка

**Путь:** `C:\Users\vibecoder_blogger\ZIA\hermes.cmd`

```batch
@echo off
rem ЗАГЛУШКА — вся логика в проектной папке
if "%~1"=="" (
  wsl hermes
  goto :eof
)
python "C:\Users\vibecoder_blogger\PycharmProjects\paperclip_hermes-paperclip-adapter_integration\launch_hermes.py" %*
```

### `config.yaml` — конфиг hermes в WSL

**Путь:** `~/.hermes/config.yaml` (внутри WSL Ubuntu)

```yaml
model: zai/glm-4.6
provider: zai
base_url: https://api.z.ai/api/paas/v4
compression:
  enabled: true
  threshold: 0.50
```

---

## Быстрая установка

### Шаг 1 — Получить API ключ ZAI

1. Зайди на https://z.ai/manage-apikey/apikey-list
2. Зарегистрируйся / войди
3. Создай новый ключ и скопируй его

### Шаг 2 — Запустить установочный скрипт

```powershell
# В PowerShell (правая кнопка → "Запустить от имени пользователя")
.\install_hermes_wsl.ps1
```

### Шаг 3 — Настроить Paperclip-агента

1. Открой http://127.0.0.1:3100/MYA/agents/
2. Нажми "New Agent" (или отредактируй существующего)
3. В поле **Hermes Command** укажи полный путь:
   ```
   C:\Users\vibecoder_blogger\ZIA\hermes.cmd
   ```
   (это заглушка, которая делегирует в проектную папку)
4. В **Environment Variables** добавь:
   - `ZAI_API_KEY` = твой ключ с z.ai
   - `GLM_API_KEY` = тот же ключ
5. Нажми **Test Environment** — должно показать `Passed`

---

## Ручная установка (пошагово)

### 1. Установи WSL Ubuntu

```powershell
wsl --install -d Ubuntu
```

### 2. Установи hermes-agent в WSL

```bash
pip install --upgrade hermes-agent
```

### 3. Создай конфигурацию hermes в WSL

```bash
mkdir -p ~/.hermes

# Скопируй config.yaml из этого репо:
cp /mnt/c/Users/vibecoder_blogger/PycharmProjects/paperclip_hermes-paperclip-adapter_integration/config.yaml ~/.hermes/config.yaml

# Создай .env с API ключом:
echo "ZAI_API_KEY=ВАШ_КЛЮЧ" > ~/.hermes/.env
echo "GLM_API_KEY=ВАШ_КЛЮЧ" >> ~/.hermes/.env
```

### 4. Проверь что hermes работает в WSL

```bash
wsl bash -lc "hermes --version"
# Ожидаемо: Hermes Agent v0.8.x
```

### 5. Запусти Paperclip

```powershell
npx paperclipai@latest start
```

Открой: http://127.0.0.1:3100

---

## Типы запусков Paperclip

| Тип | Когда | PAPERCLIP_TASK_ID | Поведение |
|-----|-------|-------------------|-----------|
| **Assignment run** | Задача назначена агенту | ✅ Установлен | launch_hermes.py получает задачу из API |
| **Heartbeat run** | "Run Heartbeat" кнопка | ❌ Не установлен | hermes запускается без промпта (интерактивный режим) |

**Важно:** чтобы запустить Assignment run повторно, нужно:
1. Убрать назначение (поставить "No assignee")
2. Заново назначить агента на задачу

---

## Отладка

### Лог-файлы

**Наш мост (главные логи для отладки hermes):**
```
<папка_проекта>\logs\hermes_launch_debug.txt   — все запуски, append, до 1 МБ
<папка_проекта>\logs\последний_запуск.txt      — сырой stdout hermes (только последний)
```
Содержат: timestamp, argv от Paperclip, PAPERCLIP_* env vars, этапы ШАГ 1–4, exit code.

**Paperclip (HTTP-лог сервера):**
```
C:\Users\<ИМЯ_ПОЛЬЗОВАТЕЛЯ>\.paperclip\instances\default\logs\server.log
```
Содержит: HTTP-запросы к API (200/304/500 и т.д.). Записей о запусках hermes здесь нет.

**База данных Paperclip:**
```
C:\Users\<ИМЯ_ПОЛЬЗОВАТЕЛЯ>\.paperclip\instances\default\db\   — embedded PostgreSQL
```

### Частые проблемы

**`hermes: command not found` в WSL**
→ Убедись что hermes установлен: `wsl bash -lc "which hermes"`
→ Если нет: `wsl bash -lc "pip install --upgrade hermes-agent"`

**`API fetch failed` в логе**
→ Убедись что Paperclip запущен: `curl http://127.0.0.1:3100/api/health`
→ Установи `TEST_MODE = True` в `launch_hermes.py` для отладки без API

**`bash: -c: line 1: unexpected EOF while looking for matching '"'`**
→ Классическая проблема WSL-квотирования: промпт или код содержат `"` и ломают bash.
→ Убедись что используется актуальная версия `dist\hermes.exe` (собранная из последней `launch_hermes.py`).
→ Пересобрать: `pyinstaller --clean hermes.spec`

**Задача не запускается повторно**
→ Убери назначение агента ("No assignee"), подожди 2-3 секунды, назначь снова.

---

## Проверка работы

```powershell
# 1. Hermes установлен в WSL
wsl bash -lc "hermes --version"

# 2. Config верный
wsl bash -lc "head -3 ~/.hermes/config.yaml"
# Ожидаемо: model: zai/glm-4.6

# 3. Заглушка вызывает правильный файл
type C:\Users\vibecoder_blogger\ZIA\hermes.cmd

# 4. Paperclip запущен
curl http://127.0.0.1:3100/api/health
```

---

## Полезные ссылки

- YouTube-плейлист по настройке: https://www.youtube.com/playlist?list=PL6D9b9lf9gb2_0Wpg5HcYenthYSK9KznR
- ZAI API ключи: https://z.ai/manage-apikey/apikey-list
- Paperclip агенты: http://127.0.0.1:3100/MYA/agents/
