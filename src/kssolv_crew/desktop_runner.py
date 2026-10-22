"""Desktop task execution with no HTTP server or browser dependency."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import uuid
from .config import resolve_kssolv
from .models import JobRequest
from .processes import kill_worker
from .storage import atomic_json, stage

TERMINAL = {"prepared", "completed_unverified", "failed", "timed_out", "interrupted", "cancelled"}
STATUS_LABELS = {"queued": "等待开始", "starting": "启动计算流程", "normalizing": "规范化化学式",
    "fetching_structure": "获取材料结构", "preparing": "生成 MATLAB 输入与 k 路径",
    "calculating": "MATLAB 正在计算 SCF / NSCF", "reporting": "生成报告",
    "prepared": "输入文件已生成（未执行计算）", "completed_unverified": "计算已返回（收敛待核验）",
    "failed": "任务失败", "timed_out": "任务超时", "interrupted": "任务已中断", "cancelled": "任务已停止"}


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def history(project):
    jobs = []
    for path in (Path(project) / "runs").glob("*/status.json"):
        state = read_json(path)
        if state:
            metadata = read_json(path.parent / "selection.json")
            jobs.append({"id": path.parent.name, "output": path.parent,
                         "material": metadata.get("formula", "—"), **state})
    return sorted(jobs, key=lambda j: j.get("time", 0), reverse=True)[:200]


class DesktopRunner:
    def __init__(self, project, root=None, model="openai/gpt-4o-mini", timeout=7200):
        self.project = Path(project).resolve()
        self.root = resolve_kssolv(root, project=self.project)
        self.model, self.timeout = model, timeout
        self.thread = None
        self.proc = None
        self.output = None
        self.last_error = None
        self._cancel = threading.Event()
        self._proc_lock = threading.Lock()

    @property
    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def submit(self, request):
        if self.running:
            raise RuntimeError("已有任务正在运行，请先等待完成或停止它。")
        request = JobRequest.model_validate(request)
        if request.mode == "run" and (not self.root.is_dir() or self.root.name != "kssolv-3o-dev"):
            raise ValueError("未检测到 KSSOLV。请将完整的 kssolv-3o-dev 文件夹放入项目目录或与项目同级，或重新解压完整发布包，然后重试。")
        self._cancel.clear()
        self.last_error = None
        self.output = self.project / "runs" / str(uuid.uuid4())
        self.output.mkdir(parents=True)
        # Never save API keys or the full natural-language prompt.
        atomic_json(self.output / "desktop_job.json", {"mode": request.mode,
            "material_id": request.material_id, "parameters": request.parameters.model_dump()})
        stage(self.output, "queued")
        self.thread = threading.Thread(target=self._execute, args=(request, self.output), daemon=True)
        self.thread.start()
        return self.output

    def _execute(self, request, output):
        try:
            payload = request.model_dump(mode="json")
            payload["mp_api_key"] = request.mp_api_key.get_secret_value()
            payload["llm_api_key"] = request.llm_api_key.get_secret_value()
            executable = Path(sys.executable)
            if os.name == "nt" and executable.name.lower() == "pythonw.exe":
                executable = executable.with_name("python.exe")
            with self._proc_lock:
                if self._cancel.is_set():
                    stage(output, "cancelled")
                    return
                stage(output, "starting")
                options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
                self.proc = subprocess.Popen([str(executable), "-m", "kssolv_crew.worker"],
                    cwd=self.project, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    text=True, encoding="utf-8", **options)
            content = json.dumps({"request": payload, "output": str(output), "root": str(self.root), "model": self.model})
            try:
                self.proc.communicate(content, timeout=self.timeout)
            except subprocess.TimeoutExpired:
                kill_worker(self.proc)
                stage(output, "timed_out", error="任务超过运行时限，请检查 MATLAB 日志。")
                return
            if self._cancel.is_set():
                stage(output, "cancelled")
            elif read_json(output / "status.json").get("status") not in TERMINAL:
                stage(output, "failed", error="工作进程提前退出，请检查依赖和日志。")
        except Exception as exc:
            self.last_error = "启动或执行任务失败，请检查目录权限和日志。"
            try:
                stage(output, "failed", error_type=type(exc).__name__, error="启动或执行任务失败；异常原文未写入，以保护密钥。")
            except OSError:
                pass
        finally:
            with self._proc_lock:
                self.proc = None

    def cancel(self):
        self._cancel.set()
        with self._proc_lock:
            proc = self.proc
        if proc is not None:
            kill_worker(proc)
