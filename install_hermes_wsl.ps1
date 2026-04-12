# ============================================================
#  Расположение этого файла:
#    Любая папка на Windows — запускать от имени пользователя.
#    Например: C:\Users\<ВАШ_ПОЛЬЗОВАТЕЛЬ>\Downloads\install_hermes_wsl.ps1
#
#  Как запустить:
#    Правой кнопкой -> "Выполнить с помощью PowerShell"
#    или в PowerShell: .\install_hermes_wsl.ps1
#
#  Что делает скрипт:
#    1. Устанавливает hermes-agent в WSL Ubuntu через pip
#    2. Записывает config.yaml (модель zai/glm-4.6)
#    3. Записывает .env с вашим API ключом
#    4. Создаёт hermes.bat в C:\Users\<USER>\bin\ для Windows PATH
#    5. Проверяет установку
# ============================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Hermes Agent x ZAI x Paperclip Setup " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Запросить API ключ ──────────────────────────────────────
Write-Host "Получить API ключ: https://z.ai/manage-apikey/apikey-list" -ForegroundColor Yellow
Write-Host ""
$ZAI_API_KEY = Read-Host "Введите ваш ZAI_API_KEY"

if ([string]::IsNullOrWhiteSpace($ZAI_API_KEY)) {
    Write-Host "[ERROR] API ключ не может быть пустым." -ForegroundColor Red
    exit 1
}

# ── STEP 1: Установка hermes-agent в WSL ───────────────────
Write-Host ""
Write-Host "[1/4] Установка hermes-agent в WSL Ubuntu..." -ForegroundColor Yellow

wsl -d Ubuntu -- bash -c "pip install --upgrade hermes-agent 2>&1 | tail -3"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Установка hermes-agent завершилась с ошибкой." -ForegroundColor Red
    Write-Host "Убедитесь, что WSL Ubuntu установлен: wsl --install -d Ubuntu" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] hermes-agent установлен." -ForegroundColor Green

# ── STEP 2: Запись config.yaml и .env в WSL ────────────────
Write-Host ""
Write-Host "[2/4] Запись конфигурации в WSL..." -ForegroundColor Yellow

$configYaml = @"
# Hermes Agent - ZAI (z.ai / GLM-4.6) config
# Расположение: ~/.hermes/config.yaml (внутри WSL Ubuntu)
model: zai/glm-4.6
provider: zai
base_url: https://api.z.ai/api/paas/v4

compression:
  enabled: true
  threshold: 0.50
  summary_model: ""
  summary_provider: auto
"@

$envContent = @"
ZAI_API_KEY=$ZAI_API_KEY
GLM_API_KEY=$ZAI_API_KEY
"@

$tempConfig = "$env:TEMP\hermes_config.yaml"
$tempEnv    = "$env:TEMP\hermes_env"

$configYaml | Out-File -FilePath $tempConfig -Encoding utf8 -NoNewline
$envContent | Out-File -FilePath $tempEnv    -Encoding utf8 -NoNewline

$wslTempConfig = (wsl -d Ubuntu -- wslpath -u ($tempConfig -replace '\\','/')).Trim()
$wslTempEnv    = (wsl -d Ubuntu -- wslpath -u ($tempEnv    -replace '\\','/')).Trim()

wsl -d Ubuntu -- bash -c "mkdir -p ~/.hermes && cp '$wslTempConfig' ~/.hermes/config.yaml && cp '$wslTempEnv' ~/.hermes/.env"
Remove-Item $tempConfig, $tempEnv -ErrorAction SilentlyContinue

Write-Host "[OK] config.yaml и .env записаны в WSL (~/.hermes/)." -ForegroundColor Green

# ── STEP 3: Создание hermes.bat в Windows PATH ─────────────
Write-Host ""
Write-Host "[3/4] Создание hermes.bat для Windows PATH..." -ForegroundColor Yellow

$binDir = "$env:USERPROFILE\bin"
if (!(Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir | Out-Null
    Write-Host "[OK] Создана папка: $binDir" -ForegroundColor Green
}

$batContent = @"
@echo off
rem Перенаправляет hermes из Windows в WSL Ubuntu
wsl bash -lc "hermes %*"
"@
$batContent | Out-File -FilePath "$binDir\hermes.bat" -Encoding ascii -NoNewline

# Добавить в PATH если отсутствует
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$binDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$binDir", "User")
    Write-Host "[OK] $binDir добавлен в Windows PATH." -ForegroundColor Green
    Write-Host "     ВАЖНО: перезапустите терминал/Paperclip чтобы PATH обновился." -ForegroundColor Yellow
} else {
    Write-Host "[OK] $binDir уже в Windows PATH." -ForegroundColor Green
}

# ── STEP 4: Проверка ───────────────────────────────────────
Write-Host ""
Write-Host "[4/4] Проверка установки..." -ForegroundColor Yellow

$version = wsl -d Ubuntu -- bash -lc "hermes --version 2>&1 | head -1"
if ($version -match "Hermes") {
    Write-Host "[OK] $version" -ForegroundColor Green
} else {
    Write-Host "[WARN] hermes --version не вернул версию. Возможно нужно перезапустить WSL:" -ForegroundColor Yellow
    Write-Host "       wsl --shutdown  (затем открыть снова)" -ForegroundColor Yellow
}

# ── Итог ───────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ГОТОВО!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Следующие шаги:" -ForegroundColor White
Write-Host "  1. Запустите Paperclip:" -ForegroundColor White
Write-Host "     npx paperclipai@latest start" -ForegroundColor Yellow
Write-Host "  2. Откройте браузер: http://127.0.0.1:3100" -ForegroundColor White
Write-Host "  3. Создайте агента с адаптером 'Hermes Agent (Local)'" -ForegroundColor White
Write-Host "     Агенты: http://127.0.0.1:3100/MYA/agents/" -ForegroundColor Yellow
Write-Host "  4. В настройках агента укажите модель: zai/glm-4.6" -ForegroundColor White
Write-Host ""
