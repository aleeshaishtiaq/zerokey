@echo off
cd /d "%~dp0\.."
echo Installing backend packages... > scripts\test_output.txt
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt >> scripts\test_output.txt 2>&1
echo Running tests... >> scripts\test_output.txt
".venv\Scripts\python.exe" -m pytest tests -q >> scripts\test_output.txt 2>&1
echo FINISHED >> scripts\test_output.txt
