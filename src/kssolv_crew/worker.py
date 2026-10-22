"""Isolated worker; secret inputs arrive on stdin, never command line/files."""
import json
import os
import sys
from pathlib import Path


def main():
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["CREWAI_TELEMETRY_DISABLED"] = "true"
    os.environ["CREWAI_TRACING_ENABLED"] = "false"
    data = json.load(sys.stdin)
    output = Path(data["output"])
    # Keep incidental framework databases inside this isolated job, not AppData.
    os.environ["CREWAI_STORAGE_DIR"] = str((output / ".crew").resolve())
    from .storage import stage
    try:
        from .models import JobRequest
        from .workflow import BandFlow
        BandFlow(JobRequest.model_validate(data["request"]), output, data["root"], data["model"]).kickoff()
    except Exception as exc:
        # Avoid persisting remote exception messages that might contain credentials.
        current = json.loads((output / "status.json").read_text(encoding="utf-8")) if (output / "status.json").exists() else {}
        message = "Workflow failed; check stage history and MATLAB logs. Remote exception text is suppressed."
        if current.get("status") == "normalizing" and type(exc).__name__ == "AuthenticationError":
            message = "LLM API 认证失败，请检查密钥和模型是否匹配；DeepSeek 使用 deepseek/deepseek-flash。尚未执行 MATLAB 计算。"
        stage(output, "failed", failed_stage=current.get("status", "starting"), error_type=type(exc).__name__,
              error=message)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
