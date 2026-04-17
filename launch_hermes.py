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
     "sed -i 's|^model:.*|model: zai/glm-4.5-flash|' ~/.hermes/config.yaml"]
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
# ШАГ 2: Запускаем hermes, ждём баннер загрузки
# ═════════════════════════════════════════════════════════════════════════════
log('ШАГ 2: запускаем hermes')
try:
    proc = subprocess.Popen(
        ['wsl', 'bash', '-lc', 'hermes'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log(f'ШАГ 2 OK: процесс запущен (pid={proc.pid})')
except FileNotFoundError:
    log('ШАГ 2 ОШИБКА: wsl.exe не найден')
    sys.exit(1)
except Exception as e:
    log(f'ШАГ 2 ОШИБКА: {type(e).__name__}: {e}')
    sys.exit(1)

READY_INDICATORS = [
    b'Welcome',
    b'Hermes Agent',
    b'\xe2\x9d\xaf',   # ❯
]

output_lines = []
ready_event  = threading.Event()

def _stdout_reader(proc, output_lines, ready_event):
    """Читает stdout hermes: пишет сырые байты в последний_запуск.txt."""
    try:
        for raw_line in iter(proc.stdout.readline, b''):
            output_lines.append(raw_line)
            _session_write_raw(raw_line)
            sys.stdout.buffer.write(raw_line)
            sys.stdout.buffer.flush()
            if not ready_event.is_set():
                if any(ind in raw_line for ind in READY_INDICATORS):
                    log(f'ШАГ 2: готов — {raw_line.decode("utf-8","replace").strip()!r}')
                    ready_event.set()
    except Exception as e:
        log(f'_stdout_reader ОШИБКА: {type(e).__name__}: {e}')
    finally:
        ready_event.set()

reader_thread = threading.Thread(
    target=_stdout_reader,
    args=(proc, output_lines, ready_event),
    daemon=True
)
reader_thread.start()

ready_event.wait()
log('ШАГ 2 OK: hermes готов')

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 3: Проверяем что hermes жив, отправляем промпт
# ═════════════════════════════════════════════════════════════════════════════
log('ШАГ 3: отправляем промпт')

if proc.poll() is not None:
    log(f'ШАГ 3 ОШИБКА: hermes завершился до отправки промпта (returncode={proc.poll()})')
    sys.exit(1)

try:
    proc.stdin.write(prompt.encode('utf-8') + b'\n')
    proc.stdin.flush()
    proc.stdin.close()
    log(f'ШАГ 3 OK: промпт отправлен ({len(prompt)} символов), stdin закрыт')
except BrokenPipeError:
    log('ШАГ 3 ОШИБКА: BrokenPipe — hermes умер при инициализации')
    sys.exit(1)
except Exception as e:
    log(f'ШАГ 3 ОШИБКА: {type(e).__name__}: {e}')
    sys.exit(1)

# ═════════════════════════════════════════════════════════════════════════════
# ШАГ 4: Ждём завершения hermes
# ═════════════════════════════════════════════════════════════════════════════
log('ШАГ 4: ждём завершения hermes (макс. 300 секунд)')
try:
    reader_thread.join()
    returncode = proc.wait()
    log(f'ШАГ 4 OK: hermes завершился с кодом {returncode}')
    sys.exit(returncode)
except Exception as e:
    log(f'ШАГ 4 ОШИБКА: {type(e).__name__}: {e}')
    sys.exit(1)