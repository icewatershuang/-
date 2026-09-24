# -*- coding: utf-8 -*-
import struct, zipfile, hashlib
OUT = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.1_758_fixed.apk"
raw = open(OUT, "rb").read()
print("APK size:", len(raw), "bytes")
print("SHA-256 :", hashlib.sha256(raw).hexdigest())
print("MD5     :", hashlib.md5(raw).hexdigest())
z = zipfile.ZipFile(OUT)
bad = 0
print("\n%-34s %8s %8s %6s %s" % ("entry", "size", "comp", "data_off", "off%4"))
for zi in z.infolist():
    # locate local header to get data offset
    lho = zi.header_offset
    sig, ver, flg, meth, t, d, crc, csz, usz, nlen, elen = struct.unpack_from("<IHHHHHIIIHH", raw, lho)
    data_off = lho + 30 + nlen + elen
    align_ok = (data_off % 4 == 0)
    if not align_ok:
        bad += 1
    mth = {0: "STORED", 8: "DEFLATE"}.get(meth, str(meth))
    print("%-34s %8d %8s %6d %5d%s" % (zi.filename, zi.file_size, mth, data_off, data_off % 4,
                                        "" if align_ok else "  <-- MISALIGNED"))
print("\nentries total=%d  misaligned=%d" % (len(z.infolist()), bad))
dex = z.read("classes.dex")
print("classes.dex: %d bytes, magic=%r version=%r" % (len(dex), dex[:4], dex[4:8]))
print("META-INF:", [n for n in z.namelist() if n.startswith("META-INF/")])
print("VERDICT:", "ALIGN OK / ALL STORED-COMPATIBLE" if bad == 0 else "PROBLEM")
