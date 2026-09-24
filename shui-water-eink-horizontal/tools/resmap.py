# -*- coding: utf-8 -*-
import struct, zipfile
# Use our source manifest (apk_extract) which is the pristin original bytes
m = open(r"D:\workbuddy\2026-09-23-08-21-00\apk_extract\AndroidManifest.xml","rb").read()
n=len(m); pos=8; chunks=[]
while pos+8<=n:
    ct,hs,cs=struct.unpack_from("<HHI",m,pos); chunks.append((pos,ct,hs,cs)); pos+=cs
# string pool
sp=next(p for (p,ct,hs,cs) in chunks if ct==0x0001)
sCount,stCount,flags,sStart,stStart=struct.unpack_from("<IIIII",m,sp+8)
base=sp+sStart
offs=[struct.unpack_from("<I",m,sp+28+i*4)[0] for i in range(sCount)]
strings=[]
for o in offs:
    pp=base+o; ln=struct.unpack_from("<H",m,pp)[0]; pp+=2
    strings.append(m[pp:pp+ln*2].decode("utf-16-le","replace"))
# resource map
rm=next((c for c in chunks if c[1]==0x0180), None)
print("ResourceMap chunk:", rm)
if rm:
    rp,_,rhs,rcs=rm
    cnt=(rcs-rhs)//4
    print("  entries=%d" % cnt)
    for i in range(cnt):
        rid=struct.unpack_from("<I",m,rp+rhs+i*4)[0]
        if rid:
            print("    strIdx %3d %-24r -> resID 0x%08X" % (i, strings[i] if i<len(strings) else '?', rid))
print()
print("Is there a ResourceMap entry for versionCode(str 18)? on versionName(str 19)?")
