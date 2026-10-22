import json
import os
import time
import uuid
from pathlib import Path


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        # Windows readers/antivirus may briefly deny replacement of an open file.
        for attempt in range(8):
            try:
                os.replace(temp, path)
                return
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(min(.01 * 2**attempt, .2))
    finally:
        temp.unlink(missing_ok=True)


def stage(output, status, **details):
    output = Path(output)
    event = {"time": time.time(), "status": status, **details}
    atomic_json(output / "status.json", event)
    with (output / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
