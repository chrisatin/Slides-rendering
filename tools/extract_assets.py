#!/usr/bin/env python3
"""Extract raw images and videos from reference presentations.

Usage:
    python3 tools/extract_assets.py [SOURCE_DIR] [--out DIR] [--min-size PX] [--recursive]

SOURCE_DIR defaults to $EXAMPLE_PRESENTATIONS_PATH. Output goes to
assets/extracted_resources/<deck>/{images,videos}/ plus a manifest.json that
records the slide or page each file came from.

Supported: .pptx/.ppsx/.potx (ZIP, ppt/media), .odp/.key (ZIP), .pdf (PyMuPDF if
installed, otherwise poppler's pdfimages). No third-party packages are required.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp",
             ".svg", ".emf", ".wmf", ".jp2", ".jpx", ".ppm", ".pbm", ".pgm", ".jb2e", ".ccitt"}
VIDEO_EXT = {".mp4", ".m4v", ".mov", ".avi", ".wmv", ".webm", ".mkv", ".mpg", ".mpeg", ".gif_video"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".wma", ".aac", ".ogg"}
OOXML_EXT = {".pptx", ".ppsx", ".potx", ".pptm"}
OTHER_ZIP_EXT = {".odp", ".key"}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = PROJECT_ROOT / "assets" / "extracted_resources"


def slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()
    return slug or "deck"


def kind_of(ext: str) -> str | None:
    ext = ext.lower()
    if ext in VIDEO_EXT:
        return "videos"
    if ext in IMAGE_EXT:
        return "images"
    if ext in AUDIO_EXT:
        return "audio"
    return None


class DeckWriter:
    """Writes files for one deck, deduplicating identical bytes by SHA-256."""

    def __init__(self, out_dir: Path, source: Path):
        self.out_dir = out_dir
        self.source = source
        self.by_hash: dict[str, dict] = {}
        self.external_links: list[dict] = []

    def add(self, data: bytes, name: str, locations: list[str], width=None, height=None):
        ext = Path(name).suffix.lower()
        kind = kind_of(ext)
        if kind is None:
            return
        digest = hashlib.sha256(data).hexdigest()
        if digest in self.by_hash:
            found_in = self.by_hash[digest]["found_in"]
            found_in.extend(loc for loc in locations if loc not in found_in)
            return
        target_dir = self.out_dir / kind
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{Path(name).stem}{ext}"
        if target.exists():
            target = target_dir / f"{Path(name).stem}_{digest[:8]}{ext}"
        target.write_bytes(data)
        self.by_hash[digest] = {
            "file": str(target.relative_to(self.out_dir)),
            "kind": kind,
            "bytes": len(data),
            "width": width,
            "height": height,
            "found_in": list(locations),
        }

    def write_manifest(self, method: str):
        entries = sorted(self.by_hash.values(), key=lambda e: e["file"])
        manifest = {"source": self.source.name, "method": method, "count": len(entries), "files": entries,
                    "external_links": self.external_links}
        (self.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        return entries


def slide_media_map(zf: zipfile.ZipFile, writer: DeckWriter) -> dict[str, list[str]]:
    """Map ppt/media/* paths to the slides that reference them, via slide .rels files.

    External targets (e.g. Drive links to videos) can't be downloaded, so they go to the manifest.
    """
    usage: dict[str, list[str]] = {}
    rel_re = re.compile(r'Target="([^"]+)"')
    for info in zf.infolist():
        m = re.match(r"ppt/slides/_rels/slide(\d+)\.xml\.rels$", info.filename)
        if not m:
            continue
        slide = f"slide {int(m.group(1))}"
        xml = zf.read(info).decode("utf-8", errors="replace")
        for target in rel_re.findall(xml):
            if target.startswith(("http:", "https:")):
                writer.external_links.append({"slide": slide, "url": target})
                continue
            resolved = str(PurePosixPath(os.path.normpath(f"ppt/slides/{target}")))
            usage.setdefault(resolved, []).append(slide)
    for slides in usage.values():
        slides.sort(key=lambda s: int(s.split()[1]))
    return usage


def extract_zip_deck(path: Path, writer: DeckWriter) -> str:
    with zipfile.ZipFile(path) as zf:
        usage = slide_media_map(zf, writer) if path.suffix.lower() in OOXML_EXT else {}
        for info in zf.infolist():
            if info.is_dir():
                continue
            lower = info.filename.lower()
            # OOXML keeps media under ppt/media; ODP under Pictures/; Keynote under Data/.
            if not lower.startswith(("ppt/media/", "pictures/", "data/", "media/")):
                continue
            writer.add(zf.read(info), Path(info.filename).name, usage.get(info.filename, []))
    return "zip"


def extract_pdf_pymupdf(path: Path, writer: DeckWriter, min_size: int) -> str:
    import fitz  # PyMuPDF

    doc = fitz.open(path)
    for page_index, page in enumerate(doc, start=1):
        for img in page.get_images(full=True):
            xref, smask = img[0], img[1]
            info = doc.extract_image(xref)
            if not info or min(info["width"], info["height"]) < min_size:
                continue
            data, ext = info["image"], info["ext"]
            if smask:
                # Recombine with the alpha mask so transparent PNGs keep their alpha.
                pix = fitz.Pixmap(fitz.Pixmap(doc, xref), fitz.Pixmap(doc, smask))
                data, ext = pix.tobytes("png"), "png"
            writer.add(data, f"p{page_index:03d}_x{xref}.{ext}", [f"page {page_index}"],
                       info["width"], info["height"])
    return "pymupdf"


def extract_pdf_pdfimages(path: Path, writer: DeckWriter, min_size: int, tmp_root: Path) -> str:
    listing = subprocess.run(["pdfimages", "-list", str(path)], capture_output=True, text=True, check=True)
    # Columns: page num type width height color comp bpc enc interp object ID ...
    keep: dict[int, tuple[int, int, int]] = {}
    for line in listing.stdout.splitlines()[2:]:
        cols = line.split()
        if len(cols) < 5 or not cols[1].isdigit():
            continue
        page, num, kind, w, h = int(cols[0]), int(cols[1]), cols[2], int(cols[3]), int(cols[4])
        if kind == "image" and min(w, h) >= min_size:
            keep[num] = (page, w, h)

    tmp = tmp_root / slugify(path.stem)
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["pdfimages", "-all", str(path), str(tmp / "img")], check=True, stderr=subprocess.DEVNULL)
        for f in sorted(tmp.iterdir()):
            m = re.match(r"img-(\d+)\.", f.name)
            if not m or int(m.group(1)) not in keep:
                continue
            page, w, h = keep[int(m.group(1))]
            writer.add(f.read_bytes(), f"p{page:03d}_{m.group(1)}{f.suffix}", [f"page {page}"], w, h)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return "pdfimages"


def extract_pdf(path: Path, writer: DeckWriter, min_size: int, tmp_root: Path) -> str:
    try:
        import fitz  # noqa: F401
        return extract_pdf_pymupdf(path, writer, min_size)
    except ImportError:
        pass
    if shutil.which("pdfimages"):
        return extract_pdf_pdfimages(path, writer, min_size, tmp_root)
    raise RuntimeError("PDF support needs PyMuPDF (pip install pymupdf) or poppler's pdfimages")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", nargs="?", default=os.environ.get("EXAMPLE_PRESENTATIONS_PATH"),
                        help="folder with presentations (default: $EXAMPLE_PRESENTATIONS_PATH)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output folder (default: {DEFAULT_OUT})")
    parser.add_argument("--min-size", type=int, default=64,
                        help="skip PDF images whose shorter side is below this many pixels (default: 64)")
    parser.add_argument("--recursive", action="store_true", help="search subfolders too")
    parser.add_argument("--clean", action="store_true", help="delete each deck's previous output first")
    args = parser.parse_args()

    if not args.source:
        parser.error("pass SOURCE_DIR or set EXAMPLE_PRESENTATIONS_PATH")
    source = Path(args.source).expanduser().resolve()
    if not source.is_dir():
        parser.error(f"not a directory: {source}")

    supported = OOXML_EXT | OTHER_ZIP_EXT | {".pdf"}
    pattern = "**/*" if args.recursive else "*"
    out_root = args.out.resolve()
    decks = sorted(p for p in source.glob(pattern)
                   if p.is_file() and p.suffix.lower() in supported and out_root not in p.parents)
    if not decks:
        print(f"No presentations found in {source}", file=sys.stderr)
        return 1

    out_root.mkdir(parents=True, exist_ok=True)
    tmp_root = out_root / ".tmp"
    summary = []
    failures = 0
    for deck in decks:
        deck_dir = out_root / slugify(deck.stem)
        if args.clean and deck_dir.exists():
            shutil.rmtree(deck_dir)
        deck_dir.mkdir(parents=True, exist_ok=True)
        writer = DeckWriter(deck_dir, deck)
        try:
            if deck.suffix.lower() == ".pdf":
                method = extract_pdf(deck, writer, args.min_size, tmp_root)
            else:
                method = extract_zip_deck(deck, writer)
        except (zipfile.BadZipFile, subprocess.CalledProcessError, RuntimeError) as exc:
            print(f"FAILED  {deck.name}: {exc}", file=sys.stderr)
            failures += 1
            continue
        entries = writer.write_manifest(method)
        counts = {k: sum(e["kind"] == k for e in entries) for k in ("images", "videos", "audio")}
        summary.append({"deck": deck.name, "folder": deck_dir.name, **counts})
        print(f"{deck.name}: {counts['images']} images, {counts['videos']} videos, "
              f"{counts['audio']} audio -> {deck_dir.relative_to(out_root.parent)}")
        for link in writer.external_links:
            print(f"    external link on {link['slide']} (not downloaded): {link['url']}")

    shutil.rmtree(tmp_root, ignore_errors=True)
    (out_root / "index.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
