import asyncio
import hmac
import json
import os
import secrets
import subprocess
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .models import JobRequest
from .storage import atomic_json, stage
from .config import resolve_kssolv
from .processes import kill_worker

TERMINAL = {"prepared", "completed_unverified", "failed", "timed_out", "interrupted", "cancelled"}


def create_app(runs=None, root=None, model=None, timeout=None, max_jobs=16):
    runs = Path(runs or os.environ.get("KSSOLV_RUNS", "runs")).resolve()
    root = str(resolve_kssolv(root))
    model = model or os.environ.get("KSSOLV_LLM_MODEL", "openai/gpt-4o-mini")
    timeout = float(timeout or os.environ.get("KSSOLV_TIMEOUT", "7200"))
    tasks, processes = set(), set()
    gate = asyncio.Semaphore(1)  # One MATLAB process at a time per server.

    @asynccontextmanager
    async def lifespan(app):
        runs.mkdir(parents=True, exist_ok=True)
        for statefile in runs.glob("*/status.json"):
            if (statefile.parent / "desktop_job.json").exists():
                continue
            if json.loads(statefile.read_text(encoding="utf-8")).get("status") not in TERMINAL:
                stage(statefile.parent, "interrupted", error="Server restarted; resubmit with credentials")
        yield
        for proc in list(processes):
            await asyncio.to_thread(kill_worker, proc)
        for task in list(tasks):
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(title="KSSOLV Crew", lifespan=lifespan)
    instance_id = os.environ.get("KSSOLV_INSTANCE_ID", "foreground")
    stop_token = os.environ.get("KSSOLV_SERVICE_TOKEN", "")

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Pydantic's default errors may echo secret input values.
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(e["loc"]), "type": e["type"], "msg": "Invalid input"} for e in exc.errors()]})

    async def execute(request, output):
        try:
            async with gate:
                stage(output, "starting")
                payload = request.model_dump(mode="json")
                payload["mp_api_key"] = request.mp_api_key.get_secret_value()
                payload["llm_api_key"] = request.llm_api_key.get_secret_value()
                proc = subprocess.Popen([sys.executable, "-m", "kssolv_crew.worker"], stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                    start_new_session=os.name != "nt")
                processes.add(proc)
                try:
                    content = json.dumps({"request": payload, "output": str(output), "root": root, "model": model})
                    await asyncio.to_thread(proc.communicate, content, timeout=timeout)
                    state = json.loads((output / "status.json").read_text(encoding="utf-8"))["status"]
                    if state not in TERMINAL:
                        stage(output, "failed", error="Worker exited before completing workflow")
                except subprocess.TimeoutExpired:
                    await asyncio.to_thread(kill_worker, proc)
                    stage(output, "timed_out", error="Execution deadline exceeded; inspect MATLAB processes if necessary")
                finally:
                    processes.discard(proc)
        except asyncio.CancelledError:
            stage(output, "interrupted", error="Server stopped; resubmit with credentials")
            raise
        except Exception as exc:
            stage(output, "failed", error_type=type(exc).__name__, error="Worker launch or execution failed")

    def authorized(job_id, authorization):
        try:
            if str(uuid.UUID(job_id)) != job_id:
                raise ValueError()
            output = runs / job_id
            expected = json.loads((output / "access.json").read_text(encoding="utf-8"))["token_hash"]
            import hashlib
            token = (authorization or "").removeprefix("Bearer ")
            if not hmac.compare_digest(expected, hashlib.sha256(token.encode()).hexdigest()):
                raise ValueError()
            return output
        except (ValueError, OSError, KeyError):
            raise HTTPException(404, "Job not found")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (Path(__file__).parent / "web" / "index.html").read_text(encoding="utf-8")

    @app.get("/health")
    def health():
        return {"service": "kssolv-crew", "instance_id": instance_id,
                "status": "ok", "kssolv_directory_present": Path(root).is_dir(),
                "calculation_verified": False}

    @app.post("/service/stop")
    def stop_service(x_service_token: str = Header("")):
        if not stop_token or not hmac.compare_digest(stop_token, x_service_token):
            raise HTTPException(404, "Service control unavailable")
        callback = getattr(app.state, "stop_callback", None)
        if callback is None:
            raise HTTPException(409, "Service control unavailable")
        callback()
        return {"status": "stopping"}

    @app.post("/jobs", status_code=202)
    async def submit(request: JobRequest):
        if len(tasks) >= max_jobs:
            raise HTTPException(429, "Queue full")
        if request.mode == "run" and not Path(root).is_dir():
            raise HTTPException(503, "Configure KSSOLV_ROOT to an existing kssolv-3o-dev folder")
        job_id, token = str(uuid.uuid4()), secrets.token_urlsafe(32)
        output = runs / job_id
        output.mkdir(parents=True)
        import hashlib
        atomic_json(output / "access.json", {"token_hash": hashlib.sha256(token.encode()).hexdigest()})
        stage(output, "queued")
        task = asyncio.create_task(execute(request, output))
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        return {"job_id": job_id, "token": token, "status": "queued"}

    @app.get("/jobs/{job_id}")
    def status(job_id: str, authorization: str | None = Header(None)):
        output = authorized(job_id, authorization)
        result = json.loads((output / "status.json").read_text(encoding="utf-8"))
        result["artifacts"] = [p.name for p in sorted(output.iterdir()) if p.is_file()
                               and p.name not in {"access.json", "status.tmp"} and p.suffix != ".tmp"]
        return result

    @app.get("/jobs/{job_id}/artifacts/{filename}")
    def artifact(job_id: str, filename: str, authorization: str | None = Header(None)):
        output = authorized(job_id, authorization)
        path = (output / filename).resolve()
        if path.parent != output or filename == "access.json" or path.suffix == ".tmp" or not path.is_file():
            raise HTTPException(404, "Artifact not found")
        return FileResponse(path, filename=path.name)

    return app
