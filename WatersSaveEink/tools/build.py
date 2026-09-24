# -*- coding: utf-8 -*-
import io, os, sys, datetime, hashlib, base64, zipfile
from cryptography.hazmat.primitives.asymmetric import rsa, padding as _pad
from cryptography.hazmat.primitives import hashes
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import asn1crypto.x509 as a_x509
import asn1crypto.cms as a_cms
import asn1crypto.keys as a_keys
import asn1crypto.algos as a_algos
import asn1crypto.core as a_core

EXTRACT = r"D:\workbuddy\2026-09-23-08-21-00\apk_extract"
PATCHED = r"D:\workbuddy\2026-09-23-08-21-00\apk_extract\assets\dashboard.html"
OUT_APK = r"D:\workbuddy\2026-09-23-08-21-00\KDashBoardL_V3.0_757_fixed.apk"
ALIAS   = "CERT"

def b64(b): return base64.b64encode(b).decode("ascii")

# ---------- 1. collect entries from extracted tree (skip old META-INF) ----------
# 源码 APK(E:\) 已不可访问，改为从解包目录 apk_extract 收集，字节级等价于原包。
entries = []
for dp, dn, fn in os.walk(EXTRACT):
    for f in fn:
        full = os.path.join(dp, f)
        rel = os.path.relpath(full, EXTRACT).replace("\\", "/")
        if rel.startswith("META-INF/"):
            continue
        if rel.endswith(".bak"):
            continue   # 不把本地备份打包进 APK
        with io.open(full, "rb") as fh:
            data = fh.read()
        if rel == "assets/dashboard.html":
            with io.open(PATCHED, "rb") as fh:
                data = fh.read()   # 始终用补丁后的版本
        entries.append((rel, data))
entries.sort(key=lambda e: e[0])
print("collected %d entries (patched dashboard=%d bytes)" % (len(entries), len(dict(entries).get("assets/dashboard.html", b""))))

# ---------- 2. build MANIFEST.MF ----------
manifest_parts = ["Manifest-Version: 1.0\r\n", "\r\n"]
sf_blocks = {}
for nm, data in entries:
    if nm.endswith("/"):
        continue
    d = hashlib.sha1(data).digest()
    block = "Name: %s\r\nSHA1-Digest: %s\r\n\r\n" % (nm, b64(d))
    manifest_parts.append(block)
    sf_blocks[nm] = block.encode("utf-8")
manifest_bytes = "".join(manifest_parts).encode("utf-8")

# ---------- 3. build CERT.SF ----------
sf_parts = ["Signature-Version: 1.0\r\n",
            "Created-By: KDashBoardL-Patcher\r\n",
            "SHA1-Digest-Manifest: %s\r\n" % b64(hashlib.sha1(manifest_bytes).digest()),
            "\r\n"]
for nm, block in sf_blocks.items():
    sd = hashlib.sha1(block).digest()
    sf_parts.append("Name: %s\r\nSHA1-Digest: %s\r\n\r\n" % (nm, b64(sd)))
sf_bytes = "".join(sf_parts).encode("utf-8")

# ---------- 4. key + self-signed cert (SHA1) ----------
# cryptography>=43 blocks SHA1 for CertificateBuilder.sign(), but Android 4.0's v1
# verifier requires a SHA1 (not SHA-256) cert/signature chain. So we build the
# self-signed cert manually with asn1crypto and sign the TBSCertificate with SHA1.
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
now = datetime.datetime.utcnow()
spki_der = key.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
pki = a_keys.PublicKeyInfo.load(spki_der)

def _utc(dt):
    return a_core.UTCTime(dt.strftime("%y%m%d%H%M%SZ"))

def _build_name():
    return a_x509.Name().build({
        "common_name": u"KDashBoardL Build",
        "organization_name": u"KDashBoardL",
    })

