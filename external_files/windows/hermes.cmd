@echo off
rem ============================================================
rem  Положить в: C:\Users\%USERNAME%\bin\hermes.cmd
rem  (папка bin должна быть в Windows PATH)
rem
rem  Этот файл нужен для вызова hermes из командной строки Windows.
rem  Paperclip вызывает dist\hermes.exe напрямую, не через этот файл.
rem ============================================================
if "%~1"=="" (
  wsl hermes
  goto :eof
)
python "C:\Users\%USERNAME%\PycharmProjects\paperclip_hermes-paperclip-adapter_integration\launch_hermes.py" %*
