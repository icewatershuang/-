# -*- coding: utf-8 -*-
import os, struct, zlib, hashlib, base64, datetime
import asn1crypto.x509 as a_x509
import asn1crypto.cms as a_cms
import asn1crypto.core as a_core
from cryptography.hazmat.primitives.asymmetric import rsa, padding as _pad
from cryptography.hazmat.primitives import hashes
from cryptography.x509 import load_der_x509_certificate

APK = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.0_757_fixed.apk"
print("FILE:", APK, os.path.getsize(APK), "bytes")

with open(APK, "rb") as f:
    raw = f.read()
import zipfile
z = zipfile.ZipFile(APK)
infos = z.infolist()
ALIGN = 4
problems = []
for zi in infos:
    extra_len = struct.unpack("<H", raw[zi.header_offset+28:zi.header_offset+30])[0]
    data_off = zi.header_offset + 30 + len(zi.filename) + extra_len
    if zi.compress_type == 0 and data_off % ALIGN != 0:
        problems.append(zi.filename)
print("ALIGNMENT:", "OK" if not problems else problems)

# ---- certificate ----
print("\n[CERTIFICATE]")
cms = z.read("META-INF/CERT.RSA")
ci = a_cms.ContentInfo.load(cms)
sd = ci["content"]
acert_choice = sd["certificates"][0]
acert = acert_choice.chosen if hasattr(acert_choice, "chosen") else acert_choice
print("  subject:", dict(acert.subject.native))
print("  issuer :", dict(acert.issuer.native))
print("  serial :", hex(int(acert.serial_number)))
print("  sig alg:", str(acert["signature_algorithm"].native))
tbs = acert["tbs_certificate"]
nb = tbs["validity"]["not_before"].native
na = tbs["validity"]["not_after"].native
now = datetime.datetime.now(datetime.timezone.utc)
print("  not_before:", nb)
print("  not_after :", na, "  now(utc):", now)
print("  validity covers now:", (nb <= now <= na))
print("  self-signed:", acert.issuer.dump() == acert.subject.dump())

# ---- signature verify (Android 4.0 / Harmony style) ----
print("\n[SIGNATURE VERIFY - Android JarVerifier style]")
sf = z.read("META-INF/CERT.SF")
manifest = z.read("META-INF/MANIFEST.MF")
signer = sd["signer_infos"][0]
attrs = signer["signed_attrs"]
emb = attrs.dump()  # 0xA0 form
verify_input = b"\x31" + emb[1:]
md = None
for at in attrs:
    if str(at["type"]) == "1.2.840.113549.1.9.4":
        md = bytes(at["values"][0])
print("  signed_attrs first byte:", "0x%02X" % emb[0], " (expect 0xA0 implicit[0] SET)")
print("  digest_algorithms:", [str(x.native) for x in sd["digest_algorithms"]])
print("  signer digest_algorithm:", str(signer["digest_algorithm"].native))
print("  signer signature_algorithm:", str(signer["signature_algorithm"].native))
print("  CERT.SF sha1 == message_digest attr:", hashlib.sha1(sf).digest() == md)
cpp_cert = load_der_x509_certificate(acert.dump())
cpp_pub = cpp_cert.public_key()
try:
    cpp_pub.verify(bytes(signer["signature"]), verify_input, _pad.PKCS1v15(), hashes.SHA1())
    print("  RSA signature over signed_attrs: VALID")
except Exception as e:
    print("  RSA signature over signed_attrs: INVALID ->", repr(e))
# also check MANIFEST digests
print("  MANIFEST entries covered:", manifest.count(b"SHA1-Digest:") )
# encap content present?
eci = sd["encap_content_info"]
print("  encap_content_info has content:", "content" in eci and eci["content"] is not None)

# ---- dex ----
print("\n[classes.dex]")
dinfo = z.getinfo("classes.dex")
dex = z.read("classes.dex")
print("  compress:", "STORED" if dinfo.compress_type==0 else "DEFL", "size:", dinfo.file_size)
print("  magic:", dex[:4], "version:", dex[4:8].decode("ascii","replace"))

# ---- manifest AXML (best-effort) ----
print("\n[MANIFEST AXML - first 32 bytes]")
m = z.read("AndroidManifest.xml")
print("  head:", m[:32].hex())
print("  len:", len(m))
# search for known res_ids in LE
import re
for rid, name in [(0x0101021B,"versionCode"),(0x0101021C,"versionName"),
                  (0x0101020C,"minSdkVersion"),(0x0101021D,"targetSdkVersion"),
                  (0x01010000,"package")]:
    idx = m.find(struct.pack("<I", rid))
    if idx >= 0:
        print("  found %s @%d" % (name, idx))
print("DONE")
