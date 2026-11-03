"""Optional Roboflow download. Skipped cleanly when credentials are not configured.

Usage:
    pip install -r backend/requirements-optional.txt
    set ROBOFLOW_API_KEY, ROBOFLOW_WORKSPACE, ROBOFLOW_PROJECT, ROBOFLOW_VERSION
    python -m scripts.dataset.download_roboflow
"""

import os
from pathlib import Path


def main() -> int:
    required = ["ROBOFLOW_API_KEY", "ROBOFLOW_WORKSPACE", "ROBOFLOW_PROJECT", "ROBOFLOW_VERSION"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print("Roboflow is optional; missing " + ", ".join(missing) + ". Nothing downloaded.")
        return 0
    try:
        from roboflow import Roboflow
    except ImportError:
        print(
            "Install the optional dependency first: pip install -r backend/requirements-optional.txt"
        )
        return 1

    location = Path(os.getenv("ROBOFLOW_DIR", "data/raw/roboflow"))
    location.mkdir(parents=True, exist_ok=True)
    project = (
        Roboflow(api_key=os.environ["ROBOFLOW_API_KEY"])
        .workspace(os.environ["ROBOFLOW_WORKSPACE"])
        .project(os.environ["ROBOFLOW_PROJECT"])
    )
    dataset = project.version(int(os.environ["ROBOFLOW_VERSION"])).download(
        os.getenv("ROBOFLOW_FORMAT", "coco"), location=str(location)
    )
    print(f"Roboflow dataset downloaded to {dataset.location}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
