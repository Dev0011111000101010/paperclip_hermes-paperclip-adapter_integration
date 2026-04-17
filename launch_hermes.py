"""
Windows -> WSL argument bridge for hermes.

Root cause of quoting breakage:
  resolveSpawnTarget builds: cmd.exe /d /s /c "hermes.cmd" chat -q "You are ""Hermes Dev"", ..." ...
  cmd.exe /s/c strips outer quotes — Python sys.argv receives the prompt split
  into individual words. Previous fix (stdin) put hermes in interactive mode
  where it treated each line of the prompt as a separate turn.

Final fix:
  1. Fetch task from Paperclip API via PAPERCLIP_TASK_ID env var.
  2. Write the prompt to /tmp/hermes_prompt.txt in WSL via stdin pipe.
  3. Call hermes with: -q "$(cat /tmp/hermes_prompt.txt)"
     bash evaluates $(cat ...) INSIDE the double-quoted arg — the result is
     a single -q value regardless of quotes/newlines in the file content.
     No cmd.exe quoting anywhere on the prompt path.

File locations:
  This file (canonical):
    C:\\Users\\vibecoder_blogger\\PycharmProjects\\
      paperclip_hermes-paperclip-adapter_integration\\launch_hermes.py

  Windows entry point (Paperclip adapter points here):
    C:\\Users\\vibecoder_blogger\\ZIA\\hermes.cmd   ← stub, calls THIS file
    C:\\Users\\vibecoder_blogger\\PycharmProjects\\...\\hermes.cmd  ← also calls THIS file

  Paperclip env vars set by execute.js (only on Assignment runs):
    PAPERCLIP_TASK_ID    — issue UUID to fetch from API
    PAPERCLIP_AGENT_ID   — agent UUID
    PAPERCLIP_COMPANY_ID — company/workspace UUID
    PAPERCLIP_API_URL    — base URL, default http://127.0.0.1:3100
"""
import subprocess
import sys
import os
import json
import urllib.request

args = sys.argv[1:]

# Version check — proxy to real hermes in WSL so Paperclip can parse the version
if not args or args[0] == '--version':
    result = subprocess.run(
        ['wsl', 'bash', '-lc', 'hermes --version'],
        capture_output=True, text=True, timeout=15
    )
    print(result.stdout, end='')
    sys.exit(result.returncode)

# Определяем корень проекта (работает и как .py и как .exe через PyInstaller)
import datetime
if getattr(sys, 'frozen', False):
    # Запущен как .exe: dist/hermes.exe → поднимаемся на уровень выше
    _project_dir = os.path.dirname(os.path.dirname(os.path.abspath(sys.executable)))
else:
    _project_dir = os.path.dirname(os.path.abspath(__file__))

# Папки внутри проекта
_logs_dir = os.path.join(_project_dir, 'logs')
_temp_dir = os.path.join(_project_dir, 'temp')
os.makedirs(_logs_dir, exist_ok=True)
os.makedirs(_temp_dir, exist_ok=True)

# Debug лог — теперь в logs/ внутри проекта
_log = os.path.join(_logs_dir, 'hermes_launch_debug.txt')
with open(_log, 'a', encoding='utf-8') as _f:
    _f.write(f'\n=== {datetime.datetime.now().isoformat()} ===\n')
    _f.write(f'argv: {sys.argv}\n')
    for k in ['PAPERCLIP_TASK_ID','PAPERCLIP_AGENT_ID','PAPERCLIP_COMPANY_ID','PAPERCLIP_API_URL']:
        _f.write(f'{k}={os.environ.get(k, "<NOT SET>")}\n')

# Сохраняем raw вызов от Paperclip в temp/
_task_id_raw = os.environ.get('PAPERCLIP_TASK_ID', '')
if _task_id_raw:
    _raw_path = os.path.join(_temp_dir, 'задача_от_paperclip.txt')
else:
    _raw_path = os.path.join(_temp_dir, 'сердцебиение_paperclip.txt')
with open(_raw_path, 'w', encoding='utf-8') as _f:
    _f.write('\n'.join(sys.argv))

TEST_MODE = False

# Update model config to free tier
subprocess.run(
    ['wsl', 'bash', '-lc',
     "sed -i 's|^model:.*|model: zai/glm-4.5-flash|' ~/.hermes/config.yaml"],
    timeout=15
)

