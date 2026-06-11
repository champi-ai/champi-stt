"""
REST API server for champi-stt.

Exposes:
  POST /transcribe      — Upload an audio file, returns transcription text
  GET  /status          — Service health and loaded provider info
  POST /command         — Inject a text command into the assistant pipeline
  WS   /stream          — WebSocket for real-time transcript streaming
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from loguru import logger

try:
    import uvicorn
    from fastapi import (
        FastAPI,
        HTTPException,
        UploadFile,
        WebSocket,
        WebSocketDisconnect,
    )
    from fastapi.responses import JSONResponse

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

_DEFAULT_HOST = "localhost"
_DEFAULT_PORT = 8766

_provider: Any = None
_command_queue: asyncio.Queue[str] | None = None


def _require_fastapi() -> None:
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "fastapi and uvicorn are required for the REST API. "
            "Install with: pip install 'champi-stt[webui]'"
        )


def create_api_app(
    provider: Any | None = None,
    command_queue: asyncio.Queue[str] | None = None,
) -> FastAPI:
    """Build the FastAPI REST application.

    Args:
        provider:       An initialized BaseSTTProvider used for /transcribe and /stream.
        command_queue:  asyncio.Queue that receives injected text commands from POST /command.

    Returns:
        Configured FastAPI application.
    """
    _require_fastapi()

    app = FastAPI(
        title="Champi STT API", version="1.0", docs_url="/docs", redoc_url=None
    )
    _state: dict[str, Any] = {"provider": provider, "command_queue": command_queue}

    @app.get("/status")
    async def status() -> JSONResponse:
        prov = _state["provider"]
        return JSONResponse(
            {
                "status": "ok",
                "provider": prov.__class__.__name__ if prov else None,
                "ready": bool(prov and getattr(prov, "is_loaded", False)),
            }
        )

    @app.post("/transcribe")
    async def transcribe(file: UploadFile) -> JSONResponse:
        prov = _state["provider"]
        if prov is None:
            raise HTTPException(status_code=503, detail="No provider configured")

        try:
            audio_bytes = await file.read()
        except Exception as exc:
            raise HTTPException(
                status_code=400, detail=f"Could not read upload: {exc}"
            ) from exc

        t0 = time.monotonic()
        try:
            result = await prov.transcribe(audio_bytes)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        elapsed = round(time.monotonic() - t0, 3)
        text = (
            result
            if isinstance(result, str)
            else result.get("text", "")
            if isinstance(result, dict)
            else str(result)
        )
        return JSONResponse({"text": text, "processing_time": elapsed})

    @app.post("/command")
    async def inject_command(payload: dict[str, Any]) -> JSONResponse:
        text = payload.get("text", "").strip()
        if not text:
            raise HTTPException(
                status_code=400, detail="'text' field is required and must not be empty"
            )

        q = _state["command_queue"]
        if q is None:
            raise HTTPException(status_code=503, detail="Command queue not configured")

        await q.put(text)
        logger.info(f"Command injected via API: {text!r}")
        return JSONResponse({"status": "queued", "text": text})

    @app.websocket("/stream")
    async def stream(websocket: WebSocket) -> None:
        await websocket.accept()
        prov = _state["provider"]
        if prov is None:
            await websocket.send_json({"error": "No provider configured"})
            await websocket.close(code=1011)
            return

        try:

            async def _audio_source() -> AsyncIterator[bytes]:
                while True:
                    try:
                        data = await asyncio.wait_for(
                            websocket.receive_bytes(), timeout=30.0
                        )
                        if data == b"__END__":
                            break
                        yield data
                    except TimeoutError:
                        break

            if hasattr(prov, "stream_transcribe"):
                async for chunk in prov.stream_transcribe(_audio_source()):
                    await websocket.send_json(
                        {
                            "text": chunk.text,
                            "is_final": chunk.is_final,
                            "language": chunk.language,
                        }
                    )
            else:
                await websocket.send_json(
                    {"error": "Provider does not support streaming"}
                )

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as exc:
            logger.warning(f"WebSocket error: {exc}")
            await websocket.close(code=1011)

    return app


def serve_api(
    provider: Any | None = None,
    command_queue: asyncio.Queue[str] | None = None,
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
) -> None:
    """Start the REST API server (blocking).

    Args:
        provider:       STT provider for transcription endpoints.
        command_queue:  Queue for POST /command injections.
        host:           Bind address (default: localhost).
        port:           Port to listen on (default: 8766).
    """
    _require_fastapi()
    app = create_api_app(provider=provider, command_queue=command_queue)
    logger.info(f"Starting REST API at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")
