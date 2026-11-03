"""Small, dependency-free clients for Wikimedia Commons and Wikipedia.

Both APIs ask for a descriptive User-Agent. We also throttle requests and retry
transient failures so a dataset run is reproducible without hammering the servers.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "HeritageAtlas/0.1 (hackathon dataset; https://github.com/heritage-atlas)"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
IMAGE_MIME = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
SKIP_TITLE_PARTS = ("stereoscopic", "images by", "sculptures in", "interior of")


class ApiError(RuntimeError):
    """The remote API did not return usable data after retries."""


def _get(url: str, params: dict[str, Any], retries: int = 3) -> dict[str, Any]:
    query = urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
    request = urllib.request.Request(f"{url}?{query}", headers={"User-Agent": USER_AGENT})  # noqa: S310 - fixed https API host
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - https only
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == retries:
                raise ApiError(f"request failed after {retries} attempts: {exc}") from exc
            time.sleep(2**attempt)
    raise ApiError("unreachable")


def _download(url: str, destination: Path, retries: int = 3) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310 - https only
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310 - https only
                data = response.read()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            return len(data)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == retries:
                raise ApiError(f"download failed after {retries} attempts: {exc}") from exc
            time.sleep(2**attempt)
    raise ApiError("unreachable")


def search_categories(site_name: str, limit: int = 8) -> list[str]:
    data = _get(
        COMMONS_API,
        {
            "action": "query",
            "list": "search",
            "srsearch": site_name,
            "srnamespace": "14",
            "srlimit": limit,
        },
    )
    return [item["title"] for item in data.get("query", {}).get("search", [])]


def resolve_category(site: dict[str, Any]) -> str | None:
    if site.get("commons_category"):
        return str(site["commons_category"])
    for title in search_categories(str(site["name"])):
        lowered = title.lower()
        if any(part in lowered for part in SKIP_TITLE_PARTS):
            continue
        return title
    return None


def category_files(category: str, limit: int) -> list[str]:
    data = _get(
        COMMONS_API,
        {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": "file",
            "cmlimit": min(max(limit, 1), 500),
        },
    )
    return [item["title"] for item in data.get("query", {}).get("categorymembers", [])]


def search_files(query: str, limit: int) -> list[str]:
    data = _get(
        COMMONS_API,
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srnamespace": "6",
            "srlimit": min(max(limit, 1), 50),
        },
    )
    return [item["title"] for item in data.get("query", {}).get("search", [])]


def image_info(titles: list[str], thumb_width: int = 1600) -> list[dict[str, Any]]:
    """Return imageinfo blocks for up to 50 file titles."""
    if not titles:
        return []
    data = _get(
        COMMONS_API,
        {
            "action": "query",
            "titles": "|".join(titles),
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata|sha1",
            "iiurlwidth": thumb_width,
        },
    )
    pages = data.get("query", {}).get("pages", [])
    results: list[dict[str, Any]] = []
    for page in pages:
        if page.get("imageinfo"):
            info = dict(page["imageinfo"][0])
            info["title"] = page.get("title", "")
            results.append(info)
    return results


def file_candidates(site: dict[str, Any], per_site: int) -> list[str]:
    category = resolve_category(site)
    titles = category_files(category, per_site * 4) if category else []
    if len(titles) < per_site:
        titles += search_files(f"{site['name']} {site.get('region', '')}", per_site * 3)
    seen: set[str] = set()
    unique: list[str] = []
    for title in titles:
        if title in seen or not title.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        seen.add(title)
        unique.append(title)
    return unique[: max(per_site * 4, per_site)]


def download_file(info: dict[str, Any], destination_dir: Path) -> tuple[Path, int]:
    url = info.get("thumburl") or info["url"]
    extension = IMAGE_MIME.get(
        str(info.get("mime", "")), Path(urllib.parse.urlparse(url).path).suffix
    )
    filename = str(info.get("sha1", "image"))[:16] + extension
    destination = destination_dir / filename
    if destination.exists():
        return destination, destination.stat().st_size
    size = _download(url, destination)
    return destination, size


def wikipedia_page(title: str) -> dict[str, Any]:
    data = _get(
        WIKIPEDIA_API,
        {
            "action": "query",
            "titles": title,
            "prop": "extracts|coordinates",
            "explaintext": "1",
            "exintro": "1",
            "redirects": "1",
        },
    )
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return {}
    page = pages[0]
    coordinates = page.get("coordinates") or []
    return {
        "title": page.get("title", title),
        "description": (page.get("extract") or "").strip(),
        "lat": coordinates[0].get("lat") if coordinates else None,
        "lon": coordinates[0].get("lon") if coordinates else None,
    }
