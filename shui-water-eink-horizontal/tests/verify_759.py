# -*- coding: utf-8 -*-
"""独立复检 KDashBoardL_V3.2_759*.apk：ZIP 结构 / AXML 版本 / 包内 dashboard.html 指纹 / zipalign / apksigner"""
import io, os, sys, struct, zipfile, hashlib, subprocess, json

W = r"D:\workbuddy\2026-09-23-08-21-00"
SRC_HTML = os.path.join(W, "apk_extract", "assets", "dashboard.html")
APKS = [
    os.path.join(W, "KDashBoardL_V3.3_760.apk"),
    os.path.join(W, "KDashBoardL_V3.3_760_v123.apk"),
]
if len(sys.argv) > 1:
    APKS = [p if os.path.isabs(p) else os.path.join(W, p) for p in sys.argv[1:]]
JAVA = r"C:\Program Files\HONOR\HNPCAIService\jdk\bin\java.exe"
ZIPALIGN = r"C:\Users\icewa\android-sdk\build-tools\34.0.0\zipalign.exe"
APKSIGNER = r"C:\Users\icewa\android-sdk\build-tools\34.0.0\lib\apksigner.jar"

out = []
def log(s=""):
    out.append(str(s))

# ---------- AXML 极简解析（取字符串池 + 顶层 manifest 属性） ----------
def parse_strings(buf):
    # 顶层是 XML chunk (0x0003)，其第一个子 chunk 是字符串池 (0x0001)
    typ0, hsz0, sz0 = struct.unpack_from("<HHI", buf, 0)
    assert typ0 == 0x0003, hex(typ0)
    off = hsz0
    typ, hsz, sz = struct.unpack_from("<HHI", buf, off)
    assert typ == 0x0001, hex(typ)
    scount, styleCount, flags, sStart, stStart = struct.unpack_from("<IIIII", buf, off + 8)
    utf8 = bool(flags & 0x100)
    idx = [struct.unpack_from("<I", buf, off + 28 + 4 * i)[0] for i in range(scount)]
    raw = buf[off + sStart:]
    strs = []
    for i in range(scount):
        p = idx[i]
        if utf8:
            n = raw[p]
            if n & 0x80:
                n = ((n & 0x7F) << 8) | raw[p + 1]
                p += 1
            # utf8: len(1-2B) + len bytes + NUL(1B)
            strs.append(raw[p + 1: p + 1 + n].decode("utf-8", "replace"))
        else:
            n = struct.unpack_from("<H", raw, p)[0]
            strs.append(raw[p + 2: p + 2 + n * 2].decode("utf-16-le", "replace"))
    return strs, utf8

def walk_elems(buf, base):
    """返回 [(name, [(ns,name,dtype,data), ...]), ...]  —— 与 _rebuild5.py 的 parse_axml 同源"""
    n = len(buf); pos = base; chunks = []
    while pos + 8 <= n:
        ct, hs, cs = struct.unpack_from("<HHI", buf, pos)
        chunks.append((pos, ct, hs, cs))
        if cs == 0:
            break
        pos += cs
    res = []
    for (p, ct, hs, cs) in chunks:
        if ct != 0x0102:
            continue
        attrStart, attrSize, attrCount = struct.unpack_from("<HHH", buf, p + 24)
        apos = p + 16 + attrStart
        nameIdx = struct.unpack_from("<I", buf, p + 8 + 4)[0]
        attrs = []
        for i in range(attrCount):
            aoff = apos + i * attrSize
            ns, nm, rawv = struct.unpack_from("<III", buf, aoff)
            dtype = buf[aoff + 15]
            data = struct.unpack_from("<I", buf, aoff + 16)[0]
            attrs.append((ns, nm, dtype, data))
        res.append((nameIdx, attrs))
    return res

