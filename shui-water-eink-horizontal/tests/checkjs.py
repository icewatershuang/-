# -*- coding: utf-8 -*-
"""把 dashboard.html 里的 <script> 块抽出来，用 node --check 逐个做语法校验"""
import io, os, re, subprocess, tempfile

W = r"D:\workbuddy\2026-09-23-08-21-00"
HTML = os.path.join(W, "apk_extract", "assets", "dashboard.html")
NODE = r"C:\Users\icewa\.workbuddy\binaries\node\versions\22.22.2-3\node.exe"

t = io.open(HTML, encoding="utf-8").read()
blocks = []
for m in re.finditer(r"<script\b([^>]*)>(.*?)</script>", t, re.S):
    attrs, body = m.group(1), m.group(2)
    if "src=" in attrs:
        blocks.append(("external " + attrs.strip(), None))
        continue
    line = t[:m.start()].count("\n") + 1
    blocks.append(("inline @line %d (len %d)" % (line, len(body)), body))

print("script blocks:", len(blocks))
tmp = os.path.join(W, "_syntax_tmp.js")
bad = 0
for i, (name, body) in enumerate(blocks):
    print("-", name)
    if body is None:
        continue
    io.open(tmp, "w", encoding="utf-8").write(body)
    r = subprocess.run([NODE, "--check", tmp], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        bad += 1
        print("   !! SYNTAX FAIL")
        print((r.stdout or "") + (r.stderr or ""))
    else:
        print("   OK")
try:
    os.remove(tmp)
except Exception:
    pass
print("FAILED BLOCKS:", bad)
