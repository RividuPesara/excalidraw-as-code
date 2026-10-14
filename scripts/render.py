from __future__ import annotations

import argparse
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
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
BROWSER_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "chrome",
                 "firefox"]


def to_svg(src: Path, out: Path) -> None:
    # kroki wants the raw scene as plain text
    req = urllib.request.Request(
        f"{KROKI_URL}/excalidraw/svg",
        data=src.read_bytes(),
        headers={"Content-Type": "text/plain", "User-Agent": "excalidraw-as-code"},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as res:
            out.write_bytes(res.read())
    except urllib.error.HTTPError as err:
        sys.exit(f"kroki said {err.code} {err.read().decode(errors='ignore')[:400]}")


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


def workdir(browser: str) -> Path:
    # snap browsers cannot see /tmp or dot folders so they get their own common folder
    if "/snap/" in browser or Path(browser).resolve().parts[:2] == ("/", "snap"):
        d = Path.home() / "snap" / Path(browser).name / "common" / "excalidraw-as-code"
    else:
        d = Path(tempfile.gettempdir()) / "excalidraw-as-code" / "work"
    d.mkdir(parents=True, exist_ok=True)
    return d


def to_png(svg: Path, out: Path, scale: float) -> bool:
    browser = find_browser()
    if not browser:
        print("no Chrome, Edge, Chromium or Firefox found so set BROWSER_BIN to get a png", file=sys.stderr)
        return False
    head = svg.read_text(encoding="utf-8", errors="ignore")[:2000]
    match = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', head)
    width, height = (math.ceil(float(match.group(1))), math.ceil(float(match.group(2)))) if match else (1600, 1000)
    work = workdir(browser)
    page, shot = work / svg.name, work / out.name
    shutil.copyfile(svg, page)
    shot.unlink(missing_ok=True)
    if "firefox" in Path(browser).name:
        cmd = [browser, "--headless", "--screenshot", str(shot), f"--window-size={width},{height}", page.as_uri()]
    else:
        cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--force-device-scale-factor={scale}",
               f"--window-size={width},{height}", f"--screenshot={shot}", page.as_uri()]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not shot.exists():
        print(f"{Path(browser).name} made no png\n{res.stderr[-800:]}", file=sys.stderr)
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(shot), out)
    page.unlink(missing_ok=True)
    return True


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