name = _build_name()
tbs = a_x509.TbsCertificate()
tbs["version"] = 2  # v3
tbs["serial_number"] = a_core.Integer(0x4B44415348)  # "KDASH"
tbs["signature"] = a_algos.SignedDigestAlgorithm({"algorithm": "sha1_rsa"})
tbs["issuer"] = name
tbs["validity"] = a_x509.Validity({
    "not_before": a_x509.Time(name="utc_time", value=_utc(now - datetime.timedelta(days=2))),
    "not_after":  a_x509.Time(name="utc_time", value=_utc(now + datetime.timedelta(days=3650))),
})
tbs["subject"] = name
tbs["subject_public_key_info"] = pki
bc = a_x509.BasicConstraints({"ca": True})
ext = a_x509.Extension({
    "extn_id": a_x509.ExtensionId("2.5.29.19"),
    "critical": True,
    "extn_value": bc,
})
tbs["extensions"] = a_x509.Extensions([ext])

tbs_der = tbs.dump()
sig = key.sign(tbs_der, _pad.PKCS1v15(), hashes.SHA1())
# asn1crypto BitString needs a tuple of 0/1 bits (not raw bytes)
_sig_bits = tuple((sig[i // 8] >> (7 - (i % 8))) & 1 for i in range(len(sig) * 8))
cert = a_x509.Certificate()
cert["tbs_certificate"] = tbs
cert["signature_algorithm"] = a_algos.SignedDigestAlgorithm({"algorithm": "sha1_rsa"})
cert["signature_value"] = a_core.OctetBitString(sig)
cert_der = cert.dump()
acert = a_x509.Certificate.load(cert_der)

# ---------- 5. build PKCS#7 SignedData (v1 JAR signature) ----------
content_digest = hashlib.sha1(sf_bytes).digest()
sa = a_cms.CMSAttributes()
sa.append(a_cms.CMSAttribute({"type": "content_type", "values": ["data"]}))
sa.append(a_cms.CMSAttribute({"type": "message_digest", "values": [content_digest]}))

signer = a_cms.SignerInfo()
signer["version"] = 1
signer["sid"] = a_cms.IssuerAndSerialNumber({"issuer": acert.issuer, "serial_number": acert.serial_number})
signer["digest_algorithm"] = a_cms.DigestAlgorithm({"algorithm": "sha1"})
signer["signed_attrs"] = sa   # embedded field uses [0] IMPLICIT (0xA0) - correct for the structure
signer["signature_algorithm"] = a_cms.SignedDigestAlgorithm({"algorithm": "sha1_rsa"})
signer["signature"] = b"\x00" * 256   # placeholder; spliced in-place after signing

sd = a_cms.SignedData()
sd["version"] = 1
sd["digest_algorithms"] = a_cms.DigestAlgorithms([a_cms.DigestAlgorithm({"algorithm": "sha1"})])
sd["encap_content_info"] = a_cms.ContentInfo({"content_type": "data", "content": sf_bytes})
sd["certificates"] = a_cms.CertificateSet([acert])
sd["signer_infos"] = a_cms.SignerInfos([signer])
ci = a_cms.ContentInfo({"content_type": "signed_data", "content": sd})
cms_der = ci.dump()

# In-place patch: the signature in PKCS#7 v1 MUST be computed over the DER *SET* form
# (tag 0x31) of signed_attrs, while the embedded field uses the [0] IMPLICIT form (0xA0).
# asn1crypto always re-encodes signed_attrs as 0xA0, so we sign the 0x31 form explicitly.
sa_for_sign = b"\x31" + sa.dump()[1:]   # sa.dump() is 0xA0 (implicit); SET tag is 0x31
sig = key.sign(sa_for_sign, _pad.PKCS1v15(), hashes.SHA1())

# splice the real signature into the exact placeholder OCTET STRING slot
ph = b"\x04\x82\x01\x00" + b"\x00" * 256   # OCTET STRING, 256-byte content, all zeros
assert cms_der.count(ph) == 1, "placeholder signature not unique (count=%d)" % cms_der.count(ph)
cms_der = cms_der.replace(ph, b"\x04\x82\x01\x00" + sig)
print("CERT.RSA length:", len(cms_der))

# ---------- 6. write APK (STORED, 4-byte zipaligned, v1 signed) ----------
import struct, zlib
ALIGN = 4  # Android ICS requires every STORED entry's data to start on a 4-byte boundary

def _zipalign_write(path, items):
    """Write a valid ZIP where each entry's data begins at a 4-byte boundary.
    items: list of (name, data_bytes)."""
    buf = bytearray()
    central = []
    for nm, data in items:
        name_b = nm.encode("utf-8")
        lho = len(buf)                       # local header offset == current file offset
        base = lho + 30 + len(name_b)
        extra_len = (ALIGN - (base % ALIGN)) % ALIGN
        extra = b"\x00" * extra_len
        crc = zlib.crc32(data) & 0xffffffff
        flag = 0x0800                        # UTF-8 filename flag (names are ASCII anyway)
        # local file header
        buf += struct.pack("<IHHHHHIIIHH", 0x04034b50, 20, flag, 0,
                            0, 0, crc, len(data), len(data),
                            len(name_b), len(extra))
        buf += name_b + extra + data
        central.append(struct.pack("<IHHHHHHIIIHHHHHII",
            0x02014b50, 20, 20, flag, 0, 0, 0, crc,
            len(data), len(data), len(name_b), len(extra),
            0, 0, 0, 0, lho) + name_b + extra)
    cd_start = len(buf)
    for c in central:
        buf += c
    cd_size = len(buf) - cd_start
    buf += struct.pack("<IHHHHIIH", 0x06054b50, 0, 0,
                       len(items), len(items), cd_size, cd_start, 0)
    with open(path, "wb") as f:
        f.write(buf)

items = list(entries) + [
    ("META-INF/MANIFEST.MF", manifest_bytes),
    ("META-INF/%s.SF" % ALIAS, sf_bytes),
    ("META-INF/%s.RSA" % ALIAS, cms_der),
]
_zipalign_write(OUT_APK, items)
print("wrote (zipaligned)", OUT_APK, os.path.getsize(OUT_APK), "bytes")

# self-check: every STORED entry's data offset must be 4-aligned (Android ICS rule)
with open(OUT_APK, "rb") as f:
    raw = f.read()
mis = 0
with zipfile.ZipFile(OUT_APK) as z:
    for zi in z.infolist():
        if zi.compress_type == 0:  # STORED (only these are alignment-checked by Android)
            # extra length lives at local-header offset +28 (2 bytes)
            extra_len = struct.unpack("<H", raw[zi.header_offset+28:zi.header_offset+30])[0]
            off = zi.header_offset + 30 + len(zi.filename) + extra_len
            if off % ALIGN != 0:
                mis += 1
                print("MISALIGNED:", zi.filename, "offset", off)
print("zipalign check: %s" % ("OK (all STORED entries 4-aligned)" if mis == 0 else "%d misaligned" % mis))

# ---------- 7. local verification ----------
ok = True
with zipfile.ZipFile(OUT_APK) as z:
    m = z.read("META-INF/MANIFEST.MF")
    assert m == manifest_bytes, "MANIFEST mismatch"
    lines = m.decode("utf-8").split("\r\n")
    for nm, data in entries:
        if nm.endswith("/"):
            continue
        exp = b64(hashlib.sha1(data).digest())
        for i, l in enumerate(lines):
            if l == "Name: %s" % nm:
                dd = lines[i+1].split("SHA1-Digest: ")[1].strip()
                if dd != exp:
                    print("DIGEST FAIL", nm); ok = False
print("manifest digests:", "OK" if ok else "FAIL")

# verify PKCS#7: re-parse, extract embedded signed_attrs (0xA0 form), convert to 0x31 for verify
ci2 = a_cms.ContentInfo.load(cms_der)
sd2 = ci2["content"]
sg = sd2["signer_infos"][0]
attrs = sg["signed_attrs"]
embedded_a0 = attrs.dump()              # embedded [0] IMPLICIT form
md = None
for at in attrs:
    oid = str(at["type"])
    if oid == "1.2.840.113549.1.9.4":    # message_digest
        md = bytes(at["values"][0])
sig_ok = (md == content_digest)
print("message_digest match:", sig_ok)
# signature was computed over the SET (0x31) form; verify over the same
verify_input = b"\x31" + embedded_a0[1:]
try:
    key.public_key().verify(bytes(sg["signature"]), verify_input, _pad.PKCS1v15(), hashes.SHA1())
    sig_verify = True
    print("signature verifies: True")
except Exception as e:
    sig_verify = False
    print("signature verifies: False ->", repr(e))
print("RESULT:", "ALL GOOD" if (ok and sig_ok and sig_verify) else "PROBLEM")