# ── Paperclip env vars (set by execute.js before spawning us) ─────────────────
api_url    = os.environ.get('PAPERCLIP_API_URL', 'http://127.0.0.1:3100').rstrip('/')
task_id    = os.environ.get('PAPERCLIP_TASK_ID', '')
agent_id   = os.environ.get('PAPERCLIP_AGENT_ID', '')
company_id = os.environ.get('PAPERCLIP_COMPANY_ID', '')

api_base = api_url if api_url.endswith('/api') else api_url + '/api'

# ── Fetch task from Paperclip API ─────────────────────────────────────────────
prompt = None
if TEST_MODE:
    prompt = 'привет'
    with open(_log, 'a', encoding='utf-8') as _f:
        _f.write(f'TEST_MODE=True — prompt hardcoded to: {prompt!r}\n')
elif task_id:
    try:
        url = f'{api_base}/issues/{task_id}'
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            issue = json.loads(resp.read().decode('utf-8'))
        title = issue.get('title', '')
        body  = (issue.get('body') or '').strip()
        prompt = f'''You are "Hermes Dev", an AI agent employee in a Paperclip-managed company.

IMPORTANT: Use `terminal` tool with `curl` for ALL Paperclip API calls (web_extract and browser cannot access localhost).

Your Paperclip identity:
  Agent ID: {agent_id}
  Company ID: {company_id}
  API Base: {api_base}

## Assigned Task

Issue ID: {task_id}
Title: {title}

{body}

## Workflow

1. Work on the task using your tools
2. When done, mark the issue as completed:
   curl -s -X PATCH "{api_base}/issues/{task_id}" -H "Content-Type: application/json" -d \'{{"status":"done"}}\'
3. Post a completion comment:
   curl -s -X POST "{api_base}/issues/{task_id}/comments" -H "Content-Type: application/json" -d \'{{"body":"DONE: <your summary here>"}}\'
'''
    except Exception as exc:
        sys.stderr.write(f'[launch_hermes] API fetch failed: {exc}\n')
        with open(_log, 'a', encoding='utf-8') as _f:
            _f.write(f'API fetch FAILED: {exc}\n')
else:
    if not TEST_MODE:
        with open(_log, 'a', encoding='utf-8') as _f:
            _f.write('PAPERCLIP_TASK_ID is empty — prompt=None, hermes will run interactive\n')

# ── Extract simple single-word flags from argv (best-effort) ──────────────────
model    = 'zai/glm-4.5-flash'
provider = 'zai'
source   = 'tool'
resume   = None
i = 0
while i < len(args):
    if   args[i] == '-m'         and i+1 < len(args): model    = args[i+1]; i += 2
    elif args[i] == '--provider' and i+1 < len(args): provider = args[i+1]; i += 2
    elif args[i] == '--source'   and i+1 < len(args): source   = args[i+1]; i += 2
    elif args[i] == '--resume'   and i+1 < len(args): resume   = args[i+1]; i += 2
    else: i += 1

# ── Log final prompt decision ─────────────────────────────────────────────────
with open(_log, 'a', encoding='utf-8') as _f:
    if prompt is not None:
        _f.write(f'prompt (first 80 chars): {prompt[:80]!r}\n')
    else:
        _f.write('prompt=None → interactive mode\n')

# ── Write prompt to /tmp/hermes_prompt.txt in WSL ─────────────────────────────
if prompt is not None:
    subprocess.run(
        ['wsl', 'bash', '-c', 'cat > /tmp/hermes_prompt.txt'],
        input=prompt.encode('utf-8'),
        timeout=10
    )
    # Use "$(cat file)" — bash passes entire file content as one -q argument.
    # Prompt content is in the FILE, not in the command string — no quoting issues.
    resume_part = f' --resume {resume}' if resume else ''
    bash_cmd = (
        f'echo "=== PROMPT SENT TO HERMES ===" && cat /tmp/hermes_prompt.txt && echo "=== END PROMPT ===" && '
        f'/usr/local/bin/hermes chat'
        f' -q "$(cat /tmp/hermes_prompt.txt)"'
        f' -Q -m {model} --provider {provider} --source {source} --yolo'
        f'{resume_part}'
    )
    result = subprocess.run(['wsl', 'bash', '-lc', bash_cmd])
else:
    # No task — start hermes interactively (gets EOF, exits 0)
    bash_cmd = (
        f'/usr/local/bin/hermes chat'
        f' -Q -m {model} --provider {provider} --source {source} --yolo'
    )
    result = subprocess.run(['wsl', 'bash', '-lc', bash_cmd])

sys.exit(result.returncode)
