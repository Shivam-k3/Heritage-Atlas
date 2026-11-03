"""Environment-backed configuration. Read values at call time so tests can override env."""

import os
import socket
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UPLOAD_DIR = REPO_ROOT / "uploads"
DEFAULT_DATABASE_URL = "postgresql://atlas:atlas@localhost:5432/atlas"
DEFAULT_FEATURE_PROMPTS = Path(__file__).with_name("feature_prompts.json")
DEFAULT_REVIEWERS = "asha,ravi,guest"

API_TITLE = "Heritage Atlas API"
API_VERSION = "0.2.0"


def database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def upload_dir() -> Path:
    return Path(os.getenv("UPLOAD_DIR", str(DEFAULT_UPLOAD_DIR))).resolve()


def cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def max_upload_bytes() -> int:
    return int(os.getenv("MAX_UPLOAD_MB", "15")) * 1024 * 1024


def related_clip_weight() -> float:
    return float(os.getenv("RELATED_CLIP_WEIGHT", "0.6"))


def job_max_retries() -> int:
    return int(os.getenv("JOB_MAX_RETRIES", "3"))


def job_lease_seconds() -> int:
    """A running job older than this is assumed abandoned and returned to the queue."""
    return int(os.getenv("JOB_LEASE_SECONDS", "300"))


def job_retry_backoff_seconds() -> int:
    """Base delay before a failed job becomes claimable again; doubles per retry."""
    return int(os.getenv("JOB_RETRY_BACKOFF_SECONDS", "10"))


def worker_id() -> str:
    return os.getenv("WORKER_ID", "").strip() or f"{socket.gethostname()}:{os.getpid()}"


def reviewers() -> list[str]:
    """Fixed demo reviewer identifiers. Not authentication; see docs/API.md."""
    raw = os.getenv("REVIEWERS", DEFAULT_REVIEWERS)
    return [name.strip().lower() for name in raw.split(",") if name.strip()]


def feature_prompts_path() -> Path:
    return Path(os.getenv("FEATURE_PROMPTS_PATH", str(DEFAULT_FEATURE_PROMPTS)))


def max_features() -> int:
    return int(os.getenv("MAX_FEATURES", "4"))


def clip_model_name() -> str:
    return os.getenv("CLIP_MODEL_NAME", "clip-ViT-B-32")


def text_embedding_model() -> str:
    return os.getenv("TEXT_EMBEDDING_MODEL", "all-MiniLM-L6-v2")


def model_device() -> str | None:
    value = os.getenv("MODEL_DEVICE", "").strip()
    return value or None


def ai_enabled() -> bool:
    return os.getenv("AI_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def ai_provider() -> str:
    return os.getenv("AI_PROVIDER", "gemini").strip().lower()


def gemini_api_key() -> str | None:
    value = os.getenv("GEMINI_API_KEY", "").strip()
    return value or None


def gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3-flash-preview").strip() or "gemini-3-flash-preview"


def ai_timeout_seconds() -> float:
    return max(1.0, float(os.getenv("AI_TIMEOUT_SECONDS", "30")))


def ai_max_output_tokens() -> int:
    return max(1, int(os.getenv("AI_MAX_OUTPUT_TOKENS", "700")))


def ai_temperature() -> float:
    return min(2.0, max(0.0, float(os.getenv("AI_TEMPERATURE", "0.3"))))


def ai_max_history_messages() -> int:
    return max(0, int(os.getenv("AI_MAX_HISTORY_MESSAGES", "10")))


def ai_max_requests_per_minute() -> int:
    return max(1, int(os.getenv("AI_MAX_REQUESTS_PER_MINUTE", "10")))


def ai_max_retries() -> int:
    return min(2, max(0, int(os.getenv("AI_MAX_RETRIES", "1"))))


def ai_max_concurrency() -> int:
    return min(4, max(1, int(os.getenv("AI_MAX_CONCURRENCY", "2"))))
