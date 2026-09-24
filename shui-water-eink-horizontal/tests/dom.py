# -*- coding: utf-8 -*-
"""Headless-render a harness page and extract the @@DIAG@@ geometry dump."""
import subprocess, sys, os, re

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
RD = r"D:\workbuddy\2026-09-23-08-21-00\_render"


def dump(name, w=1230, h=1001, budget=20000):
    page = "file:///D:/workbuddy/2026-09-23-08-21-00/_render/%s.html" % name
    prof = os.path.join(RD, "_prof_" + name)
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--hide-scrollbars", "--force-device-scale-factor=1",
           "--user-data-dir=" + prof,
           "--window-size=%d,%d" % (w, h),
           "--virtual-time-budget=%d" % budget,
           "--dump-dom", page]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=200,
                       encoding="utf-8", errors="replace")
    dom = r.stdout or ""
    m = re.search(r"@@BEGMARK@@(.*?)@@ENDMARK@@", dom, re.S)
    print("=" * 70)
    print("### " + name)
    print("=" * 70)
    if m:
        text = m.group(1)
        # un-escape HTML entities that --dump-dom may emit
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        print(text.strip())
    else:
        print("NO DIAG FOUND. dom len=%d rc=%d" % (len(dom), r.returncode))
        t = re.search(r"<title>(.*?)</title>", dom, re.S)
        if t:
            print("title:", t.group(1)[:300])


if __name__ == "__main__":
    for nm in (sys.argv[1:] or ["orig", "legacy"]):
        dump(nm)
