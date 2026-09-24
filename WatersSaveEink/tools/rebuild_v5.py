# -*- coding: utf-8 -*-
"""V3.2_759：把修好的 dashboard.html 打进包，并原地升版本号（758/V3.1 -> 759/V3.2）。

沿用 758b 的构建口径（原始 AXML 编码 + 按原版压缩 + 官方 apksigner v1/SHA1 签名），
只做两处改动：替换 assets/dashboard.html、原地升版本号（等长，不动字符串池）。
"""
import os, struct, zlib, zipfile, subprocess, hashlib

WORK = r"D:\workbuddy\2026-09-23-08-21-00\_build"
SRC  = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.1_758b.apk"      # 用户已装成功的那版
HTML = r"D:\workbuddy\2026-09-23-08-21-00\apk_extract\assets\dashboard.html"  # 修好的页面
OUT  = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.2_759.apk"
OUT2 = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.2_759_v123.apk"

NEW_CODE = 759
NEW_NAME = "V3.2"          # 必须与旧的 "V3.1" 等长（原地改写）

UNSIGNED = WORK + r"\u5.apk"
ALIGNED  = WORK + r"\a5.apk"
KEYSTORE = WORK + r"\kd_keystore.p12"
ALIAS = "KDashBoardL"; PASS = "kdash2026"
JAVA     = r"C:/Program Files/HONOR/HNPCAIService/jdk/bin/java.exe"
ZIPALIGN = r"C:/Users/icewa/android-sdk/build-tools/34.0.0/zipalign.exe"
APKSIGNER= r"C:/Users/icewa/android-sdk/build-tools/34.0.0/lib/apksigner.jar"

A_VERSIONCODE = 0x0101021B
A_VERSIONNAME = 0x0101021C


def parse_axml(m):
    n = len(m); pos = 8; chunks = []
    while pos + 8 <= n:
        ct, hs, cs = struct.unpack_from("<HHI", m, pos); chunks.append((pos, ct, hs, cs))
        if cs == 0: break
        pos += cs
    sp = next(p for (p, ct, hs, cs) in chunks if ct == 0x0001)
    sCount, stCount, flags, sStart, stStart = struct.unpack_from("<IIIII", m, sp+8)
    base = sp + sStart
    offs = [struct.unpack_from("<I", m, sp+28 + i*4)[0] for i in range(sCount)]
    ranges = []; strings = []
    for o in offs:
        pp = base + o; ln = struct.unpack_from("<H", m, pp)[0]; pp += 2
        ranges.append((pp, ln*2)); strings.append(m[pp:pp+ln*2].decode("utf-16-le", "replace"))
    elems = []
    for (p, ct, hs, cs) in chunks:
        if ct == 0x0102:
            attrStart, attrSize, attrCount = struct.unpack_from("<HHH", m, p+24)
            elems.append((p, attrStart, attrSize, attrCount, p+16+attrStart))
    return strings, ranges, elems


def bump_inplace(m, new_code, new_name):
    m = bytearray(m)
    strings, ranges, elems = parse_axml(m)
    cur_code = cur_name = None; name_idx = None
    min_sdk = None
    for (p, attrStart, attrSize, attrCount, apos) in elems:
        for i in range(attrCount):
            aoff = apos + i*attrSize
            ns, name, raw = struct.unpack_from("<III", m, aoff)
            idx = name & 0x7fffffff
            nm = strings[idx] if idx < len(strings) else None
            adata = struct.unpack_from("<I", m, aoff+16)[0]
            if nm == "versionCode": cur_code = adata; struct.pack_into("<I", m, aoff+16, new_code)
            elif nm == "versionName": name_idx = adata; cur_name = strings[adata]
            elif nm == "minSdkVersion": min_sdk = adata
    print("  versionCode %s -> %d ; versionName %r -> %r ; minSdkVersion=%s"
          % (cur_code, new_code, cur_name, new_name, min_sdk))
    co, blen = ranges[name_idx]
    nb = new_name.encode("utf-16-le")
    assert len(nb) == blen, "versionName 必须等长（原地改写）：%d vs %d" % (len(nb), blen)
    m[co:co+blen] = nb
    return bytes(m)


def deflate(data):
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    return co.compress(data) + co.flush()


def write_apk(path, items, compress_names):
    ALIGN = 4
    buf = bytearray(); central = []
    for nm, data in items:
        name_b = nm.encode("utf-8")
        if nm in compress_names:
            body = deflate(data); meth = 8
        else:
            body = data; meth = 0
        crc = zlib.crc32(data) & 0xffffffff
        flag = 0x0800
        lho = len(buf)
        base = lho + 30 + len(name_b)
        extra_len = (ALIGN - (base % ALIGN)) % ALIGN if meth == 0 else 0
        extra = b"\x00" * extra_len
        buf += struct.pack("<IHHHHHIIIHH", 0x04034b50, 20, flag, meth, 0, 0, crc,
                           len(body), len(data), len(name_b), len(extra))
        buf += name_b + extra + body
        central.append(struct.pack("<IHHHHHHIIIHHHHHII", 0x02014b50, 20, 20, flag, meth, 0, 0, crc,
                       len(body), len(data), len(name_b), len(extra), 0, 0, 0, 0, lho) + name_b + extra)
    cd_start = len(buf)
    for c in central: buf += c
    cd_size = len(buf) - cd_start
    buf += struct.pack("<IHHHHIIH", 0x06054b50, 0, 0, len(items), len(items), cd_size, cd_start, 0)
    open(path, "wb").write(buf)


