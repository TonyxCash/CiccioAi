"""Create safe, downloadable Markdown work products for each completed Ciccio task."""
from datetime import datetime, timezone
from pathlib import Path
import os
import re
import unicodedata


def save_deliverable_artifact(title, content, output_dir=None):
    """Write a UTF-8 Markdown artifact with a sanitized, collision-resistant filename."""
    title = str(title or "deliverable").strip()
    content = str(content or "").strip()
    if not content:
        raise ValueError("Cannot save an empty Ciccio deliverable")
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()[:64] or "deliverable"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = Path(output_dir or os.getenv("CICCIO_OUTPUT_DIR", "ciccio_output"))
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stamp}-{slug}.md"
    path.write_text(f"# {title}\n\nCreato da Ciccio — {datetime.now(timezone.utc).isoformat()}\n\n{content}\n", encoding="utf-8")
    if not path.is_file() or path.stat().st_size <= len(content.encode("utf-8")):
        raise OSError("Ciccio artifact write could not be verified")
    return path
