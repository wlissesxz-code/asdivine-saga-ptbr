@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python 3.9+ nao encontrado. Instale em https://www.python.org/downloads/ ^(marque "Add Python to PATH"^) e rode de novo.
  pause & exit /b 1
)
echo ==================================================
echo  Asdivine Saga - Traducao PT-BR
echo ==================================================
echo  1 = Instalar - Portugues COM acentos (recomendado)
echo  2 = Instalar - Portugues SEM acentos
echo  3 = Somente tela cheia (jogo em ingles)
echo  4 = Restaurar o jogo original
echo  5 = Verificar compatibilidade (nao altera nada)
echo.
set /p OPC=Escolha 1-5: 
set "ARGS="
if "%OPC%"=="1" set "CMD=instalar"
if "%OPC%"=="2" set "CMD=instalar" & set "ARGS=--sem-acentos"
if "%OPC%"=="3" set "CMD=instalar" & set "ARGS=--so-fullscreen"
if "%OPC%"=="4" set "CMD=restaurar"
if "%OPC%"=="5" set "CMD=verificar"
if not defined CMD (echo Opcao invalida. & pause & exit /b 1)
echo.
echo Feche o jogo antes de continuar.
pause
%PY% -m pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (echo Falha ao instalar dependencias do Python. & pause & exit /b 1)
%PY% ptbr_cli.py %CMD% %ARGS%
echo.
pause
