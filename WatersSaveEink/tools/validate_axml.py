# -*- coding: utf-8 -*-
# Strictly validate AXML chunk structure of both the ORIGINAL and MODIFIED manifests.
import struct, zipfile
A = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.0_757_fixed.apk"
B = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.1_758_fixed.apk"

def strict(m, label):
    print("==== %s (len=%d) ====" % (label, len(m)))
    t, hs, size = struct.unpack_from("<HHI", m, 0)
    print("top chunk: type=0x%04X headerSize=%d size=%d  (file len=%d) %s"
          % (t, hs, size, len(m), "OK" if size == len(m) else "** SIZE MISMATCH **"))
    pos = 8; n = len(m); chunks = []
    while pos + 8 <= n:
        ct, chs, csz = struct.unpack_from("<HHI", m, pos)
        chunks.append((pos, ct, chs, csz))
        if csz == 0:
            print("  !! chunk size 0 at %d" % pos); break
        if csz < chs:
            print("  !! chunk size < headerSize at %d (csz=%d chs=%d)" % (pos, csz, chs)); break
        pos += csz
    print("chunks: %d, walked-to=%d (file=%d) %s" % (len(chunks), pos, n, "OK" if pos == n else "** TRAILING/MISMATCH **"))
    for (p, ct, chs, csz) in chunks:
        nm = {0x0001:"StringPool",0x0100:"StartNS",0x0101:"EndNS",0x0102:"StartElem",
              0x0103:"EndElem",0x0180:"ResourceMap"}.get(ct, "0x%04X" % ct)
        flag = "" if (p % 4 == 0) else "  <-- chunk not 4-aligned!"
        print("   @%-6d %-12s hdr=%d size=%d%s" % (p, nm, chs, csz, flag))
    # string pool detail
    sp = next(p for (p, ct, hs2, cs) in chunks if ct == 0x0001)
    sCount, stCount, flags, sStart, stStart = struct.unpack_from("<IIIII", m, sp+8)
    utf8 = bool(flags & 0x100)
    offs = [struct.unpack_from("<I", m, sp+28 + i*4)[0] for i in range(sCount)]
    data_end = sp + (stStart if stCount else struct.unpack_from("<I", m, sp+4)[0])
    oob = sum(1 for o in offs if not (0 <= o < (data_end - (sp + sStart)) + 1))
    print("  pool: count=%d styles=%d utf8=%s sStart=%d stStart=%d poolSize=%d oob_offsets=%d"
          % (sCount, stCount, utf8, sStart, stStart, struct.unpack_from("<I", m, sp+4)[0], oob))
    print()

strict(zipfile.ZipFile(A).read("AndroidManifest.xml"), "ORIGINAL V3.0_757_fixed")
strict(zipfile.ZipFile(B).read("AndroidManifest.xml"), "MODIFIED V3.1_758_fixed")
