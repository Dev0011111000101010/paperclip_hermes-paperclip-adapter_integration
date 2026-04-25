# launch_hermes.py
"""
Windows -> WSL argument bridge for hermes.

Лог-файлы:
  logs/hermes_launch_debug.txt — накопленный лог всех запусков (append, лимит 1MB)
  logs/последний_запуск.txt   — сырой вывод hermes из Linux, только текущий запуск (overwrite)

Файлы проекта:
  dist/hermes.exe             — скомпилированный исполняемый файл (Paperclip вызывает его)
  temp/сердцебиение_paperclip.txt — raw argv heartbeat-вызовов
  temp/задача_от_paperclip.txt    — raw argv task-вызовов
"""
import subprocess
import sys
import os
import datetime
import threading
import json

# ── Определяем корень проекта (PyInstaller-aware) ─────────────────────────────
if getattr(sys, 'frozen', False):
    _project_dir = os.path.dirname(os.path.dirname(os.path.abspath(sys.executable)))
else:
    _project_dir = os.path.dirname(os.path.abspath(__file__))

_logs_dir = os.path.join(_project_dir, 'logs')
_temp_dir = os.path.join(_project_dir, 'temp')
os.makedirs(_logs_dir, exist_ok=True)
os.makedirs(_temp_dir, exist_ok=True)

_debug_log   = os.path.join(_logs_dir, 'hermes_launch_debug.txt')
_session_log = os.path.join(_logs_dir, 'последний_запуск.txt')

_DEBUG_LOG_LIMIT = 1 * 1024 * 1024  # 1 MB

# ── Функции логирования ───────────────────────────────────────────────────────

def log(msg):
    """Пишет только в накопленный debug-лог с таймстемпом. Если > 1MB — очищает."""
    try:
        if os.path.exists(_debug_log) and os.path.getsize(_debug_log) > _DEBUG_LOG_LIMIT:
            mode = 'w'
        else:
            mode = 'a'
        with open(_debug_log, mode, encoding='utf-8') as f:
            f.write(f'{datetime.datetime.now().isoformat()} {msg}\n')
    except Exception:
        pass

def _session_write_raw(data: bytes):
    """Пишет сырые байты от hermes в лог текущего запуска."""
    try:
        with open(_session_log, 'ab') as f:
            f.write(data)
    except Exception:
        pass

# ── Старт сессии ──────────────────────────────────────────────────────────────
args = sys.argv[1:]
_start_time = datetime.datetime.now().isoformat()

# Очищаем лог текущего запуска
open(_session_log, 'w').close()

log(f'\n=== НОВЫЙ ЗАПУСК {_start_time} ===')
log(f'argv: {sys.argv}')
for k in ['PAPERCLIP_TASK_ID', 'PAPERCLIP_AGENT_ID', 'PAPERCLIP_COMPANY_ID', 'PAPERCLIP_API_URL']:
    log(f'{k}={os.environ.get(k, "<NOT SET>")}')

# ── Version check ─────────────────────────────────────────────────────────────
if not args or args[0] == '--version':
    result = subprocess.run(
        ['wsl', 'bash', '-lc', 'hermes --version'],
        capture_output=True, text=True, timeout=15
    )
    print(result.stdout, end='')
    sys.exit(result.returncode)

# ── Сохраняем raw вызов от Paperclip в temp/ ─────────────────────────────────
_task_id_raw = os.environ.get('PAPERCLIP_TASK_ID', '')
_raw_path = os.path.join(_temp_dir, 'задача_от_paperclip.txt' if _task_id_raw else 'сердцебиение_paperclip.txt')
with open(_raw_path, 'w', encoding='utf-8') as _f:
    _f.write('\n'.join(sys.argv))

# ── Обновляем модель в конфиге WSL ───────────────────────────────────────────
subprocess.run(
    ['wsl', 'bash', '-lc',
     "sed -i 's|^model:.*|model: zai/glm-4.6|' ~/.hermes/config.yaml"]
)

# ── Извлекаем промпт из argv ──────────────────────────────────────────────────
prompt = None
if '-q' in args:
    _q_idx = args.index('-q')
    if _q_idx + 1 < len(args):
        prompt = args[_q_idx + 1]
        log(f'prompt получен из -q ({len(prompt)} символов)')
else:
    log('нет -q аргумента')

