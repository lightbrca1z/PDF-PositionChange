#!/usr/bin/env bash
# macOS用の "PDF向きなおし.app" をビルドするスクリプト
#
# 使い方:
#   cd pdf-orient
#   python3 -m venv .venv-build
#   source .venv-build/bin/activate
#   pip install -r requirements-build.txt
#   ./scripts/build_mac.sh
#
# ビルド後、dist/PDF向きなおし.app が生成されます。

set -euo pipefail
cd "$(dirname "$0")/.."

APP_NAME="PDF向きなおし"

rm -rf build dist "${APP_NAME}.spec"

pyinstaller \
  --noconfirm \
  --clean \
  --onedir \
  --windowed \
  --name "${APP_NAME}" \
  --add-data "static:static" \
  --collect-all uvicorn \
  launcher.py

echo ""
echo "ビルド完了: dist/${APP_NAME}.app"
