# -*- coding: utf-8 -*-
# Rebuild KDashBoardL with OFFICIAL signing toolchain (keytool + zipalign + apksigner),
# bump versionCode/versionName, AND fix the AXML attribute-name encoding:
#   the original manifest stored attribute names as PLAIN string-pool indices
#   (e.g. 0x12 = "versionCode") WITHOUT the required 0x80000000 high bit, so
#   Android 4.0's PackageManager cannot resolve any attribute name and aborts the
#   install (INSTALL_FAILED_INVALID_APK). We set the high bit on ns+name for every
#   attribute, making the manifest spec-compliant.
import os, struct, zlib, zipfile, subprocess

# ---------------- paths ----------------
SRC = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.0_757_fixed.apk"
OUT = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.1_758_fixed.apk"
WORK = r"D:\workbuddy\2026-09-23-08-21-00\_build"
os.makedirs(WORK, exist_ok=True)
UNSIGNED = WORK + r"\unsigned.apk"
ALIGNED  = WORK + r"\aligned.apk"
KEYSTORE = WORK + r"\kd_keystore.p12"
ALIAS = "KDashBoardL"; PASS = "kdash2026"
JAVA     = r"C:/Program Files/HONOR/HNPCAIService/jdk/bin/java.exe"
KEYTOOL  = r"C:/Program Files/HONOR/HNPCAIService/jdk/bin/keytool.exe"
ZIPALIGN = r"C:/Users/icewa/android-sdk/build-tools/34.0.0/zipalign.exe"
APKSIGNER= r"C:/Users/icewa/android-sdk/build-tools/34.0.0/lib/apksigner.jar"

# ---------------- AXML parse ----------------
def parse_axml(m):
    assert m[:4] == b"\x03\x00\x08\x00", "not AXML"
    n = len(m); pos = 8; chunks = []
    while pos + 8 <= n:
        ctype, hsize, csize = struct.unpack_from("<HHI", m, pos)
        chunks.append((pos, ctype, hsize, csize))
        if csize == 0: break
        pos += csize
    sp = None
    for (p, ct, hs, cs) in chunks:
        if ct == 0x0001:
            sp = p; break
    stringCount, styleCount, flags, stringsStart, stylesStart = struct.unpack_from("<IIIII", m, sp+8)
    utf8 = bool(flags & 0x100)
    offs = [struct.unpack_from("<I", m, sp+28 + i*4)[0] for i in range(stringCount)]
    base = sp + stringsStart
    str_ranges = []; strings = []
    for o in offs:
        pp = base + o
        if utf8:
            b0 = m[pp]
            if b0 & 0x80:
                ln = ((b0 & 0x7f) << 8) | m[pp+1]; pp += 2
            else:
                ln = b0; pp += 1
            str_ranges.append((pp, ln)); strings.append(m[pp:pp+ln].decode("utf-8", "replace"))
        else:
            ln = struct.unpack_from("<H", m, pp)[0]; pp += 2
            str_ranges.append((pp, ln*2)); strings.append(m[pp:pp+ln*2].decode("utf-16-le", "replace"))
    elements = []
    for (p, ct, hs, cs) in chunks:
        if ct == 0x0102:
            attrStart, attrSize, attrCount = struct.unpack_from("<HHH", m, p+24)
            apos = p + 16 + attrStart
            elements.append((p, attrStart, attrSize, attrCount, apos))
    return strings, str_ranges, utf8, sp, stringCount, stylesStart, styleCount, elements

def read_attrs(m, apos, attrSize, attrCount):
    return [struct.unpack_from("<III", m, apos + i*attrSize) for i in range(attrCount)]  # (ns, name, rawValue)

def encode_str_len(ln, utf8):
    if utf8:
        if ln < 0x80:
            return struct.pack("<B", ln)
        return struct.pack("<BB", ((ln >> 8) & 0x7f) | 0x80, ln & 0xff)
    return struct.pack("<H", ln)

