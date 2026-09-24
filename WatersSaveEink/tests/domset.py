# -*- coding: utf-8 -*-
"""抓取设置页测试夹具里的 @@SETBEG@@ .. @@SETEND@@ 诊断块。"""
import subprocess, sys, os, re

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
RD = r"D:\workbuddy\2026-09-23-08-21-00\_render"
MK = "@@" + "SET" + "BEG" + "@@"
EN = "@@" + "SET" + "END" + "@@"


def dump(name, w=1200, h=825, budget=30000):
    page = "file:///D:/workbuddy/2026-09-23-08-21-00/_render/%s.html" % name
    prof = os.path.join(RD, "_prof_" + name)
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--hide-scrollbars", "--force-device-scale-factor=1",
           "--user-data-dir=" + prof,
           "--window-size=%d,%d" % (w, h),
           "--virtual-time-budget=%d" % budget,
           "--dump-dom", page]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=240,
                       encoding="utf-8", errors="replace")
    dom = r.stdout or ""
    print("=" * 72)
    print("### " + name)
    print("=" * 72)
    m = re.search(re.escape(MK) + r"(.*?)" + re.escape(EN), dom, re.S)
    if m:
        text = m.group(1)
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        print(text.strip())
    else:
        print("NO SET DIAG. dom len=%d rc=%d" % (len(dom), r.returncode))
        t = re.search(r"<title>(.*?)</title>", dom, re.S)
        if t:
            print("title:", t.group(1)[:400])
        i = dom.find("__setdiag")
        if i > 0:
            print("...", dom[i - 200:i + 400])


if __name__ == "__main__":
    for nm in (sys.argv[1:] or ["set", "set_legacy"]):
        dump(nm)
