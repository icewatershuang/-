# -*- coding: utf-8 -*-
# Independent v1 (JAR) signature verification, parsed entirely from the on-disk APK.
# Uses SHA1 (Android 4.0 compatible).
import io, base64, hashlib, zipfile
from cryptography.hazmat.primitives.asymmetric import padding as _pad
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography import x509
import asn1crypto.x509 as a_x509
import asn1crypto.cms as a_cms

OUT_APK = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.0_757_fixed.apk"
ALIAS = "CERT"
def b64(b): return base64.b64encode(b).decode("ascii")

with zipfile.ZipFile(OUT_APK) as z:
    names = z.namelist()
    manifest = z.read("META-INF/MANIFEST.MF").decode("utf-8")
    sf = z.read("META-INF/%s.SF" % ALIAS).decode("utf-8")
    rsa = z.read("META-INF/%s.RSA" % ALIAS)
    entry_data = {n: z.read(n) for n in names if not n.startswith("META-INF/")}

print("== 1. MANIFEST per-entry digests (SHA1) ==")
mblocks = {}
mlines = manifest.split("\r\n")
i = 0
while i < len(mlines):
    if mlines[i].startswith("Name: "):
        nm = mlines[i][6:].strip()
        dg = mlines[i+1].split("SHA1-Digest: ")[1].strip()
        mblocks[nm] = dg
        i += 2
    else:
        i += 1
bad = 0
for nm, data in entry_data.items():
    exp = b64(hashlib.sha1(data).digest())
    if mblocks.get(nm) != exp:
        print("  FAIL", nm); bad += 1
print("  entries checked:", len(entry_data), "| failures:", bad)

print("== 2. CERT.SF digests vs MANIFEST blocks (SHA1) ==")
sblocks = {}
slines = sf.split("\r\n")
i = 0
digest_manifest = None
while i < len(slines):
    if slines[i].startswith("SHA1-Digest-Manifest:"):
        digest_manifest = slines[i].split(": ")[1].strip()
    if slines[i].startswith("Name: "):
        nm = slines[i][6:].strip()
        dg = slines[i+1].split("SHA1-Digest: ")[1].strip()
        sblocks[nm] = dg
        i += 2
    else:
        i += 1
manifest_bytes = manifest.encode("utf-8")
sfdm_ok = (digest_manifest == b64(hashlib.sha1(manifest_bytes).digest()))
print("  Digest-Manifest OK:", sfdm_ok)
sfail = 0
for nm, dg in sblocks.items():
    if nm in mblocks:
        block = ("Name: %s\r\nSHA1-Digest: %s\r\n\r\n" % (nm, mblocks[nm])).encode("utf-8")
        if b64(hashlib.sha1(block).digest()) != dg:
            print("  FAIL block", nm); sfail += 1
print("  SF per-block failures:", sfail)

print("== 3. PKCS#7 RSA signature (SHA1) ==")
ci = a_cms.ContentInfo.load(rsa)
sd = ci["content"]
sg = sd["signer_infos"][0]
attrs = sg["signed_attrs"]
cert_der = bytes(sd["certificates"][0].dump())
c = x509.load_der_x509_certificate(cert_der)
pub = c.public_key()
embedded_a0 = attrs.dump()
verify_input = b"\x31" + embedded_a0[1:]
md = None
for at in attrs:
    if str(at["type"]) == "1.2.840.113549.1.9.4":
        md = bytes(at["values"][0])
sf_bytes_check = sf.encode("utf-8")
print("  cert subject:", c.subject.rfc4514_string())
print("  message_digest attr == SHA1(.SF):", md == hashlib.sha1(sf_bytes_check).digest())
try:
    pub.verify(bytes(sg["signature"]), verify_input, _pad.PKCS1v15(), hashes.SHA1())
    print("  signature verifies: True")
    sig_ok = True
except Exception as e:
    print("  signature verifies: False ->", repr(e))
    sig_ok = False

print("== 4. cert self-signature (SHA1) ==")
ci = a_cms.ContentInfo.load(rsa)
sd = ci["content"]
from cryptography.hazmat.primitives.asymmetric import rsa as _rsa
cert_der2 = bytes(sd["certificates"][0].dump())
c2 = x509.load_der_x509_certificate(cert_der2)
pub2 = c2.public_key()
print("  cert signature_algorithm:", c2.signature_hash_algorithm.name if c2.signature_hash_algorithm else "?")
try:
    pub2.verify(c2.signature, c2.tbs_certificate_bytes, _pad.PKCS1v15(), hashes.SHA1())
    print("  cert self-signature verifies: True")
    cert_ok = True
except Exception as e:
    print("  cert self-signature verifies: False ->", repr(e))
    cert_ok = False
print("  PKCS#7 digest_algorithm:", str(sg["digest_algorithm"].native))
print("  PKCS#7 signature_algorithm:", str(sg["signature_algorithm"].native))

print("RESULT:", "ALL GOOD" if (bad == 0 and sfdm_ok and sfail == 0 and sig_ok and md == hashlib.sha1(sf_bytes_check).digest() and cert_ok) else "PROBLEM")
