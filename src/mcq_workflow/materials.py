from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable, List, Tuple


Material = Tuple[str, bytes]


def extract_course_material(files: Iterable[Material], max_chars: int = 80000) -> str:
    """Extract a bounded amount of text from PDF, text, and Markdown files."""
    parts: List[str] = []
    used_chars = 0

    for filename, content in files:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            text = _extract_pdf(content, filename)
        elif suffix in {".txt", ".md"}:
            text = content.decode("utf-8", errors="replace")
        else:
            raise ValueError(
                f"unsupported course material '{filename}'; use PDF, TXT, or MD"
            )

        remaining = max_chars - used_chars
        if remaining <= 0:
            break
        excerpt = text[:remaining].strip()
        if excerpt:
            parts.append(f"--- {filename} ---\n{excerpt}")
            used_chars += len(excerpt)

    if not parts:
        raise ValueError("no readable text was found in the supplied course material")
    return "\n\n".join(parts)


def load_material_paths(paths: Iterable[str]) -> List[Material]:
    return [(path, Path(path).read_bytes()) for path in paths]


def _extract_pdf(content: bytes, filename: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF support requires the 'pypdf' package") from exc

    try:
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ValueError(f"could not read PDF '{filename}': {exc}") from exc