if prompt is None:
    log('prompt=None → нет задачи, выходим')
    sys.exit(0)

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 1: Проверяем доступность hermes
# ═════════════════════════════════════════════════════════════════════════════
log('ШАГ 1: hermes --version')
try:
    check = subprocess.run(
        ['wsl', 'bash', '-lc', 'hermes --version'],
        capture_output=True, text=True
    )
    if check.returncode != 0:
        log(f'ШАГ 1 ОШИБКА: returncode={check.returncode} stderr={check.stderr.strip()!r}')
        sys.exit(1)
    log(f'ШАГ 1 OK: {check.stdout.strip()!r}')
except subprocess.TimeoutExpired:
    log('ШАГ 1 ОШИБКА: таймаут')
    sys.exit(1)
except FileNotFoundError:
    log('ШАГ 1 ОШИБКА: wsl.exe не найден')
    sys.exit(1)
except Exception as e:
    log(f'ШАГ 1 ОШИБКА: {type(e).__name__}: {e}')
    sys.exit(1)

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 2: Пишем промпт в /tmp/hermes_prompt.txt в WSL
# ═════════════════════════════════════════════════════════════════════════════
log('ШАГ 2: пишем промпт в WSL /tmp/hermes_prompt.txt')
try:
    subprocess.run(
        ['wsl', 'bash', '-c', 'cat > /tmp/hermes_prompt.txt'],
        input=prompt.encode('utf-8')
    )
    log(f'ШАГ 2 OK: промпт записан ({len(prompt)} символов)')
except Exception as e:
    log(f'ШАГ 2 ОШИБКА: {type(e).__name__}: {e}')
    sys.exit(1)

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 3: Запускаем hermes с -q, весь вывод пишем в лог
# ═════════════════════════════════════════════════════════════════════════════
log('ШАГ 3: формируем runner-скрипт и запускаем hermes в WSL')
# Пробрасываем флаги Paperclip, кроме: -q (промпт из файла), -m и --provider
# (модель берётся из WSL ~/.hermes/config.yaml, обновлённого sed выше)
_SKIP_FLAGS = {'-q', '-m', '--provider'}
_forward_args = []
_skip_val = False
for _a in args:
    if _skip_val:
        _skip_val = False
        continue
    if _a in _SKIP_FLAGS:
        _skip_val = True
        continue
    _forward_args.append(_a)

_hermes_cmd = ['hermes'] + _forward_args
_runner_lines = [
    'import subprocess, sys',
    f'cmd = {json.dumps(_hermes_cmd)}',
    'p = open("/tmp/hermes_prompt.txt").read()',
    'try:',
    '    idx = cmd.index("chat") + 1',
    'except ValueError:',
    '    idx = 1',
    'cmd = cmd[:idx] + ["-q", p] + cmd[idx:]',
    'r = subprocess.run(cmd)',
    'sys.exit(r.returncode)',
]
_runner_script = '\n'.join(_runner_lines) + '\n'

try:
    subprocess.run(
        ['wsl', 'bash', '-c', 'cat > /tmp/run_hermes.py'],
        input=_runner_script.encode('utf-8'),
        check=True
    )
    log('ШАГ 3a OK: /tmp/run_hermes.py записан')
except Exception as e:
    log(f'ШАГ 3 ОШИБКА (write runner): {type(e).__name__}: {e}')
    sys.exit(1)

try:
    proc = subprocess.Popen(
        ['wsl', 'bash', '-lc', 'python3 /tmp/run_hermes.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log(f'ШАГ 3b OK: процесс запущен (pid={proc.pid}), cmd={_hermes_cmd!r}')
except FileNotFoundError:
    log('ШАГ 3b ОШИБКА: wsl.exe не найден')
    sys.exit(1)
except Exception as e:
    log(f'ШАГ 3b ОШИБКА: {type(e).__name__}: {e}')
    sys.exit(1)

def _stdout_reader(proc):
    """Читает stdout hermes: пишет сырые байты в последний_запуск.txt."""
    try:
        for raw_line in iter(proc.stdout.readline, b''):
            _session_write_raw(raw_line)
            sys.stdout.buffer.write(raw_line)
            sys.stdout.buffer.flush()
    except Exception as e:
        log(f'_stdout_reader ОШИБКА: {type(e).__name__}: {e}')

reader_thread = threading.Thread(target=_stdout_reader, args=(proc,), daemon=True)
reader_thread.start()

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 4: Ждём завершения hermes
# ═════════════════════════════════════════════════════════════════════════════
log('ШАГ 4: ждём завершения hermes')
try:
    reader_thread.join()
    returncode = proc.wait()
    log(f'ШАГ 4 OK: hermes завершился с кодом {returncode}')
    sys.exit(returncode)
except Exception as e:
    log(f'ШАГ 4 ОШИБКА: {type(e).__name__}: {e}')
    sys.exit(1)