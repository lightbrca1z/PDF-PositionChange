from __future__ import annotations

import io
import uuid
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pypdf import PdfReader, PdfWriter
from pydantic import BaseModel, Field

STATIC_DIR = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 40 * 1024 * 1024

app = FastAPI(title="PDF向きなおし")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# session_id -> PDF bytes
_sessions: dict[str, bytes] = {}


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
        raise HTTPException(status_code=400, detail="PDFファイルを選んでください")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空のファイルです")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="ファイルサイズは40MBまでです")

    try:
        reader = PdfReader(io.BytesIO(data))
        page_count = len(reader.pages)
        if page_count == 0:
            raise ValueError("ページがありません")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="PDFとして読み込めませんでした") from exc

    session_id = str(uuid.uuid4())
    _sessions[session_id] = data

    return {
        "session_id": session_id,
        "filename": file.filename,
        "page_count": page_count,
        "size": len(data),
    }


@app.post("/api/rotate")
def rotate(body: RotateRequest) -> Response:
    data = _sessions.get(body.session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="セッションが見つかりません。再度アップロードしてください")

    try:
        rotated = _rotate_pdf(data, body.degrees)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="回転に失敗しました") from exc

    _sessions[body.session_id] = rotated
    return Response(
        content=rotated,
        media_type="application/pdf",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/preview/{session_id}")
def preview(session_id: str) -> Response:
    data = _sessions.get(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/download/{session_id}")
def download(session_id: str, filename: str = "rotated.pdf") -> Response:
    data = _sessions.get(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    safe_name = Path(filename).name
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
    if not safe_name.startswith("向きなおし_"):
        safe_name = f"向きなおし_{safe_name}"

    # HTTPヘッダーはlatin-1しか扱えないため、日本語名はfilename*(RFC 5987)で渡す
    ascii_fallback = "rotated.pdf"
    encoded_name = quote(safe_name)

    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_fallback}"; '
                f"filename*=UTF-8''{encoded_name}"
            ),
            "Cache-Control": "no-store",
        },
    )
