from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import TypedDict
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pypdf import PdfReader, PdfWriter

STATIC_DIR = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 40 * 1024 * 1024

app = FastAPI(title="PDF向きなおし")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class SessionData(TypedDict):
    data: bytes
    filename: str


# session_id -> SessionData (バイトデータと元のファイル名を保持)
_sessions: dict[str, SessionData] = {}


class RotateRequest(BaseModel):
    session_id: str
    degrees: int = Field(..., description="90, -90, or 180")


def _rotate_pdf(data: bytes, degrees: int) -> bytes:
    if degrees not in (90, -90, 180, 270, -180, -270):
        raise ValueError("対応していない角度です")

    reader = PdfReader(io.BytesIO(data))
    if len(reader.pages) == 0:
        raise ValueError("ページがありません")

    writer = PdfWriter()
    for page in reader.pages:
        page.rotate(degrees)
        page.transfer_rotation_to_content()
        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="PDFファイルを選んでください"
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空のファイルです")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400, detail="ファイルサイズは40MBまでです"
        )

    try:
        reader = PdfReader(io.BytesIO(data))
        page_count = len(reader.pages)
        if page_count == 0:
            raise ValueError("ページがありません")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400, detail="PDFとして読み込めませんでした"
        ) from exc

    session_id = str(uuid.uuid4())
    # 元のファイル名を保持
    _sessions[session_id] = {
        "data": data,
        "filename": Path(file.filename).name,
    }

    return {
        "session_id": session_id,
        "filename": file.filename,
        "page_count": page_count,
        "size": len(data),
    }


@app.post("/api/rotate")
def rotate(body: RotateRequest) -> Response:
    session = _sessions.get(body.session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="セッションが見つかりません。再度アップロードしてください",
        )

    try:
        rotated = _rotate_pdf(session["data"], body.degrees)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail="回転に失敗しました"
        ) from exc

    session["data"] = rotated
    return Response(
        content=rotated,
        media_type="application/pdf",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/preview/{session_id}")
def preview(session_id: str) -> Response:
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=404, detail="セッションが見つかりません"
        )
    return Response(
        content=session["data"],
        media_type="application/pdf",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/download/{session_id}")
def download(session_id: str) -> Response:
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=404, detail="セッションが見つかりません"
        )

    # 「向きなおし_」を付けず、アップロード時の元のファイル名を使用
    filename = session["filename"]

    ascii_fallback = "download.pdf"
    encoded_name = quote(filename)

    return Response(
        content=session["data"],
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_fallback}"; '
                f"filename*=UTF-8''{encoded_name}"
            ),
            "Cache-Control": "no-store",
        },
    )