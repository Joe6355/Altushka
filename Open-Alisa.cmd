@echo off
setlocal
set "alisaProject=%~dp0unity\Alisa2D"
set "alisaEditor=C:\Unity\6000.6.8f1\Editor\Unity.exe"
if not exist "%alisaEditor%" set "alisaEditor=%ProgramFiles%\Unity\Hub\Editor\6000.6.8f1\Editor\Unity.exe"
if not exist "%alisaEditor%" (
  echo Unity 6000.6.8f1 was not found. Open unity\Alisa2D through Unity Hub.
  pause
  exit /b 1
)
start "" "%alisaEditor%" -projectPath "%alisaProject%" -executeMethod AlisaGame.Editor.AlisaProjectBuilder.OpenGame
