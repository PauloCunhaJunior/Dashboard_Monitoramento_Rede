@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ================================================
echo DASHBOARD - MONITORAMENTO DE TRAFEGO DE REDE
echo ================================================
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Criando o ambiente virtual...
    py -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar o ambiente Python.
        echo Tente no VS Code: python -m venv .venv
        pause
        exit /b 1
    )
    echo [2/3] Instalando dependencias (primeira execucao)...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar dependencias.
        pause
        exit /b 1
    )
)
echo [3/3] Abrindo painel em http://localhost:8501
echo Para encerrar, pressione Ctrl+C nesta janela.
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1
if errorlevel 1 (
    echo [ERRO] O painel nao iniciou. Confira README.md.
    pause
)
