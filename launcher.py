"""PDF向きなおし - デスクトップ起動用エントリーポイント

このファイルを PyInstaller でビルドすると、
Windows用の .exe / macOS用の .app を作成できます。

起動すると:
  1. ローカルでWebサーバー（main.py の FastAPI アプリ）を起動
  2. 既定のブラウザで自動的にアプリ画面を開く

終了するには、開いたウィンドウ（コンソール/ターミナル）を閉じるか、
Ctrl+C（Windows）/ Control+C（Mac）を押してください。
"""

from __future__ import annotations

import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

HOST = "127.0.0.1"
PREFERRED_PORT = 8765


def _app_dir() -> Path:
    """exe/app化されている場合は展開先のディレクトリを返す"""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base)
    return Path(__file__).parent


def _find_free_port(preferred: int) -> int:
    for port in range(preferred, preferred + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((HOST, port))
                return port
            except OSError:
                continue
    raise RuntimeError("空いているポートが見つかりませんでした")


def _wait_for_server(port: int, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _open_browser_when_ready(port: int) -> None:
    if _wait_for_server(port):
        webbrowser.open(f"http://{HOST}:{port}/")


def main() -> None:
    # main.py（FastAPIアプリ）を読み込めるようにパスを通す
    sys.path.insert(0, str(_app_dir()))
    from main import app  # noqa: E402  (パス設定後にインポートするため)

    port = _find_free_port(PREFERRED_PORT)
    url = f"http://{HOST}:{port}/"

    threading.Thread(
        target=_open_browser_when_ready, args=(port,), daemon=True
    ).start()

    print("=" * 50)
    print(" PDF向きなおし を起動しています…")
    print(f" ブラウザで開かない場合はこちら: {url}")
    print(" 終了するには、このウィンドウを閉じてください。")
    print("=" * 50)

    uvicorn.run(app, host=HOST, port=port, log_level="warning")


if __name__ == "__main__":
    main()
