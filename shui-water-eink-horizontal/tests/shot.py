# -*- coding: utf-8 -*-
"""Headless-render a harness page and save a PNG (uses Edge via subprocess)."""
import subprocess, sys, os

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
RD = r"D:\workbuddy\2026-09-23-08-21-00\_render"

def shot(name, w=1200, h=825, budget=20000):
    page = "file:///D:/workbuddy/2026-09-23-08-21-00/_render/%s.html" % name
    png = os.path.join(RD, name + ".png")
    if os.path.exists(png):
        os.remove(png)
    prof = os.path.join(RD, "_prof_" + name)
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--hide-scrollbars", "--force-device-scale-factor=1",
           "--user-data-dir=" + prof,
           "--window-size=%d,%d" % (w, h),
           "--virtual-time-budget=%d" % budget,
           "--screenshot=" + png, page]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    ok = os.path.exists(png)
    print("%-10s rc=%d png=%s size=%s" % (name, r.returncode, ok,
          os.path.getsize(png) if ok else "-"))
    err = (r.stderr or "").strip()
    if err:
        print("   stderr:", err[:400].replace("\n", " | "))
    return ok

if __name__ == "__main__":
    names = sys.argv[1:] or ["orig", "legacy"]
    for nm in names:
        shot(nm)
