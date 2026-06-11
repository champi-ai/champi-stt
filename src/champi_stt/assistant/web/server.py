"""
Lightweight web configuration server for champi-stt.

Serves a browser UI at http://localhost:8765 to view and edit the
assistant configuration YAML. Changes are validated and written to disk;
an optional reload callback lets the caller hot-reload the running daemon.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

try:
    import uvicorn
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from champi_stt.assistant.service.config import AssistantConfig

_DEFAULT_HOST = "localhost"
_DEFAULT_PORT = 8765


def _config_to_dict(cfg: AssistantConfig) -> dict[str, Any]:
    return dataclasses.asdict(cfg)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _save_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=True)


def _build_html(config_json: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Champi STT — Configuration</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
    h1 {{ color: #333; }}
    textarea {{ width: 100%; height: 400px; font-family: monospace; font-size: 0.9rem; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
    .btn {{ padding: 0.5rem 1.2rem; border: none; border-radius: 4px; cursor: pointer; font-size: 0.95rem; margin-right: 0.5rem; }}
    .btn-save {{ background: #2563eb; color: white; }}
    .btn-reload {{ background: #16a34a; color: white; }}
    .btn-save:hover {{ background: #1d4ed8; }}
    .btn-reload:hover {{ background: #15803d; }}
    #status {{ margin-top: 1rem; padding: 0.5rem 0.75rem; border-radius: 4px; display: none; }}
    .ok {{ background: #dcfce7; color: #166534; }}
    .err {{ background: #fee2e2; color: #991b1b; }}
    pre {{ background: #f3f4f6; padding: 1rem; border-radius: 4px; overflow: auto; }}
  </style>
</head>
<body>
  <h1>Champi STT — Configuration</h1>
  <p>Edit the assistant configuration below. Changes are saved to disk immediately.</p>
  <textarea id="cfg" spellcheck="false"></textarea>
  <br><br>
  <button class="btn btn-save" onclick="save()">Save</button>
  <button class="btn btn-reload" onclick="reload()">Save &amp; Reload Daemon</button>
  <div id="status"></div>

  <script>
    const raw = {config_json};
    function toYaml(obj, indent) {{
      // Simple JSON display — server stores YAML
      return JSON.stringify(obj, null, 2);
    }}
    document.getElementById('cfg').value = JSON.stringify(raw, null, 2);

    function showStatus(msg, ok) {{
      const el = document.getElementById('status');
      el.textContent = msg;
      el.className = ok ? 'ok' : 'err';
      el.style.display = 'block';
      setTimeout(() => {{ el.style.display = 'none'; }}, 4000);
    }}

    async function save() {{
      let data;
      try {{ data = JSON.parse(document.getElementById('cfg').value); }}
      catch(e) {{ showStatus('JSON parse error: ' + e.message, false); return; }}
      const r = await fetch('/config', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(data)
      }});
      const body = await r.json();
      showStatus(r.ok ? 'Saved.' : ('Error: ' + body.detail), r.ok);
    }}

    async function reload() {{
      let data;
      try {{ data = JSON.parse(document.getElementById('cfg').value); }}
      catch(e) {{ showStatus('JSON parse error: ' + e.message, false); return; }}
      const r = await fetch('/config/reload', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(data)
      }});
      const body = await r.json();
      showStatus(r.ok ? 'Saved and daemon reload triggered.' : ('Error: ' + body.detail), r.ok);
    }}
  </script>
</body>
</html>
"""


def create_app(
    config_path: str | Path,
    reload_callback: Callable[[], None] | None = None,
) -> FastAPI:
    """
    Build the FastAPI application.

    Args:
        config_path:     Path to the YAML config file to read/write.
        reload_callback: Optional callable invoked after a save+reload request.
                         Use this to signal the running daemon to reload config.

    Returns:
        Configured FastAPI application instance.
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "fastapi and uvicorn are required for the web UI. "
            "Install with: pip install fastapi uvicorn"
        )

    app = FastAPI(title="Champi STT Config", docs_url=None, redoc_url=None)
    _path = Path(config_path)

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        data = _load_yaml(_path)
        return HTMLResponse(_build_html(json.dumps(data)))

    @app.get("/config")
    async def get_config() -> JSONResponse:
        return JSONResponse(_load_yaml(_path))

    @app.post("/config")
    async def save_config(request: Request) -> JSONResponse:
        try:
            data: dict[str, Any] = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc

        try:
            _save_yaml(_path, data)
            logger.info(f"Config saved to {_path}")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return JSONResponse({"status": "saved"})

    @app.post("/config/reload")
    async def save_and_reload(request: Request) -> JSONResponse:
        try:
            data: dict[str, Any] = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc

        try:
            _save_yaml(_path, data)
            logger.info(f"Config saved to {_path}")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        if reload_callback:
            try:
                reload_callback()
                logger.info("Daemon reload triggered")
            except Exception as exc:
                logger.warning(f"Reload callback failed: {exc}")

        return JSONResponse({"status": "saved", "reload": reload_callback is not None})

    return app


def serve(
    config_path: str | Path,
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    reload_callback: Callable[[], None] | None = None,
) -> None:
    """
    Start the configuration web server (blocking).

    Args:
        config_path:     Path to the YAML config file.
        host:            Bind address (default: localhost).
        port:            Port to listen on (default: 8765).
        reload_callback: Called when the browser requests save+reload.
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "fastapi and uvicorn are required. Install with: pip install fastapi uvicorn"
        )

    app = create_app(config_path, reload_callback=reload_callback)
    logger.info(f"Starting config server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")
