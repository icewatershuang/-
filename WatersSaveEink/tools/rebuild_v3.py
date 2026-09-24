# -*- coding: utf-8 -*-
# CORRECTED rebuild: keep the ORIGINAL AXML attribute encoding (plain string-pool indices,
# no 0x80000000) -- identical in style to a real working APK -- bump version fully IN-PLACE
# (no string-pool growth, no structural change), compress like the original, and sign v1-only.
import os, struct, zlib, zipfile, subprocess

SRC = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.0_757_fixed.apk"
OUT = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.1_758b.apk"
WORK = r"D:\workbuddy\2026-09-23-08-21-00\_build"
os.makedirs(WORK, exist_ok=True)
UNSIGNED = WORK + r"\u3.apk"
ALIGNED  = WORK + r"\a3.apk"
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
    """Only in-place edits: versionCode(int) and versionName(string, SAME length)."""
    m = bytearray(m)
    strings, ranges, elems = parse_axml(m)
    cur_code = cur_name = None; name_idx = None
    for (p, attrStart, attrSize, attrCount, apos) in elems:
        for i in range(attrCount):
            aoff = apos + i*attrSize
            ns, name, raw = struct.unpack_from("<III", m, aoff)
            idx = name & 0x7fffffff  # plain index in this file; works with/without high bit
            nm = strings[idx] if idx < len(strings) else None
            atype = struct.unpack_from("<B", m, aoff+15)[0]
            adata = struct.unpack_from("<I", m, aoff+16)[0]
            if nm == "versionCode":
                cur_code = adata; struct.pack_into("<I", m, aoff+16, new_code)
            elif nm == "versionName":
                name_idx = adata; cur_name = strings[adata]
    print("  versionCode %s -> %d ; versionName %r -> %r" % (cur_code, new_code, cur_name, new_name))
    co, blen = ranges[name_idx]
    nb = new_name.encode("utf-16-le")
    assert len(nb) == blen, "versionName must keep SAME byte length (in-place): %d vs %d" % (len(nb), blen)
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
        buf += struct.pack("<IHHHHHIIIHH", 0x04034b50, 20, flag, meth, 0, 0, crc, len(body), len(data), len(name_b), len(extra))
        buf += name_b + extra + body
        central.append(struct.pack("<IHHHHHHIIIHHHHHII", 0x02014b50, 20, 20, flag, meth, 0, 0, crc,
                       len(body), len(data), len(name_b), len(extra), 0, 0, 0, 0, lho) + name_b + extra)
    cd_start = len(buf)
    for c in central: buf += c
    cd_size = len(buf) - cd_start
    buf += struct.pack("<IHHHHIIH", 0x06054b50, 0, 0, len(items), len(items), cd_size, cd_start, 0)
    open(path, "wb").write(buf)

# ---- collect entries (original manifest encoding preserved) ----
src = zipfile.ZipFile(SRC)
entries = [(zi.filename, src.read(zi.filename)) for zi in src.infolist()
           if not zi.filename.startswith("META-INF/") and not zi.filename.endswith(".bak")]
m = dict(entries)["AndroidManifest.xml"]
m2 = bump_inplace(m, 758, "V3.1")
entries = [(n, d if n != "AndroidManifest.xml" else m2) for (n, d) in entries]
entries.sort(key=lambda e: e[0])
print("entries:", [n for (n, d) in entries])

# compress big assets like the original; keep resources.arsc STORED
COMPRESS = {"assets/dashboard.html", "assets/hls.min.js", "assets/radio_presets.js",
            "AndroidManifest.xml", "classes.dex",
            "res/drawable-xxhdpi/ic_launcher.png", "res/drawable/ic_notify.xml",
            "res/xml/device_admin.xml", "res/xml/network_security_config.xml"}
write_apk(UNSIGNED, entries, COMPRESS)
print("unsigned:", os.path.getsize(UNSIGNED))

if os.path.exists(ALIGNED): os.remove(ALIGNED)
r = subprocess.run([ZIPALIGN, "-f", "-p", "4", UNSIGNED, ALIGNED], capture_output=True, text=True)
print("zipalign rc=%d %s" % (r.returncode, r.stderr[:200]))

r = subprocess.run([JAVA, "-jar", APKSIGNER, "sign",
                    "--ks", KEYSTORE, "--ks-key-alias", ALIAS,
                    "--ks-pass", "pass:"+PASS, "--key-pass", "pass:"+PASS,
                    "--min-sdk-version", "14",
                    "--v1-signing-enabled", "true",
                    "--v2-signing-enabled", "false",
                    "--v3-signing-enabled", "false",
                    "--out", OUT, ALIGNED],
                   capture_output=True, text=True)
print("apksigner sign rc=%d %s %s" % (r.returncode, r.stdout[:300], r.stderr[:300]))

r = subprocess.run([JAVA, "-jar", APKSIGNER, "verify", "--verbose",
                    "--min-sdk-version", "14", "--print-certs", OUT], capture_output=True, text=True)
print("=== verify rc=%d ===" % r.returncode)
print(r.stdout[:1600]); print(r.stderr[:600])
print("FINAL:", OUT, os.path.getsize(OUT) if os.path.exists(OUT) else "MISSING")