def axml_info(path):
    z = zipfile.ZipFile(path)
    m = z.read("AndroidManifest.xml")
    strs, utf8 = parse_strings(m)
    elems = walk_elems(m, 8)
    info = {"utf8": utf8, "pkg": None, "versionCode": None, "versionName": None,
            "minSdkVersion": None, "attr_has_highbit": 0, "attr_total": 0}
    root = elems[0]
    for ns, nm, dt, dv in root[1]:
        name = strs[nm & 0x7FFFFFFF]
        if nm & 0x80000000:
            info["attr_has_highbit"] += 1
        info["attr_total"] += 1
        if name == "package":
            info["pkg"] = strs[dv & 0x7FFFFFFF] if dt == 0x03 else str(dv)
        elif name == "versionCode":
            info["versionCode"] = dv
        elif name == "versionName":
            info["versionName"] = strs[dv & 0x7FFFFFFF].replace("\u0000", "")
    # minSdk 在 uses-sdk
    for nameIdx, attrs in elems:
        if nameIdx & 0x7FFFFFFF < len(strs) and strs[nameIdx & 0x7FFFFFFF] == "uses-sdk":
            for ns, nm, dt, dv in attrs:
                n = strs[nm & 0x7FFFFFFF]
                if n == "minSdkVersion":
                    info["minSdkVersion"] = dv
    return info, strs

src_sha = hashlib.sha256(io.open(SRC_HTML, "rb").read()).hexdigest()
log("== 源 dashboard.html ==")
log("  %s  %d bytes  sha256=%s" % (SRC_HTML, os.path.getsize(SRC_HTML), src_sha[:16]))
log()

for ap in APKS:
    log("=" * 62)
    log("APK: %s" % os.path.basename(ap))
    if not os.path.isfile(ap):
        log("  !! 不存在"); continue
    log("  大小: %d bytes" % os.path.getsize(ap))
    z = zipfile.ZipFile(ap)
    bad = z.testzip()
    log("  ZIP 完整性: %s" % ("OK" if bad is None else "损坏@%s" % bad))
    # 结构
    items = z.infolist()
    log("  条目数: %d" % len(items))
    stored_unaligned = []
    for it in items:
        if it.compress_type == 0:  # STORED
            pad = it.header_offset + 30 + len(it.filename.encode("utf-8")) + len(it.extra)
            if pad % 4 != 0:
                stored_unaligned.append(it.filename)
    log("  STORED 条目 %d 个, 未 4 对齐 %d 个" % (sum(1 for i in items if i.compress_type == 0), len(stored_unaligned)))
    # 包内 html 指纹
    try:
        h = hashlib.sha256(z.read("assets/dashboard.html")).hexdigest()
        log("  包内 assets/dashboard.html sha256=%s  %s" % (h[:16], "==源文件 OK" if h == src_sha else "!!与源不一致"))
    except KeyError:
        log("  !! 包内缺少 assets/dashboard.html")
    # dex
    try:
        dz = z.read("classes.dex")
        log("  classes.dex magic=%r ver=%s size=%d" % (dz[:4], dz[4:8].decode('latin1'), len(dz)))
    except KeyError:
        log("  !! 缺少 classes.dex")
    # META-INF
    mi = sorted(i.filename for i in items if i.filename.startswith("META-INF/"))
    log("  META-INF: %s" % ", ".join(mi))
    # AXML
    info, _ = axml_info(ap)
    log("  AXML: pkg=%s versionCode=%s versionName=%r minSdk=%s" %
        (info["pkg"], info["versionCode"], info["versionName"], info["minSdkVersion"]))
    log("  AXML 根属性带高位: %d/%d (期望 0)" % (info["attr_has_highbit"], info["attr_total"]))
    # zipalign
    try:
        r = subprocess.run([ZIPALIGN, "-c", "-v", "4", ap], capture_output=True, text=True, timeout=120)
        last = [l for l in (r.stdout or "").splitlines() if l.strip()][-1:] or ["(no out)"]
        log("  zipalign: rc=%d -> %s" % (r.returncode, last[0]))
    except Exception as e:
        log("  zipalign 调用失败: %r" % (e,))
    # apksigner verify
    try:
        r = subprocess.run([JAVA, "-jar", APKSIGNER, "verify", "--verbose", "--min-sdk-version", "14", ap],
                           capture_output=True, text=True, timeout=180)
        txt = ((r.stdout or "") + (r.stderr or "")).strip()
        tail = " | ".join(txt.splitlines()[-6:])
        log("  apksigner rc=%d: %s" % (r.returncode, tail))
    except Exception as e:
        log("  apksigner 调用失败: %r" % (e,))
    log()

io.open(os.path.join(W, "_final759.log"), "w", encoding="utf-8").write("\n".join(out))
sys.stdout.write("\n".join(out))
