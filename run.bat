@echo off
cd /d "%~dp0"
if "%1"=="test" (
    python -m pycodestyle src tests
    if errorlevel 1 exit /b 1
    python -m coverage run -m unittest discover -b -s tests
    if errorlevel 1 exit /b 1
    python -m coverage report -m > coverage_report.txt
    if errorlevel 1 exit /b 1
    python -m coverage report -m
    exit /b
)
python -m src.main %*