def replace_pool_string(m, sp, idx, new_bytes, utf8, stringCount, stylesStart, styleCount):
    """Replace string #idx; the slot is [base+offs[idx], base+offs[idx+1]) and must be
    rewritten as length-prefix + content + NUL terminator (AXML stores a trailing NUL)."""
    m = bytearray(m)
    stringsStart = struct.unpack_from("<I", m, sp+20)[0]
    base = sp + stringsStart
    offs = [struct.unpack_from("<I", m, sp+28 + i*4)[0] for i in range(stringCount)]
    start = base + offs[idx]
    if idx + 1 < stringCount:
        end = base + offs[idx+1]
    else:
        pool_size = struct.unpack_from("<I", m, sp+4)[0]
        end = (sp + stylesStart) if styleCount else (sp + pool_size)
    if utf8:
        new_ln = len(new_bytes); prefix = encode_str_len(new_ln, True); term = b"\x00"
    else:
        new_ln = len(new_bytes)//2; prefix = struct.pack("<H", new_ln); term = b"\x00\x00"
    new_span = prefix + new_bytes + term
    delta = len(new_span) - (end - start)
    print("    [dbg] slot=[%d,%d) old_size=%d new_size=%d delta=%d new_ln=%d"
          % (start, end, end-start, len(new_span), delta, new_ln))
    m = m[:start] + bytearray(new_span) + m[end:]
    if delta != 0:
        for i in range(idx+1, stringCount):
            opos = sp + 28 + i*4
            o = struct.unpack_from("<I", m, opos)[0]
            struct.pack_into("<I", m, opos, o + delta)
        sp_size = struct.unpack_from("<I", m, sp+4)[0]
        struct.pack_into("<I", m, sp+4, sp_size + delta)
        xml_size = struct.unpack_from("<I", m, 4)[0]
        struct.pack_into("<I", m, 4, xml_size + delta)
        if styleCount != 0:
            struct.pack_into("<I", m, sp+24, stylesStart + delta)
    return bytes(m)

def fix_and_bump(m, new_code, new_name):
    m = bytearray(m)
    strings, str_ranges, utf8, sp, stringCount, stylesStart, styleCount, elements = parse_axml(m)
    # ---- PASS 1: set the 0x80000000 high bit on ns + name of every attribute ----
    set_bits = 0
    for (p, attrStart, attrSize, attrCount, apos) in elements:
        for i in range(attrCount):
            aoff = apos + i*attrSize
            ns, name, rawValue = struct.unpack_from("<III", m, aoff)
            if ns != 0 and (ns & 0x80000000) == 0:
                struct.pack_into("<I", m, aoff+0, ns | 0x80000000); set_bits += 1
            if (name & 0x80000000) == 0 and name < 0x01000000:  # plain string index -> mark it
                struct.pack_into("<I", m, aoff+4, name | 0x80000000); set_bits += 1
    # ---- PASS 2: resolve names & bump versionCode / versionName ----
    def rname(aname):
        idx = aname & 0x7FFFFFFF
        return strings[idx] if 0 <= idx < len(strings) else None
    cur_code = None; cur_name = None; name_idx = None; min_sdk = None; target_sdk = None
    for (p, attrStart, attrSize, attrCount, apos) in elements:
        for i in range(attrCount):
            aoff = apos + i*attrSize
            ns, name, rawValue = struct.unpack_from("<III", m, aoff)
            nm = rname(name)
            atype = struct.unpack_from("<B", m, aoff+15)[0]
            adata = struct.unpack_from("<I", m, aoff+16)[0]
            if nm == "versionCode":
                cur_code = adata
                struct.pack_into("<I", m, aoff+16, new_code)
            elif nm == "versionName":
                name_idx = adata; cur_name = strings[adata]
            elif nm == "minSdkVersion":  min_sdk = adata
            elif nm == "targetSdkVersion": target_sdk = adata
    print("  [fix] high bits set on %d attribute fields" % set_bits)
    print("  [info] minSdkVersion=%s targetSdkVersion=%s" % (min_sdk, target_sdk))
    print("  current versionCode=%s versionName=%r" % (cur_code, cur_name))
    new_bytes = new_name.encode("utf-8" if utf8 else "utf-16-le")
    old_len = str_ranges[name_idx][1]
    m = replace_pool_string(m, sp, name_idx, new_bytes, utf8, stringCount, stylesStart, styleCount)
    print("  versionName replaced (content %d -> %d bytes)" % (old_len, len(new_bytes)))
    print("  new versionCode=%d versionName=%r" % (new_code, new_name))
    return bytes(m)

# ---------------- 1. collect entries + fix/bump manifest ----------------
src = zipfile.ZipFile(SRC)
entries = [(zi.filename, src.read(zi.filename)) for zi in src.infolist()
           if not zi.filename.startswith("META-INF/")]
m = dict(entries)["AndroidManifest.xml"]
new_code = 758
new_name = "V3.1_758"
m2 = fix_and_bump(m, new_code, new_name)
entries = [(n, d if n != "AndroidManifest.xml" else m2) for (n, d) in entries]
entries.sort(key=lambda e: e[0])
print("collected %d entries (manifest fixed + version bumped)" % len(entries))

