@echo off
setlocal
cd /d "%~dp0"

if not exist "venv_novo\Scripts\python.exe" (
    echo Criando ambiente virtual...
    python -m venv venv_novo
    if errorlevel 1 (
        echo.
        echo ERRO: nao foi possivel criar o ambiente virtual.
        echo Verifique se o Python esta instalado e no PATH do Windows.
        pause
        exit /b 1
    )
    venv_novo\Scripts\python.exe -m pip install --upgrade pip >nul
)

REM roda sempre (rapido se ja estiver tudo instalado) para pegar
REM dependencias novas adicionadas ao requirements.txt, tipo "requests"
echo Verificando dependencias...
venv_novo\Scripts\python.exe -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo.
    echo ERRO ao instalar as dependencias.
    pause
    exit /b 1
)

echo Iniciando o aplicativo...
venv_novo\Scripts\python.exe main.py

if errorlevel 1 (
    echo.
    echo O aplicativo fechou com erro. Veja a mensagem acima.
    pause
)
