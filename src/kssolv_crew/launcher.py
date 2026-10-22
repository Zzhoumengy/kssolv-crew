"""Persistent local app launcher; no terminal window is required after readiness."""
import contextlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from .config import resolve_kssolv
from .storage import atomic_json


def health(url):
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url + "/health", timeout=1) as response:
            return json.load(response)
    except (OSError, ValueError):
        return {}


def read_state(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def matches(state):
    url = state.get("url", "")
    if not url.startswith("http://127.0.0.1:"):
        return False
    result = health(url)
    return result.get("service") == "kssolv-crew" and result.get("instance_id") == state.get("instance_id")


@contextlib.contextmanager
def launch_lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "launch.lock").open("a+b") as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b"0")
            lock.flush()
        deadline = time.monotonic() + 40
        while True:
            try:
                lock.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise RuntimeError("Another launcher is still starting; try again in a moment")
                time.sleep(.2)
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)


def launch(project=None, root=None, port=8000, open_browser=True):
    project = Path(project or Path.cwd()).resolve()
    runtime = project / ".runtime"
    with launch_lock(runtime):
        state = read_state(runtime / "server.json")
        if not matches(state):
            root = resolve_kssolv(root, project=project)
            if not root.is_dir():
                raise ValueError("Cannot find kssolv-3o-dev; check its folder location")
            state = _start(project, root, port, runtime)
            atomic_json(runtime / "server.json", state)
        (runtime / "website.url").write_text("[InternetShortcut]\nURL=" + state["url"] + "\n", encoding="utf-8")
    print("Website is ready: " + state["url"], flush=True)
    print("Running in background. Use stop.cmd to stop it. Logs: " + str(runtime / "server.log"), flush=True)
    if open_browser:
        try:
            webbrowser.open(state["url"])
        except webbrowser.Error:
            print("Open the address above in your browser.", flush=True)
    return state


def _start(project, root, port, runtime):
    if not 1024 <= port <= 65525:
        raise ValueError("Choose a port in 1024..65525")
    for candidate in range(port, port + 11):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", candidate))
            except OSError:
                continue
        instance = secrets.token_hex(16)
        token = secrets.token_urlsafe(32)
        env = dict(os.environ, KSSOLV_INSTANCE_ID=instance, KSSOLV_SERVICE_TOKEN=token)
        args = [sys.executable, "-m", "kssolv_crew.cli", "serve", "--port", str(candidate),
                "--kssolv-dir", str(root), "--runs", str(project / "runs")]
        with (runtime / "server.log").open("a", encoding="utf-8") as log:
            options = {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
            proc = subprocess.Popen(args, cwd=project, env=env, stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=subprocess.STDOUT, close_fds=True, **options)
        state = {"url": f"http://127.0.0.1:{candidate}", "pid": proc.pid,
                 "instance_id": instance, "stop_token": token}
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            if matches(state):
                return state
            time.sleep(.2)
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)
            raise RuntimeError("Website did not become ready. See .runtime/server.log")
        # Another app may have grabbed the selected port between probe and bind.
        if health(state["url"]):
            continue
        raise RuntimeError("Website failed to start. See .runtime/server.log; run install.cmd if imports are missing")
    raise RuntimeError("No available port found; close another local service or choose a different port")


def stop(project=None):
    runtime = Path(project or Path.cwd()).resolve() / ".runtime"
    with launch_lock(runtime):
        state = read_state(runtime / "server.json")
        if not matches(state):
            print("Website is already stopped.")
            return
        request = urllib.request.Request(state["url"] + "/service/stop", method="POST", data=b"",
                                         headers={"X-Service-Token": state["stop_token"]})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=5) as response:
            response.read()
        deadline = time.monotonic() + 40
        while matches(state):
            if time.monotonic() > deadline:
                raise RuntimeError("Shutdown is still in progress; see .runtime/server.log")
            time.sleep(.2)
        (runtime / "server.json").unlink(missing_ok=True)
        print("Website stopped.")