# ---------------- 1. entries ----------------
src = zipfile.ZipFile(SRC)
entries = [(zi.filename, src.read(zi.filename)) for zi in src.infolist()
           if not zi.filename.startswith("META-INF/") and not zi.filename.endswith(".bak")]
html_new = open(HTML, "rb").read()
h_new = hashlib.sha256(html_new).hexdigest()
print("new dashboard.html: %d bytes sha=%s" % (len(html_new), h_new[:16]))

m = dict(entries)["AndroidManifest.xml"]
m2 = bump_inplace(m, NEW_CODE, NEW_NAME)

out_entries = []
for (n, d) in entries:
    if n == "AndroidManifest.xml": d = m2
    elif n == "assets/dashboard.html": d = html_new
    out_entries.append((n, d))
out_entries.sort(key=lambda e: e[0])
print("entries:", [n for (n, d) in out_entries])

COMPRESS = {"assets/dashboard.html", "assets/hls.min.js", "assets/radio_presets.js",
            "AndroidManifest.xml", "classes.dex",
            "res/drawable-xxhdpi/ic_launcher.png", "res/drawable/ic_notify.xml",
            "res/xml/device_admin.xml", "res/xml/network_security_config.xml"}
write_apk(UNSIGNED, out_entries, COMPRESS)
print("unsigned:", os.path.getsize(UNSIGNED))

# ---------------- 2. zipalign ----------------
if os.path.exists(ALIGNED): os.remove(ALIGNED)
r = subprocess.run([ZIPALIGN, "-f", "-p", "4", UNSIGNED, ALIGNED],
                   capture_output=True, text=True)
print("zipalign rc=%d %s" % (r.returncode, r.stderr[:200]))


def sign(out, v1=True, v2=False, v3=False):
    if os.path.exists(out): os.remove(out)
    r = subprocess.run([JAVA, "-jar", APKSIGNER, "sign",
                        "--ks", KEYSTORE, "--ks-key-alias", ALIAS,
                        "--ks-pass", "pass:"+PASS, "--key-pass", "pass:"+PASS,
                        "--min-sdk-version", "14",
                        "--v1-signing-enabled", "true" if v1 else "false",
                        "--v2-signing-enabled", "true" if v2 else "false",
                        "--v3-signing-enabled", "true" if v3 else "false",
                        "--out", out, ALIGNED], capture_output=True, text=True)
    print("  sign %s rc=%d %s %s" % (os.path.basename(out), r.returncode,
                                     r.stdout[:200], r.stderr[:200]))
    r = subprocess.run([JAVA, "-jar", APKSIGNER, "verify", "--verbose",
                        "--min-sdk-version", "14", out], capture_output=True, text=True)
    ok = "Verifies" in r.stdout
    print("  verify %s -> %s" % (os.path.basename(out), "Verifies" if ok else "FAILED"))
    for line in r.stdout.splitlines():
        if line.strip().startswith(("Verified using", "Number of signers")):
            print("     ", line.strip())
    return out


sign(OUT, True, False, False)
sign(OUT2, True, True, True)

# ---------------- 3. self-check on final package ----------------
print("=== self-check ===")
z = zipfile.ZipFile(OUT)
h_in = hashlib.sha256(z.read("assets/dashboard.html")).hexdigest()
print("dashboard.html in APK matches source:", h_in == h_new, h_in[:16])
strings, ranges, elems = parse_axml(z.read("AndroidManifest.xml"))
vals = {}
for (p, attrStart, attrSize, attrCount, apos) in elems:
    for i in range(attrCount):
        aoff = apos + i*attrSize
        ns, name, raw = struct.unpack_from("<III", z.read("AndroidManifest.xml"), aoff)
        idx = name & 0x7fffffff
        nm = strings[idx] if idx < len(strings) else None
        if nm in ("versionCode", "versionName", "minSdkVersion", "package"):
            if nm == "versionName": vals[nm] = strings[struct.unpack_from("<I", z.read("AndroidManifest.xml"), aoff+16)[0]]
            elif nm == "package": vals[nm] = strings[struct.unpack_from("<I", z.read("AndroidManifest.xml"), aoff+16)[0]]
            else: vals[nm] = struct.unpack_from("<I", z.read("AndroidManifest.xml"), aoff+16)[0]
print("manifest:", vals)
print("OK" if vals.get("versionCode") == NEW_CODE and vals.get("versionName") == NEW_NAME
      else "MISMATCH", "minSdk=%s" % vals.get("minSdkVersion"))
for f in (OUT, OUT2):
    print("FINAL:", f, os.path.getsize(f) if os.path.exists(f) else "MISSING")