# ---------------- 2. write unsigned aligned APK (STORED, 4-aligned) ----------------
ALIGN = 4
def zipalign_write(path, items):
    buf = bytearray(); central = []
    for nm, data in items:
        name_b = nm.encode("utf-8")
        lho = len(buf)
        base = lho + 30 + len(name_b)
        extra_len = (ALIGN - (base % ALIGN)) % ALIGN
        extra = b"\x00" * extra_len
        crc = zlib.crc32(data) & 0xffffffff
        flag = 0x0800
        buf += struct.pack("<IHHHHHIIIHH", 0x04034b50, 20, flag, 0, 0, 0, crc, len(data), len(data), len(name_b), len(extra))
        buf += name_b + extra + data
        central.append(struct.pack("<IHHHHHHIIIHHHHHII", 0x02014b50, 20, 20, flag, 0, 0, 0, crc,
                     len(data), len(data), len(name_b), len(extra), 0, 0, 0, 0, lho) + name_b + extra)
    cd_start = len(buf)
    for c in central:
        buf += c
    cd_size = len(buf) - cd_start
    buf += struct.pack("<IHHHHIIH", 0x06054b50, 0, 0, len(items), len(items), cd_size, cd_start, 0)
    with open(path, "wb") as f:
        f.write(buf)

zipalign_write(UNSIGNED, entries)
print("wrote unsigned:", UNSIGNED, os.path.getsize(UNSIGNED))

# ---------------- 3. keystore (keytool) ----------------
if not os.path.exists(KEYSTORE):
    r = subprocess.run([KEYTOOL, "-genkeypair", "-alias", ALIAS, "-keyalg", "RSA",
                        "-keysize", "2048", "-sigalg", "SHA1withRSA", "-validity", "3650",
                        "-storetype", "PKCS12", "-keystore", KEYSTORE,
                        "-storepass", PASS, "-keypass", PASS,
                        "-dname", "CN=KDashBoardL, O=KDashBoardL"],
                       capture_output=True, text=True)
    print("keytool rc=%d" % r.returncode, r.stderr[:500])
else:
    print("keystore exists, skip")

# ---------------- 4. zipalign (official) ----------------
if os.path.exists(ALIGNED):
    os.remove(ALIGNED)
r = subprocess.run([ZIPALIGN, "-f", "-p", "4", UNSIGNED, ALIGNED], capture_output=True, text=True)
print("zipalign rc=%d" % r.returncode, r.stderr[:500])

# ---------------- 5. apksigner sign (v1 SHA1, min-sdk 14) ----------------
r = subprocess.run([JAVA, "-jar", APKSIGNER, "sign",
                    "--ks", KEYSTORE, "--ks-key-alias", ALIAS,
                    "--ks-pass", "pass:"+PASS, "--key-pass", "pass:"+PASS,
                    "--min-sdk-version", "14",
                    "--v1-signing-enabled", "true", "--v2-signing-enabled", "true",
                    "--v3-signing-enabled", "true",
                    "--out", OUT, ALIGNED],
                   capture_output=True, text=True)
print("apksigner sign rc=%d" % r.returncode)
print("OUT:", r.stdout[:800], r.stderr[:800])

# ---------------- 6. verify ----------------
r = subprocess.run([JAVA, "-jar", APKSIGNER, "verify", "--verbose",
                    "--min-sdk-version", "14", "--print-certs", OUT],
                   capture_output=True, text=True)
print("=== apksigner verify (min-sdk 14) ===")
print("rc=%d" % r.returncode)
print(r.stdout[:2000])
print(r.stderr[:2000])

# ---------------- 7. self-check: re-parse the FINAL signed APK manifest ----------------
final = zipfile.ZipFile(OUT)
fm = final.read("AndroidManifest.xml")
strings, str_ranges, utf8, sp, stringCount, stylesStart, styleCount, elements = parse_axml(fm)
def rname2(an):
    idx = an & 0x7FFFFFFF
    return strings[idx] if 0 <= idx < len(strings) else None
fc=None; fn=None; fmin=None; fmax=None; bad=0
for (p, attrStart, attrSize, attrCount, apos) in elements:
    for i in range(attrCount):
        aoff = apos + i*attrSize
        ns, name, rawValue = struct.unpack_from("<III", fm, aoff)
        if (name & 0x80000000) == 0 and name < 0x01000000:
            bad += 1
        nm = rname2(name); at = struct.unpack_from("<B", fm, aoff+15)[0]
        ad = struct.unpack_from("<I", fm, aoff+16)[0]
        if nm == "versionCode": fc = ad
        elif nm == "versionName": fn = strings[ad]
        elif nm == "minSdkVersion": fmin = ad
        elif nm == "targetSdkVersion": fmax = ad
print("--- self-check on FINAL APK ---")
print("versionCode=%s versionName=%r minSdk=%s targetSdk=%s" % (fc, fn, fmin, fmax))
print("attributes still missing high bit (should be 0): %d" % bad)
assert fc == 758 and fn == "V3.1_758" and fmin == 14 and bad == 0, "FINAL APK manifest check FAILED"
print("SELF-CHECK PASS")

print("FINAL:", OUT, os.path.getsize(OUT) if os.path.exists(OUT) else "MISSING")
