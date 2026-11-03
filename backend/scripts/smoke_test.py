"""End-to-end smoke test: upload -> worker -> search -> review.

Needs a running API (uvicorn app.main:app), a running worker (python worker.py) and
DATABASE_URL in .env. Usage:

    python scripts/smoke_test.py --stepwell a.jpg --fort b.jpg --temple c.jpg

Exits 0 only when every check passes; 1 on the first failed check.
"""

import argparse
import json
import mimetypes
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.db import connect  # noqa: E402

REQUEST_TIMEOUT = 180
POLL_INTERVAL = 1.0


class SmokeFailure(Exception):
    """A smoke-test check failed."""


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def _request(
    url: str, data: bytes | None = None, content_type: str | None = None, method: str = "GET"
) -> object:
    request = urllib.request.Request(url, data=data, method=method)  # noqa: S310 - local http only
    if content_type:
        request.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:  # noqa: S310
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise SmokeFailure(f"{method} {url} -> {exc.code}: {body}") from exc


def _get(url: str, **params: object) -> Any:
    query = urllib.parse.urlencode(
        {key: value for key, value in params.items() if value is not None}
    )
    return _request(f"{url}?{query}" if query else url)


def _multipart(fields: dict[str, str], file_path: pathlib.Path) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode()
        )
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{file_path.name}"\r\nContent-Type: {mime}\r\n\r\n'.encode()
    )
    parts.append(file_path.read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _upload(base_url: str, file_path: pathlib.Path, fields: dict[str, str]) -> dict:
    body, content_type = _multipart(fields, file_path)
    return _request(f"{base_url}/images/upload", body, content_type, "POST")  # type: ignore[return-value]


def _wait_for_job(base_url: str, job_id: int, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = _get(f"{base_url}/jobs/{job_id}")
        if job["status"] == "done":  # type: ignore[index]
            return job  # type: ignore[return-value]
        if job["status"] == "failed":  # type: ignore[index]
            raise SmokeFailure(f"job {job_id} failed: {job['error']}")  # type: ignore[index]
        time.sleep(POLL_INTERVAL)
    raise SmokeFailure(f"job {job_id} not done after {timeout:.0f}s")


def _db_state(image_id: int) -> tuple[int, int, list[dict]]:
    with connect() as conn:
        row = conn.execute(
            """SELECT vector_dims(i.clip_embedding) AS clip_dims,
                      vector_dims(s.description_embedding) AS desc_dims
               FROM images i JOIN sites s ON s.id=i.site_id WHERE i.id=%s""",
            (image_id,),
        ).fetchone()
        tags = conn.execute(
            """SELECT it.id, t.label, it.score, it.status FROM image_tags it
               JOIN tags t ON t.id=it.tag_id WHERE it.image_id=%s
               ORDER BY it.score DESC NULLS LAST""",
            (image_id,),
        ).fetchall()
    if row is None:
        raise RuntimeError(f"image {image_id} missing from database")
    return row["clip_dims"], row["desc_dims"], tags


def _check_scores(rows: list[dict], label: str) -> None:
    for row in rows:
        _check(isinstance(row.get("score"), (int, float)), f"{label}: missing score in {row}")
        _check(-1.0001 <= row["score"] <= 1.0001, f"{label}: score is not a cosine: {row}")


def _print_tags(name: str, tags: list[dict]) -> None:
    print(f"  {name}:")
    for tag in tags:
        print(f"    {tag['label']:<22} {tag['score']:+.4f}  {tag['status']}")


def _check_review(base_url: str, uploaded: list[dict]) -> None:
    """Review an auto tag when one exists, otherwise add a human tag.

    With every feature threshold null the worker emits no auto tags by design, so an empty
    review queue is a valid outcome. Both paths must keep provenance and audit history.
    """
    reviewers = _get(f"{base_url}/review/reviewers")
    _check(isinstance(reviewers, list) and bool(reviewers), "no reviewers configured")
    reviewer = reviewers[0]

    queue = _get(f"{base_url}/review/queue", limit=500)
    _check(isinstance(queue, list), "review queue is not a list")
    our_image_ids = {item["image_id"] for item in uploaded}
    candidates = [tag for tag in queue if tag["image_id"] in our_image_ids]  # type: ignore[union-attr]

    checks: list[tuple[int, int, str]] = []
    if len(candidates) >= 2:
        confirm, reject = candidates[0], candidates[-1]
        _check(confirm["id"] != reject["id"], "confirm and reject picked the same tag")
        for action, tag in (("confirm", confirm), ("reject", reject)):
            status = "verified" if action == "confirm" else "rejected"
            result = _request(
                f"{base_url}/review/tags/{tag['id']}",
                json.dumps({"action": action, "reviewer": reviewer}).encode(),
                "application/json",
                "POST",
            )
            _check(result["status"] == status, f"{action} returned {result['status']}")  # type: ignore[index]
            checks.append((int(tag["image_id"]), int(tag["id"]), status))
            print(f"  {action} tag {tag['id']} ({tag['label']}) -> {status}")
    else:
        print(f"  no auto tags in this run; adding human tags as {reviewer}")
        for image in uploaded[:2]:
            result = _request(
                f"{base_url}/review/tags/add",
                json.dumps(
                    {
                        "image_id": image["image_id"],
                        "label": "smoke test carving",
                        "reviewer": reviewer,
                    }
                ).encode(),
                "application/json",
                "POST",
            )
            _check(
                result["status"] == "added_by_human",  # type: ignore[index]
                f"human tag returned {result['status']}",  # type: ignore[index]
            )
            history = _get(f"{base_url}/review/history/{result['id']}")  # type: ignore[index]
            _check(
                isinstance(history, list) and bool(history),
                f"human tag {result['id']} has no audit history",  # type: ignore[index]
            )
            _check(
                history[-1]["new_status"] == "added_by_human",
                "audit history does not record the human tag",
            )
            checks.append((int(image["image_id"]), int(result["id"]), "added_by_human"))  # type: ignore[index]
            print(f"  added human tag {result['id']} -> added_by_human")  # type: ignore[index]

    site_ids = {item["image_id"]: item["site_id"] for item in uploaded}
    statuses: dict[int, str] = {}
    for site_id in {site_ids[image_id] for image_id, _, _ in checks}:
        site = _get(f"{base_url}/sites/{site_id}")
        statuses.update(
            {
                int(tag["id"]): str(tag["status"])
                for image in site["images"]
                for tag in image["tags"]
            }
        )
    for _, tag_id, expected in checks:
        _check(statuses.get(tag_id) == expected, f"tag {tag_id} is not {expected} on site detail")


def _run(args: argparse.Namespace) -> None:
    base_url = args.base_url.rstrip("/")
    photos = [
        (
            "stepwell",
            args.stepwell,
            {
                "site_name": "Rani ki Vav",
                "region": "Gujarat",
                "lat": "23.8593",
                "lon": "72.1018",
                "description": "Stepwell with carved stone pillars and sculptural carvings",
            },
        ),
        (
            "fort",
            args.fort,
            {
                "site_name": "Junagarh Fort",
                "region": "Rajasthan",
                "lat": "28.0200",
                "lon": "73.3140",
                "description": "Desert fort with stone arches, brackets and a decorative facade",
            },
        ),
        (
            "temple",
            args.temple,
            {
                "site_name": "Sun Temple Modhera",
                "region": "Gujarat",
                "lat": "23.5836",
                "lon": "72.1339",
                "description": "Stone temple with carved pillars, jali work and domes",
            },
        ),
    ]
    for _, path, _ in photos:
        _check(path.is_file(), f"photo not found: {path}")

    uploaded: list[dict] = []
    first_upload_seconds: float | None = None
    print("Upload -> worker -> database")
    for index, (kind, path, fields) in enumerate(photos):
        started = time.monotonic()
        result = _upload(base_url, path, {**fields, "author": args.author, "licence": args.licence})
        _check(result["status"] == "queued", f"{kind} upload did not return status queued")
        _wait_for_job(base_url, result["job_id"], args.timeout)
        if index == 0:
            first_upload_seconds = time.monotonic() - started
        clip_dims, desc_dims, tags = _db_state(result["image_id"])
        _check(clip_dims == 512, f"{kind}: clip_embedding has {clip_dims} dims, expected 512")
        _check(
            desc_dims == 384, f"{kind}: description_embedding has {desc_dims} dims, expected 384"
        )
        # Every feature threshold is null until human labels exist, so zero tags is valid.
        _check(
            all(tag["status"] == "auto" for tag in tags), f"{kind}: non-auto tag after processing"
        )
        _check(all(tag["score"] is not None for tag in tags), f"{kind}: auto tag without a score")
        if tags:
            _print_tags(kind, tags)
        else:
            print(f"  {kind}: no auto tags (all feature thresholds are null)")
        uploaded.append(result)

    print("Search")
    search_started = time.monotonic()
    text_to_image = _get(f"{base_url}/search/images", q="carved stone pillars", k=10)
    first_search_seconds = time.monotonic() - search_started
    _check(isinstance(text_to_image, list) and bool(text_to_image), "text-to-image search empty")
    _check_scores(text_to_image, "text-to-image")  # type: ignore[arg-type]
    for row in text_to_image[:3]:  # type: ignore[index]
        print(f"  {row['name']:<22} {row['score']:+.4f}  image {row['image_id']}")
    warm_started = time.monotonic()
    _get(f"{base_url}/search/images", q="carved stone pillars", k=10)
    warm_search_seconds = time.monotonic() - warm_started

    by_image_body, by_image_type = _multipart({}, args.stepwell)
    matches = _request(
        f"{base_url}/search/by-image?k=5",
        by_image_body,
        by_image_type,
        "POST",
    )
    _check(isinstance(matches, list) and bool(matches), "image-to-image search empty")
    _check_scores(matches, "image-to-image")  # type: ignore[arg-type]
    for match in matches:  # type: ignore[attr-defined]
        _check(
            match["image_id"] != uploaded[0]["image_id"],
            "image-to-image search returned the query image",
        )
    print(f"  by-image top match image {matches[0]['image_id']} {matches[0]['score']:+.4f}")  # type: ignore[index]

    text = _get(f"{base_url}/search/text", q="carved stone pillars", k=5)
    _check(isinstance(text, list) and bool(text), "text search empty")
    _check_scores(text, "text search")  # type: ignore[arg-type]
    print(f"  text search top site {text[0]['name']} {text[0]['score']:+.4f}")  # type: ignore[index]

    print("Review")
    _check_review(base_url, uploaded)

    print("Timings")
    print(f"  first upload queued -> done: {first_upload_seconds:.2f}s")
    print(f"  first /search/images (cold): {first_search_seconds:.2f}s")
    print(f"  second /search/images (warm): {warm_search_seconds:.2f}s")
    print("SMOKE TEST PASSED")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stepwell", type=pathlib.Path, required=True)
    parser.add_argument("--fort", type=pathlib.Path, required=True)
    parser.add_argument("--temple", type=pathlib.Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--author", default="Smoke Test")
    parser.add_argument("--licence", default="Test only, not for publication")
    parser.add_argument("--timeout", type=float, default=600.0, help="seconds to wait per job")
    args = parser.parse_args()

    try:
        _run(args)
    except SmokeFailure as exc:
        print(f"SMOKE TEST FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
