from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

KROKI_URL = os.environ.get("KROKI_URL", "https://kroki.io").rstrip("/")

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
BROWSER_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "chrome"]


def to_svg(src: Path, out: Path) -> None:
    # kroki wants the raw scene as plain text
    req = urllib.request.Request(
        f"{KROKI_URL}/excalidraw/svg",
        data=src.read_bytes(),
        headers={"Content-Type": "text/plain", "User-Agent": "excalidraw-as-code"},
    )
    with urllib.request.urlopen(req, timeout=90) as res:
        out.write_bytes(res.read())


def find_browser() -> str | None:
    if os.environ.get("BROWSER_BIN"):
        return os.environ["BROWSER_BIN"]
    for candidate in BROWSERS:
        if Path(candidate).exists():
            return candidate
    for name in BROWSER_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def to_png(svg: Path, out: Path, scale: float) -> bool:
    browser = find_browser()
    if not browser:
        print("no Chrome or Edge or Chromium found so set BROWSER_BIN to get a png", file=sys.stderr)
        return False
    head = svg.read_text(encoding="utf-8", errors="ignore")[:2000]
    match = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', head)
    width, height = (int(float(match.group(1))), int(float(match.group(2)))) if match else (1600, 1000)
    # screenshot the svg at its own size
    subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--force-device-scale-factor={scale}",
         f"--window-size={width},{height}", f"--screenshot={out.resolve()}", svg.resolve().as_uri()],
        check=True, capture_output=True, timeout=120,
    )
    return out.exists()


def main() -> None:
    parser = argparse.ArgumentParser(description="Render an .excalidraw file to svg with a png preview for review")
    parser.add_argument("input", type=Path)
    parser.add_argument("--out-dir", type=Path, help="defaults to the input folder")
    parser.add_argument("--png", action="store_true", help="also save a png next to the svg")
    parser.add_argument("--no-preview", action="store_true", help="skip the temporary review png")
    parser.add_argument("--scale", type=float, default=1, help="png pixel ratio")
    args = parser.parse_args()

    out_dir = args.out_dir or args.input.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    svg = out_dir / f"{args.input.stem}.svg"
    to_svg(args.input, svg)
    print(f"wrote {svg}")
    if args.png:
        png = out_dir / f"{args.input.stem}.png"
        if to_png(svg, png, args.scale):
            print(f"wrote {png}")
    elif not args.no_preview:
        # review copy lives in temp and is overwritten on every run
        preview_dir = Path(tempfile.gettempdir()) / "excalidraw-as-code"
        preview_dir.mkdir(exist_ok=True)
        preview = preview_dir / f"{args.input.stem}.png"
        if to_png(svg, preview, args.scale):
            print(f"preview {preview}")


if __name__ == "__main__":
    main()
