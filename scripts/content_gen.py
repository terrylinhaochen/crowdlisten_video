#!/usr/bin/env python3
"""Content repurposing pipeline CLI.

Downloads a source URL or loads a local file, extracts text + images,
stores artifacts under content_gen/, and prepares per-platform outputs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import hashlib
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parents[1]
CONTENT_GEN_DIR = BASE_DIR / "content_gen"
SOURCES_DIR = CONTENT_GEN_DIR / "sources"
PROCESSING_DIR = CONTENT_GEN_DIR / "processing"

DEFAULT_PLATFORMS = ["blog", "linkedin", "newsletter", "thread"]

EVERY_STYLE_PROMPT = """You are writing in the Every house style.

Requirements:
- Clear thesis in the first 2-3 sentences.
- Plainspoken, human voice. No jargon without a short explanation.
- Concrete examples and specific nouns.
- Short, varied sentences. Avoid robotic cadence.
- Avoid marketing fluff, formulaic transitions, and vague "this/that".
- Minimize hedging (e.g., "might", "could", "perhaps") unless needed.

Deliverable:
- A draft tailored to the target platform.
- Use the source text as the only factual basis.
"""

AI_TELLS_CHECKLIST = [
    "No vague this/that without a noun",
    "No marketing fluff or empty superlatives",
    "No formulaic transitions (e.g., 'In conclusion', 'Additionally')",
    "Limited hedging unless uncertainty is real",
    "Avoid robotic or symmetrical sentence patterns",
    "Prefer concrete examples over abstractions",
]


@dataclass
class SourceResult:
    slug: str
    source_path: Path
    extracted_text_path: Path
    images_dir: Path
    image_files: list[Path]
    image_png_copies: list[Path]
    source_url: str | None
    source_title: str | None


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_stack: list[str] = []
        self.images: list[str] = []
        self.title: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag in {"script", "style", "noscript"}:
            self._skip_stack.append(tag)
            return
        if tag == "img":
            src = None
            for k, v in attrs:
                if k == "src":
                    src = v
                    break
            if src:
                self.images.append(src)

    def handle_endtag(self, tag: str):
        if self._skip_stack and self._skip_stack[-1] == tag:
            self._skip_stack.pop()

    def handle_data(self, data: str):
        if self._skip_stack:
            return
        text = data.strip()
        if not text:
            return
        if self.lasttag == "title" and self.title is None:
            self.title = text
        self._chunks.append(text)

    def get_text(self) -> str:
        return "\n".join(self._chunks)


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "source"


def _safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _read_local(path: Path) -> tuple[bytes, str | None]:
    data = path.read_bytes()
    ext = path.suffix.lower()
    content_type = None
    if ext in {".html", ".htm"}:
        content_type = "text/html"
    elif ext in {".md", ".markdown"}:
        content_type = "text/markdown"
    return data, content_type


def _fetch_url(url: str) -> tuple[bytes, str | None]:
    req = Request(url, headers={"User-Agent": "content-gen/1.0"})
    with urlopen(req) as resp:
        data = resp.read()
        content_type = resp.headers.get("Content-Type")
    return data, content_type


def _looks_like_html(text: str) -> bool:
    if "<html" in text.lower() or "<body" in text.lower():
        return True
    return bool(re.search(r"<\s*\w+[^>]*>", text))


def _strip_markdown(md_text: str) -> str:
    text = md_text
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"!\[[^\]]*\]\(([^)]+)\)", "", text)
    text = re.sub(r"\[[^\]]+\]\(([^)]+)\)", "", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_~]+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_from_html(html_text: str) -> tuple[str, list[str], str | None]:
    parser = _HTMLTextExtractor()
    parser.feed(html_text)
    return parser.get_text(), parser.images, parser.title


def _extract_from_markdown(md_text: str) -> tuple[str, list[str]]:
    image_urls = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md_text)
    text = _strip_markdown(md_text)
    return text, image_urls


def _normalize_image_urls(urls: Iterable[str], base_url: str | None, local_dir: Path | None) -> list[str]:
    cleaned: list[str] = []
    for u in urls:
        u = u.strip().strip('"').strip("'")
        if not u:
            continue
        if base_url and not urlparse(u).scheme:
            u = urljoin(base_url, u)
        elif local_dir and not urlparse(u).scheme:
            u = str((local_dir / u).resolve())
        cleaned.append(u)
    return cleaned


def _infer_ext(url: str, content_type: str | None) -> str:
    path = urlparse(url).path
    ext = Path(path).suffix.lower()
    if ext:
        return ext
    if content_type:
        if "png" in content_type:
            return ".png"
        if "jpeg" in content_type or "jpg" in content_type:
            return ".jpg"
        if "gif" in content_type:
            return ".gif"
        if "webp" in content_type:
            return ".webp"
    return ".bin"


def _download_image(url: str, dest_dir: Path, index: int) -> tuple[Path | None, Path | None]:
    parsed = urlparse(url)
    is_local = parsed.scheme in {"", "file"}

    if is_local:
        local_path = Path(parsed.path)
        if not local_path.exists():
            return None, None
        ext = local_path.suffix.lower() or ".bin"
        dest_path = dest_dir / f"image_{index:03d}{ext}"
        shutil.copyfile(local_path, dest_path)
        png_copy = _make_png_copy(dest_path)
        return dest_path, png_copy

    req = Request(url, headers={"User-Agent": "content-gen/1.0"})
    with urlopen(req) as resp:
        content_type = resp.headers.get("Content-Type")
        data = resp.read()
    ext = _infer_ext(url, content_type)
    dest_path = dest_dir / f"image_{index:03d}{ext}"
    dest_path.write_bytes(data)
    png_copy = _make_png_copy(dest_path)
    return dest_path, png_copy


def _make_png_copy(path: Path) -> Path | None:
    if path.suffix.lower() == ".png":
        return path
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None
    try:
        with Image.open(path) as img:
            png_path = path.with_suffix(".png")
            img.save(png_path, format="PNG")
            return png_path
    except Exception:
        return None


def _write_prompt_files(
    output_dir: Path,
    platform: str,
    extracted_text: str,
    source_title: str | None,
    source_url: str | None,
) -> None:
    prompt_path = output_dir / "prompt.txt"
    draft_path = output_dir / "draft.md"

    prompt = [
        EVERY_STYLE_PROMPT.strip(),
        "",
        f"Platform: {platform}",
        f"Source title: {source_title or 'Untitled'}",
        f"Source url: {source_url or 'local file'}",
        "",
        "Source text:",
        extracted_text.strip(),
        "",
        "AI-tells checklist:",
    ]
    prompt.extend([f"- {item}" for item in AI_TELLS_CHECKLIST])
    prompt_path.write_text("\n".join(prompt).strip() + "\n", encoding="utf-8")

    draft = [
        f"# Draft for {platform}",
        "",
        "## Thesis",
        "",
        "## Outline",
        "- Hook",
        "- Core argument",
        "- Example",
        "- Close",
        "",
        "## Draft",
        "",
        "",
        "## QA Checklist",
    ]
    draft.extend([f"- [ ] {item}" for item in AI_TELLS_CHECKLIST])
    draft_path.write_text("\n".join(draft).strip() + "\n", encoding="utf-8")


def run_content_gen(
    *,
    url: str | None,
    input_path: str | None,
    platforms: list[str],
    style: str,
    version: str | None,
) -> dict:
    if bool(url) == bool(input_path):
        raise ValueError("Provide exactly one of --url or --input")
    if style.lower() != "every":
        raise ValueError("Only style 'every' is supported for now")

    if url:
        raw, content_type = _fetch_url(url)
        raw_text = raw.decode("utf-8", errors="replace")
        slug = _slugify(urlparse(url).netloc + urlparse(url).path)
        source_url = url
        local_dir = None
    else:
        input_file = Path(input_path).expanduser().resolve()
        raw, content_type = _read_local(input_file)
        raw_text = raw.decode("utf-8", errors="replace")
        slug = _slugify(input_file.stem)
        source_url = None
        local_dir = input_file.parent

    if version is None:
        version = datetime.now(timezone.utc).strftime("v%Y%m%d_%H%M%S")

    source_dir = SOURCES_DIR / slug
    images_dir = source_dir / "images"
    processing_dir = PROCESSING_DIR / slug

    _safe_mkdir(images_dir)
    _safe_mkdir(processing_dir)

    is_html = (content_type and "html" in content_type) or _looks_like_html(raw_text)
    source_ext = ".html" if is_html else ".md"
    source_path = source_dir / f"source{source_ext}"
    source_path.write_text(raw_text, encoding="utf-8")

    if is_html:
        extracted_text, image_urls, title = _extract_from_html(raw_text)
    else:
        extracted_text, image_urls = _extract_from_markdown(raw_text)
        title = None

    image_urls = _normalize_image_urls(image_urls, source_url, local_dir)

    image_files: list[Path] = []
    png_copies: list[Path] = []
    for idx, img_url in enumerate(image_urls, start=1):
        try:
            downloaded, png_copy = _download_image(img_url, images_dir, idx)
        except Exception:
            continue
        if downloaded:
            image_files.append(downloaded)
        if png_copy:
            png_copies.append(png_copy)

    extracted_text = extracted_text.strip()
    extracted_path = processing_dir / "extracted.txt"
    extracted_path.write_text(extracted_text + "\n", encoding="utf-8")

    manifest = {
        "slug": slug,
        "version": version,
        "style": style,
        "source_url": source_url,
        "source_title": title,
        "source_file": str(source_path),
        "extracted_text_file": str(extracted_path),
        "image_count": len(image_files),
        "image_files": [str(p) for p in image_files],
        "png_copies": [str(p) for p in png_copies],
        "platforms": platforms,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = processing_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    for platform in platforms:
        output_dir = CONTENT_GEN_DIR / slug / version / platform
        _safe_mkdir(output_dir)
        _write_prompt_files(output_dir, platform, extracted_text, title, source_url)

    return {
        "ok": True,
        "slug": slug,
        "version": version,
        "platforms": platforms,
        "source_path": str(source_path),
        "processing_manifest": str(manifest_path),
        "output_root": str(CONTENT_GEN_DIR / slug / version),
    }


def run_from_payload(payload: dict) -> dict:
    return run_content_gen(
        url=payload.get("url"),
        input_path=payload.get("input"),
        platforms=_parse_platforms(payload.get("platforms")),
        style=payload.get("style", "every"),
        version=payload.get("version"),
    )


def _parse_platforms(value: str | list[str] | None) -> list[str]:
    if value is None:
        return DEFAULT_PLATFORMS
    if isinstance(value, list):
        return [v.strip() for v in value if v.strip()]
    return [v.strip() for v in value.split(",") if v.strip()]


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Content repurposing pipeline")
    parser.add_argument("--url", help="Source URL (HTML or Markdown)")
    parser.add_argument("--input", help="Local file path (HTML or Markdown)")
    parser.add_argument(
        "--platforms",
        default=",".join(DEFAULT_PLATFORMS),
        help="Comma-separated list of platforms",
    )
    parser.add_argument("--style", default="every", help="Style preset (every)")
    parser.add_argument("--version", default=None, help="Version label (e.g., v1)")
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    try:
        result = run_content_gen(
            url=args.url,
            input_path=args.input,
            platforms=_parse_platforms(args.platforms),
            style=args.style,
            version=args.version,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
