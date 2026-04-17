@echo off
rem ============================================================
rem  hermes.cmd — основная точка входа (Windows)
rem
rem  Расположение этого файла (канонического):
rem    C:\Users\vibecoder_blogger\PycharmProjects\
rem      paperclip_hermes-paperclip-adapter_integration\hermes.cmd
rem
rem  Этот файл вызывается Paperclip-адаптером через resolveSpawnTarget.
rem  Он делегирует всю логику в launch_hermes.py из той же папки.
rem
rem  Все остальные hermes.cmd (в ZIA и т.д.) — тонкие заглушки,
rem  которые вызывают launch_hermes.py из ЭТОЙ папки.
rem ============================================================
if "%~1"=="--version" (
  wsl bash -lc "hermes --version"
  goto :eof
)
python "%~dp0launch_hermes.py" %*
