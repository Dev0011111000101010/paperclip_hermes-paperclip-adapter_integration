# Hermes Agent + Paperclip + ZAI — Интеграция и настройка

Эта инструкция описывает полную рабочую связку:
**Paperclip** (оркестратор AI-агентов) → **hermes.cmd** (Windows-мост) → **WSL2/Ubuntu** → **Hermes Agent** → **ZAI API** (модель `zai/glm-4.5-flash`, бесплатно).

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
    │  2. Делает HTTP GET к Paperclip API → получает текст задачи
    │  3. Пишет промпт в /tmp/hermes_prompt.txt (через WSL pipe)
    │  4. Запускает: wsl bash -lc '/usr/local/bin/hermes chat -q "$(cat /tmp/hermes_prompt.txt)" ...'
    ▼
WSL2 Ubuntu — /usr/local/bin/hermes chat
    │
    │  ~/.hermes/config.yaml (модель, провайдер)
    │  ~/.hermes/.env (ZAI_API_KEY)
    ▼
ZAI API (https://api.z.ai/api/paas/v4) — модель zai/glm-4.5-flash
```

---

## Файлы в этом репозитории

### Исполняемые файлы (вся логика живёт здесь)

| Файл | Что делает |
|------|-----------|
| `launch_hermes.py` | **Главный Python-мост** Windows→WSL. Читает задачу из Paperclip API, пишет промпт в WSL-файл, запускает hermes. |
| `hermes.cmd` | **Windows entry point** для этой папки. Вызывает `launch_hermes.py` из той же директории. |

### Архив — старые файлы (перенесены из ZIA)

Папка `archive\` содержит исходные файлы из `C:\Users\vibecoder_blogger\Documents\Claude\Projects\ZIA\` — на случай если что-то нужно восстановить. Эти файлы больше не используются Paperclip.

### Вспомогательные файлы

| Файл | Куда класть | Что делает |
|------|-------------|-----------|
| `hermes.bat` | `C:\Users\<USER>\bin\hermes.bat` | Простая обёртка для ручного CLI-вызова hermes из Windows |
| `config.yaml` | `~/.hermes/config.yaml` (в WSL) | Конфиг hermes: модель zai/glm-4.5-flash, провайдер zai |
| `.env.template` | `~/.hermes/.env` (в WSL, переименовать) | Шаблон для API ключей ZAI |
| `install_hermes_wsl.ps1` | Любая папка Windows | Автоматическая установка всей связки |

---

## Содержимое ключевых файлов

### `launch_hermes.py` — главная логика

**Путь:** `C:\Users\vibecoder_blogger\PycharmProjects\paperclip_hermes-paperclip-adapter_integration\launch_hermes.py`

Ключевые части:

```python
TEST_MODE = False          # True — тестовый режим (промпт = 'привет')
                            # False — рабочий режим (промпт берётся из Paperclip API)

# Paperclip передаёт эти env vars только в Assignment-запусках:
task_id    = os.environ.get('PAPERCLIP_TASK_ID', '')   # UUID задачи
agent_id   = os.environ.get('PAPERCLIP_AGENT_ID', '')
company_id = os.environ.get('PAPERCLIP_COMPANY_ID', '')
api_url    = os.environ.get('PAPERCLIP_API_URL', 'http://127.0.0.1:3100')
```

**Ключевой фикс квотирования** (почему промпт пишется в файл, а не передаётся аргументом):

```
ПРОБЛЕМА: cmd.exe /d /s /c "hermes.cmd" chat -q "You are ""Hermes Dev"", ..."
  → cmd.exe /s/c снимает внешние кавычки
  → Python получает промпт разбитым на отдельные слова в sys.argv

ПРЕДЫДУЩАЯ ПОПЫТКА (stdin): hermes запускался в интерактивном режиме,
  каждая строка промпта воспринималась как отдельный turn.

ФИНАЛЬНОЕ РЕШЕНИЕ:
  1. Записать промпт в файл: wsl bash -c "cat > /tmp/hermes_prompt.txt"
  2. Передать в hermes: -q "$(cat /tmp/hermes_prompt.txt)"
  Bash вычисляет $(cat ...) ВНУТРИ двойных кавычек — результат это ОДИН аргумент,
  независимо от кавычек и переносов строк в содержимом файла.
  Ни один символ промпта не проходит через cmd.exe.
```

Фрагмент кода с фиксом:
```python
# Запись промпта в WSL файл
subprocess.run(
    ['wsl', 'bash', '-c', 'cat > /tmp/hermes_prompt.txt'],
    input=prompt.encode('utf-8'),
    timeout=10
)

# Запуск hermes — $(cat file) = промпт как один аргумент, без проблем с кавычками
bash_cmd = (
    'echo "=== PROMPT SENT TO HERMES ===" && cat /tmp/hermes_prompt.txt && echo "=== END PROMPT ===" && '
    '/usr/local/bin/hermes chat'
    ' -q "$(cat /tmp/hermes_prompt.txt)"'
    ' -Q -m zai/glm-4.5-flash --provider zai --source tool --yolo'
)
result = subprocess.run(['wsl', 'bash', '-lc', bash_cmd])
```

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
model: zai/glm-4.5-flash
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

### Лог-файл (Windows)

```
%TEMP%\hermes_launch_debug.txt
```

Содержит: timestamp, argv, все Paperclip env vars, первые 80 символов промпта.

### Проверка промпта в Paperclip UI

В транскрипте запуска ищи строки:
```
=== PROMPT SENT TO HERMES ===
<текст промпта>
=== END PROMPT ===
```

### Частые проблемы

**`hermes: command not found` в WSL**
→ Убедись что hermes установлен: `wsl bash -lc "which hermes"`
→ Если нет: `wsl bash -lc "pip install --upgrade hermes-agent"`

**`API fetch failed` в логе**
→ Убедись что Paperclip запущен: `curl http://127.0.0.1:3100/api/health`
→ Установи `TEST_MODE = True` в `launch_hermes.py` для отладки без API

**Hermes получает пустой или разбитый промпт**
→ Это классическая проблема cmd.exe-квотирования. Убедись что bash_cmd использует `$(cat /tmp/hermes_prompt.txt)` а не аргумент напрямую.

**Задача не запускается повторно**
→ Убери назначение агента ("No assignee"), подожди 2-3 секунды, назначь снова.

---

## Проверка работы

```powershell
# 1. Hermes установлен в WSL
wsl bash -lc "hermes --version"

# 2. Config верный
wsl bash -lc "head -3 ~/.hermes/config.yaml"
# Ожидаемо: model: zai/glm-4.5-flash

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
