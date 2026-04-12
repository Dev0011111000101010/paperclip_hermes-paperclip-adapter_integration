# Hermes Agent + Paperclip + ZAI (GLM-4.6) — Инструкция по настройке

Эта инструкция поможет поднять связку:
**Paperclip** (платформа для управления AI-агентами) + **Hermes Agent** (AI-агент от Nous Research) + **ZAI / GLM-4.6** (бесплатная языковая модель от z.ai).

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
- Node.js 20+
- Python 3.10+ (в WSL Ubuntu — ставится автоматически)
- Аккаунт на [z.ai](https://z.ai) для получения бесплатного API ключа

---

## Архитектура связки

```
Paperclip (Node.js, Windows)
    │
    │  вызывает команду "hermes"
    ▼
hermes.bat  (C:\Users\<USER>\bin\hermes.bat, в Windows PATH)
    │
    │  wsl bash -lc "hermes ..."
    ▼
hermes-agent (Python, установлен в WSL Ubuntu)
    │
    │  читает ~/.hermes/config.yaml и ~/.hermes/.env
    ▼
ZAI API (z.ai) — модель GLM-4.6
```

**Почему через WSL?**
Hermes Agent — Python-пакет. На Windows проще и надёжнее запускать его в WSL Ubuntu, а в Windows создать `.bat`-обёртку, которая перенаправляет вызовы в WSL.

---

## Быстрая установка (автоматически)

### Шаг 1 — Получить API ключ ZAI

1. Зайди на https://z.ai/manage-apikey/apikey-list
2. Зарегистрируйся / войди
3. Создай новый ключ и скопируй его

### Шаг 2 — Запустить установочный скрипт

```powershell
# В PowerShell (правая кнопка → "Запустить от имени пользователя")
.\install_hermes_wsl.ps1
```

Скрипт:
- Установит `hermes-agent` в WSL Ubuntu через `pip`
- Запишет `~/.hermes/config.yaml` с моделью `zai/glm-4.6`
- Запишет `~/.hermes/.env` с твоим API ключом
- Создаст `hermes.bat` в `C:\Users\<USER>\bin\` и добавит папку в PATH

### Шаг 3 — Запустить Paperclip

```powershell
npx paperclipai@latest start
```

Открой браузер: http://127.0.0.1:3100

---

## Ручная установка (пошагово)

Если хочешь понимать каждый шаг.

### 1. Установи WSL Ubuntu

```powershell
wsl --install -d Ubuntu
```

Перезагрузи компьютер, если потребуется.

### 2. Установи hermes-agent в WSL

```bash
# Открой терминал Ubuntu (WSL)
pip install --upgrade hermes-agent
```

### 3. Создай конфигурационные файлы в WSL

**Файл `~/.hermes/config.yaml`** — используй файл `config.yaml` из этого репозитория:

```bash
mkdir -p ~/.hermes
# Скопируй содержимое config.yaml из этого репо в ~/.hermes/config.yaml
```

**Файл `~/.hermes/.env`** — используй `.env.template`, переименуй в `.env` и вставь ключ:

```bash
# ~/.hermes/.env
ZAI_API_KEY=ВАШ_КЛЮЧ_С_z.ai
GLM_API_KEY=ВАШ_КЛЮЧ_С_z.ai
```

### 4. Создай hermes.bat в Windows PATH

Создай папку `C:\Users\<ВАШ_ПОЛЬЗОВАТЕЛЬ>\bin\` и положи туда файл `hermes.bat` из этого репозитория.

Добавь эту папку в переменную среды PATH:
- Win + R → `sysdm.cpl` → Дополнительно → Переменные среды
- В разделе "Переменные пользователя" найди `Path` → Изменить → Создать
- Добавь: `C:\Users\<ВАШ_ПОЛЬЗОВАТЕЛЬ>\bin`

### 5. Проверь что hermes виден из Windows

```powershell
# В обычном PowerShell или CMD
hermes --version
```

Должна появиться версия, например: `Hermes Agent v0.8.0`

### 6. Установи и запусти Paperclip

```powershell
npx paperclipai@latest start
```

При первом запуске пройди онбординг. Откроется http://127.0.0.1:3100

### 7. Создай агента с Hermes-адаптером

1. Перейди в http://127.0.0.1:3100/MYA/agents/
2. Нажми "New Agent"
3. В поле **Adapter** выбери `Hermes Agent (Local)`
4. В поле **Model** укажи: `zai/glm-4.6`
5. В поле **Hermes Command** оставь: `hermes`
6. В секции **Environment Variables** добавь:
   - `ZAI_API_KEY` = твой ключ с z.ai
   - `GLM_API_KEY` = тот же ключ
7. Нажми **Test Environment** — должно показать `Passed`
8. Сохрани агента

---

## Файлы в этом репозитории

| Файл | Куда класть | Что делает |
|------|-------------|------------|
| `hermes.bat` | `C:\Users\<USER>\bin\hermes.bat` | Обёртка Windows → WSL |
| `config.yaml` | `~/.hermes/config.yaml` (в WSL) | Конфиг hermes: модель, провайдер |
| `.env.template` | `~/.hermes/.env` (в WSL, переименовать) | API ключи для ZAI |
| `install_hermes_wsl.ps1` | Любая папка Windows, запустить | Автоматическая установка |

---

## Решение проблем

**`hermes: command not found` в PowerShell**
→ Перезапусти PowerShell/терминал после добавления папки в PATH.

**`Test Environment` в Paperclip показывает ошибку**
→ Убедись, что `hermes --version` работает в PowerShell.
→ Проверь, что `.env` файл существует в WSL: `wsl bash -lc "cat ~/.hermes/.env"`

**`Warning: Failed to load config` при запуске hermes**
→ Проверь синтаксис `~/.hermes/config.yaml` — файл должен быть валидным YAML.
→ Убедись, что нет лишних отступов: `model:` должен быть без отступа.

**Hermes использует не ту модель**
→ Проверь `~/.hermes/config.yaml`: строка `model: zai/glm-4.6` должна быть первой.
→ В настройках агента в Paperclip поле **Model** тоже должно быть `zai/glm-4.6`.

---

## Проверка работы

```powershell
# 1. Hermes доступен в Windows
hermes --version

# 2. Hermes использует правильную модель (в WSL)
wsl bash -lc "hermes --version"
wsl bash -lc "cat ~/.hermes/config.yaml | head -3"

# 3. Paperclip запущен
curl http://127.0.0.1:3100/api/health
```
