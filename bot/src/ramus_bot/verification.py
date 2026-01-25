from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from typing import Iterable

import httpx
import imagehash
from PIL import Image

URL_PATTERN = re.compile(r"https?://[^\s]+")


@dataclass(frozen=True)
class ImageMetadata:
    url: str
    width: int
    height: int
    format: str
    phash: str


@dataclass(frozen=True)
class ProofCheck:
    urls: list[str]
    images: list[ImageMetadata]
    videos: list[str]
    errors: list[str]

    @property
    def is_valid(self) -> bool:
        return bool(self.images or self.videos) and not self.errors


def extract_urls(text: str) -> list[str]:
    return URL_PATTERN.findall(text)


def is_image_url(url: str) -> bool:
    return url.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".heic"))


def is_video_url(url: str) -> bool:
    return url.lower().endswith((".mp4", ".mov", ".webm"))


def analyze_proof(text: str, timeout_seconds: int = 10) -> ProofCheck:
    urls = extract_urls(text)
    images: list[ImageMetadata] = []
    videos: list[str] = []
    errors: list[str] = []

    for url in urls:
        try:
            if is_video_url(url):
                videos.append(url)
                continue
            if not is_image_url(url):
                continue
            image_bytes = _download(url, timeout_seconds)
            metadata = _analyze_image(url, image_bytes)
            images.append(metadata)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url}: {exc}")

    if not images and not videos:
        errors.append("No recognizable image/video URLs found.")

    return ProofCheck(urls=urls, images=images, videos=videos, errors=errors)


def _download(url: str, timeout_seconds: int) -> bytes:
    response = httpx.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    return response.content


def _analyze_image(url: str, payload: bytes) -> ImageMetadata:
    with Image.open(BytesIO(payload)) as image:
        width, height = image.size
        fmt = image.format or "unknown"
        phash = str(imagehash.phash(image))

    return ImageMetadata(url=url, width=width, height=height, format=fmt, phash=phash)


def dedupe_by_phash(images: Iterable[ImageMetadata]) -> list[ImageMetadata]:
    seen: set[str] = set()
    deduped: list[ImageMetadata] = []
    for image in images:
        if image.phash in seen:
            continue
        seen.add(image.phash)
        deduped.append(image)
    return deduped
