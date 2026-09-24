# -*- coding: utf-8 -*-
import struct, zipfile
SRC = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.0_757_fixed.apk"
src = zipfile.ZipFile(SRC)
m = src.read("AndroidManifest.xml")
assert m[:4] == b"\x03\x00\x08\x00"
n=len(m); pos=8; chunks=[]
while pos+8<=n:
    ctype,hsize,csize=struct.unpack_from("<HHI",m,pos)
    chunks.append((pos,ctype,hsize,csize))
    if csize==0: break
    pos+=csize
sp=None
for (p,ct,hs,cs) in chunks:
    if ct==0x0001: sp=p; break
stringCount,styleCount,flags,stringsStart,stylesStart=struct.unpack_from("<IIIII",m,sp+8)
utf8=bool(flags&0x100)
offs=[struct.unpack_from("<I",m,sp+28+i*4)[0] for i in range(stringCount)]
base=sp+stringsStart
strings=[]
for o in offs:
    pp=base+o
    if utf8:
        b0=m[pp]
        if b0&0x80: ln=((b0&0x7f)<<8)|m[pp+1]; pp+=2
        else: ln=b0; pp+=1
        strings.append(m[pp:pp+ln].decode("utf-8","replace"))
    else:
        ln=struct.unpack_from("<H",m,pp)[0]; pp+=2
        strings.append(m[pp:pp+ln*2].decode("utf-16-le","replace"))
print("string pool: count=%d utf8=%s"%(stringCount,utf8))
print("strings[0..30]=", strings[:30])
print("---- elements ----")
for (p,ct,hs,cs) in chunks:
    if ct!=0x0102: continue
    attrStart,attrSize,attrCount=struct.unpack_from("<HHH",m,p+24)
    apos=p+16+attrStart
    print("ELEMENT @%d attrStart=%d attrSize=%d attrCount=%d apos=%d"%(p,attrStart,attrSize,attrCount,apos))
    for i in range(attrCount):
        aoff=apos+i*attrSize
        ans,aname,rawValue=struct.unpack_from("<III",m,aoff)
        atype=struct.unpack_from("<B",m,aoff+15)[0]
        adata=struct.unpack_from("<I",m,aoff+16)[0]
        if aname & 0x80000000:
            idx=aname&0x7FFFFFFF
            nm=strings[idx] if idx<len(strings) else "OOB(%d)"%idx
            kind="STRIDX"
        else:
            nm="0x%08X"%aname
            kind="RESID"
        print("   attr[%d] %s %s atype=0x%02X adata=%d rawValue=%d"%(i,kind,nm,atype,adata,rawValue))
