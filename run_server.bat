@echo off
echo Dang kich hoat moi truong ao...
call .\virtual\Scripts\activate

if %errorlevel% neq 0 (
    echo [LOI] Khong the kich hoat moi truong ao tai .\virtual\Scripts\activate
    pause
    exit /b %errorlevel%
)

echo Dang chay Medimate RAG Service...
python -m main

pause
