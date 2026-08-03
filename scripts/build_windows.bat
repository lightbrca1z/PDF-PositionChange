@echo off
REM Windows用の "PDF向きなおし.exe" をビルドするスクリプト
REM
REM 使い方 (コマンドプロンプトで):
REM   cd pdf-orient
REM   py -m venv .venv-build
REM   .venv-build\Scripts\activate
REM   pip install -r requirements-build.txt
REM   scripts\build_windows.bat
REM
REM ビルド後、dist\PDF向きなおし.exe が生成されます。

cd /d "%~dp0\.."

set APP_NAME=PDF向きなおし

rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del "%APP_NAME%.spec" 2>nul

pyinstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --console ^
  --name "%APP_NAME%" ^
  --add-data "static;static" ^
  --collect-all uvicorn ^
  launcher.py

echo.
echo ビルド完了: dist\%APP_NAME%.exe
