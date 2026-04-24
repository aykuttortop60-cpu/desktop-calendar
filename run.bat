@echo off
chcp 65001 > nul
echo Masaustu Takvim baslatiliyor...

:: Sanal ortam varsa kullan, yoksa sistemi dene
set VENV_PY="%~dp0.venv\Scripts\pythonw.exe"
if exist %VENV_PY% (
    %VENV_PY% "%~dp0main.py"
) else (
    :: Global ortam — gerekirse PyQt6 yükle
    pip show PyQt6 >nul 2>&1
    if %errorlevel% neq 0 (
        echo PyQt6 yukleniyor...
        pip install PyQt6
    )
    pythonw "%~dp0main.py"
)
