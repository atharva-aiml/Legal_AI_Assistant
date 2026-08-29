"""Render every NN_*.svg in this folder to a 2x PNG via headless Chrome."""
import glob
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

svgs = sorted(f for f in glob.glob(os.path.join(HERE, "*.svg")))
only = sys.argv[1:]
if only:
    svgs = [f for f in svgs if any(o in os.path.basename(f) for o in only)]

for i, svg in enumerate(svgs):
    txt = open(svg, encoding="utf-8").read()
    m = re.search(r'width="(\d+)" height="(\d+)"', txt)
    w, h = int(m.group(1)), int(m.group(2))
    png = svg[:-4] + ".png"
    profile = os.path.join(HERE, f".prof{i}")
    cmd = [
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--no-first-run", "--no-default-browser-check", "--disable-extensions",
        "--force-device-scale-factor=2", "--hide-scrollbars",
        f"--user-data-dir={profile}",
        f"--window-size={w},{h}",
        f"--screenshot={png}",
        svg,
    ]
    ok = False
    for attempt in range(3):
        try:
            subprocess.run(cmd, capture_output=True, timeout=90)
        except subprocess.TimeoutExpired:
            pass
        if os.path.exists(png) and os.path.getsize(png) > 5000:
            ok = True
            break
        time.sleep(2)
    size = os.path.getsize(png) if os.path.exists(png) else 0
    print(f"{'OK ' if ok else 'FAIL'} {os.path.basename(png):48s} {w}x{h}@2x  {size:>9,} bytes")
    # best-effort profile cleanup
    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", profile], capture_output=True)

print("done")
