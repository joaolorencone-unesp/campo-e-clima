@echo off
chcp 65001 >nul
title Campo e Clima - Instalador seguro v2.3
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
  py -3 "%~dp0aplicar_v23.py"
  goto END
)
where python >nul 2>&1
if not errorlevel 1 (
  python "%~dp0aplicar_v23.py"
  goto END
)
if exist "%USERPROFILE%\anaconda3\envs\ml_env_311\python.exe" (
  "%USERPROFILE%\anaconda3\envs\ml_env_311\python.exe" "%~dp0aplicar_v23.py"
  goto END
)
echo Python nao encontrado. Voce pode executar o aplicar_v23.py com seu Python existente.
:END
echo.
echo Feche esta janela apenas depois de ler a mensagem acima.
pause
