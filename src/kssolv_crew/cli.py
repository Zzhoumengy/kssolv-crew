import argparse
import importlib.util
import json
import os
from pathlib import Path
from .config import resolve_kssolv


def main():
    parser = argparse.ArgumentParser(prog="kssolv-crew")
    sub = parser.add_subparsers(dest="command", required=True)
    desktop = sub.add_parser("desktop", help="Open the native desktop interface; no Web server")
    desktop.add_argument("--project", type=Path, default=Path.cwd())
    launch = sub.add_parser("launch", help="Start or reuse the persistent local website")
    launch.add_argument("--project", type=Path, default=Path.cwd())
    launch.add_argument("--kssolv-dir", type=Path)
    launch.add_argument("--port", type=int, default=8000)
    launch.add_argument("--no-browser", action="store_true")
    stop = sub.add_parser("stop", help="Stop the managed local website")
    stop.add_argument("--project", type=Path, default=Path.cwd())
    serve = sub.add_parser("serve", help="Start the local web server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--kssolv-dir", type=Path, default=None)
    serve.add_argument("--runs", type=Path, default=Path("runs"))
    serve.add_argument("--model", default=os.environ.get("KSSOLV_LLM_MODEL", "openai/gpt-4o-mini"))
    serve.add_argument("--timeout", type=float, default=7200)
    pack = sub.add_parser("bundle", help="Create a source ZIP with optional full KSSOLV folder")
    pack.add_argument("--project", type=Path, default=Path.cwd())
    pack.add_argument("--kssolv-dir", type=Path)
    pack.add_argument("--source-only", action="store_true", help="Exclude KSSOLV even if discovered")
    pack.add_argument("--output", type=Path)
    sub.add_parser("doctor", help="Check imports without starting MATLAB or calling APIs")
    args = parser.parse_args()
    if args.command == "desktop":
        from .desktop import main as desktop_main
        desktop_main(args.project)
    elif args.command == "launch":
        from .launcher import launch
        launch(args.project, args.kssolv_dir, args.port, not args.no_browser)
    elif args.command == "stop":
        from .launcher import stop
        stop(args.project)
    elif args.command == "bundle":
        from .bundle import bundle
        root = resolve_kssolv(args.kssolv_dir, project=args.project)
        vendor = None if args.source_only else (root if root.is_dir() or args.kssolv_dir or os.environ.get("KSSOLV_ROOT") else None)
        label = "with-kssolv" if vendor else "source"
        output = args.output or args.project / "dist" / f"kssolv-crew-{label}.zip"
        print(bundle(args.project, output, vendor))
    elif args.command == "doctor":
        checks = {}
        for name in ["crewai", "fastapi", "mp_api", "pymatgen", "numpy", "matlab.engine"]:
            try:
                checks[name] = importlib.util.find_spec(name) is not None
            except ModuleNotFoundError:
                checks[name] = False
        print(json.dumps(checks, indent=2))
        root = resolve_kssolv()
        print(json.dumps({"kssolv_root": str(root), "kssolv_directory_present": root.is_dir()}, ensure_ascii=False, indent=2))
    else:
        from .server import create_app
        import uvicorn
        app = create_app(args.runs, args.kssolv_dir, args.model, args.timeout)
        server = uvicorn.Server(uvicorn.Config(app, host=args.host, port=args.port, access_log=False))
        app.state.stop_callback = lambda: setattr(server, "should_exit", True)
        server.run()


if __name__ == "__main__":
    main()
