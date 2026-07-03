#!/usr/bin/env python3
"""Assemble les frames PNG de record-demo.mjs en GIF anime.

Usage:
    python scripts/make_gif.py <dossier-frames> <sortie.gif> [largeur=960]
"""
import json
import sys
from pathlib import Path

from PIL import Image


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    frames_dir = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 960

    manifest = json.loads((frames_dir / "manifest.json").read_text(encoding="utf-8"))

    images = []
    durations = []
    for entry in manifest:
        img = Image.open(frames_dir / entry["name"]).convert("RGB")
        ratio = width / img.width
        img = img.resize((width, int(img.height * ratio)), Image.LANCZOS)
        images.append(img.quantize(colors=256, method=Image.MEDIANCUT))
        durations.append(entry["duration"])

    images[0].save(
        out_path,
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    total_s = sum(durations) / 1000
    size_kb = out_path.stat().st_size // 1024
    print(f"{out_path} : {len(images)} frames, {total_s:.1f}s, {size_kb} Ko")


if __name__ == "__main__":
    main()
