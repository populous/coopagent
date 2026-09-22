@echo off
setlocal
set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Virtual environment not found. Run setup.ps1 first.
    exit /b 1
)
set "PYTHONPATH=%ROOT%src"
"%PYTHON%" -m documentation_agent.rag_proposal %*
