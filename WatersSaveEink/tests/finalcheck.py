# -*- coding: utf-8 -*-
import struct, zipfile
OUT = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.1_758_fixed.apk"
fm = zipfile.ZipFile(OUT).read("AndroidManifest.xml")
sp = 8  # first chunk is string pool
stringCount, styleCount, flags, stringsStart, stylesStart = struct.unpack_from("<IIIII", fm, sp+8)
utf8 = bool(flags & 0x100)
offs = [struct.unpack_from("<I", fm, sp+28 + i*4)[0] for i in range(stringCount)]
base = sp + stringsStart
print("utf8=%s count=%d stringsStart=%d base=%d" % (utf8, stringCount, stringsStart, base))
for idx in (44,45,46,47,48):
    o = offs[idx]
    pp = base + o
    if utf8:
        b0=fm[pp]; ln=((b0&0x7f)<<8)|fm[pp+1] if b0&0x80 else b0; pl=2 if b0&0x80 else 1
    else:
        ln=struct.unpack_from("<H", fm, pp)[0]; pl=2
    content = fm[pp+pl: pp+pl+ln*(2 if not utf8 else 1)]
    try:
        s = content.decode("utf-16-le" if not utf8 else "utf-8","replace")
    except: s="?"
    print("str[%d] off=%d prefixLen=%d len=%d raw=%r str=%r" % (idx, o, pl, ln, content[:20], s))
# show the versionCode/Name attribute region (manifest element)
# find manifest element
n=len(fm); pos=8; chunks=[]
while pos+8<=n:
    ctype,hsize,csize=struct.unpack_from("<HHI",fm,pos); chunks.append((pos,ctype,hsize,csize))
    if csize==0: break
    pos+=csize
for (p,ct,hs,cs) in chunks:
    if ct==0x0102:
        attrStart,attrSize,attrCount=struct.unpack_from("<HHH",fm,p+24); apos=p+16+attrStart
        for i in range(attrCount):
            aoff=apos+i*attrSize
            ns,name,raw=struct.unpack_from("<III",fm,aoff)
            idx=name&0x7FFFFFFF
            nm=struct.unpack_from("<H",fm,0)  # dummy
            print("attr[%d] nameIdx=%d nameStr=%r adata=%d"%(i, idx, None, struct.unpack_from("<I",fm,aoff+16)[0]))
        break
