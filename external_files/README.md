# Внешние файлы — инструкция по установке

Эта папка содержит файлы, которые **живут вне репозитория**, но необходимы
для работы интеграции Paperclip → Hermes Agent → ZAI.

---

## Структура

```
external_files/
  windows/
    .wslconfig        → C:\Users\%USERNAME%\.wslconfig
    hermes.cmd        → C:\Users\%USERNAME%\bin\hermes.cmd
  wsl/
    hermes_config.yaml → ~/.hermes/config.yaml  (внутри WSL)
```

---

## Шаг 1 — Установить Hermes Agent вручную (WSL)

> ⚠️ **Hermes устанавливается ТОЛЬКО вручную — не через AI CLI и не через скрипты.**
>
> Причина: инсталлятор hermes задаёт интерактивные вопросы в терминале
> (выбор провайдера, ввод API ключа и т.д.). Если запустить установку через
> AI-агента (Claude Code, Codex и т.п.) — агент просто зависнет, потому что
> ему некуда вводить ответы. Поэтому **открывай WSL-терминал руками и
> устанавливай сам**.

Открыть терминал WSL (не через AI!) и установить hermes согласно официальной
документации NousResearch hermes-agent. После установки проверить:

```bash
hermes --version
```

Должно вывести что-то вроде: `Hermes Agent v0.10.0`

---

## Шаг 2 — Настроить ZAI в конфиге Hermes (WSL)

Скопировать файл `wsl/hermes_config.yaml` в WSL:

```bash
cp /mnt/c/путь/к/проекту/external_files/wsl/hermes_config.yaml ~/.hermes/config.yaml
```

Или создать `~/.hermes/config.yaml` вручную с таким содержимым:

```yaml
model: zai/glm-4.6
provider: zai
base_url: https://api.z.ai/api/paas/v4
```

После этого авторизоваться в ZAI:

```bash
hermes auth zai
```

Проверить что ZAI отвечает:

```bash
hermes chat -q "скажи привет"
```

---

## Шаг 3 — Включить mirrored networking для WSL2 (Windows)

Скопировать файл `windows/.wslconfig` в домашнюю папку пользователя Windows:

```
C:\Users\%USERNAME%\.wslconfig
```

Содержимое файла:

```ini
[wsl2]
networkingMode=mirrored
```

**Зачем:** без этого WSL не видит `127.0.0.1:3100` (Paperclip API), так как
у WSL2 по умолчанию отдельный сетевой стек. Mirrored mode проксирует
Windows loopback в WSL.

После создания файла перезапустить WSL:

```cmd
wsl --shutdown
```

---

## Шаг 4 — Добавить hermes.cmd в Windows PATH (опционально)

> Нужен только для вызова `hermes` из командной строки Windows напрямую.
> Paperclip вызывает `dist\hermes.exe` напрямую — этот файл для него не нужен.

1. Создать папку `C:\Users\%USERNAME%\bin\` (если нет)
2. Скопировать `windows/hermes.cmd` туда
3. Открыть файл и заменить путь на актуальный путь к проекту
4. Добавить `C:\Users\%USERNAME%\bin` в системную переменную PATH

---

## Шаг 5 — Собрать hermes.exe

В корне проекта (Windows, Python 3.x + pyinstaller):

```cmd
pip install pyinstaller
pyinstaller --clean hermes.spec
```

Результат: `dist\hermes.exe` — это исполняемый файл, который Paperclip вызывает
как `hermesCommand`.

---

## Итоговая схема

```
Paperclip (Node.js :3100)
    ↓  вызывает hermesCommand = dist\hermes.exe
dist\hermes.exe  (= launch_hermes.py скомпилированный)
    ↓  stdin-pipe → /tmp/hermes_prompt.txt  (промпт без bash-квотирования)
    ↓  stdin-pipe → /tmp/run_hermes.py      (runner-скрипт)
    ↓  запускает: wsl bash -lc 'python3 /tmp/run_hermes.py'
Hermes Agent (WSL, ~/.hermes/config.yaml → model: zai/glm-4.6)
    ↓  отправляет запрос
ZAI API (https://api.z.ai, model: glm-4.6)
    ↓  выполняет задачу, вызывает curl к Paperclip API
    ↓  curl http://127.0.0.1:3100/api/...  ← работает благодаря .wslconfig mirrored
Paperclip API  ✓
```
