#!/usr/bin/env python3
"""Splice reassembled dex files into a copy of the original APK, align, sign.

Usage: python build_apk.py out.apk classes20.dex=build/classes20.dex [more...]
If no dex pairs given, just re-signs a copy of the original (pipeline test).
"""
import os, sys, zipfile, shutil, subprocess, hashlib

# Windows layout kept as the default; CI overrides via env.
ROOT = os.environ.get("INSTANI_ROOT", r"Z:\hermes\instapro")
ORIG = os.environ.get("ORIG_APK", os.path.join(ROOT, "instapro-15.65.apk"))
BUILD = os.path.join(ROOT, "build")
TOOLS = os.path.join(ROOT, "tools")
SDK = os.environ.get("ANDROID_HOME", r"Z:\hermes\android-sdk")
# CI runners ship their own build-tools (detected in the workflow); local keeps 36.1.0.
BT = os.environ.get("BT_DIR") or os.path.join(SDK, "build-tools", "36.1.0")
JDK = os.environ.get("JDK_BIN", r"Z:\hermes\jdk17\jdk17.0.20_10\bin")
# The mod validates the APK's own signing certificate in native code, so a
# re-signed build refuses to run. The original was signed with AOSP's published
# *test* key (CN=Android, O=Android, EMAILADDRESS=android@android.com,
# SHA1 61:ED:37:...:AF:81); signing with the same public key makes our
# certificate byte-identical to the original. Set APKSIGN_KS to override.
KS = os.environ.get("APKSIGN_KS", os.path.join(TOOLS, "instapro.jks"))
KS_TYPE = os.environ.get("APKSIGN_KS_TYPE", "")
ALIAS = os.environ.get("APKSIGN_ALIAS", "instapro")
PASSWORD = os.environ.get("APKSIGN_PASS", "instapro")


def splice(out_apk, replacements, drops=()):
    """replacements: dict {entry_name: local_path}. drops: entry names to omit."""
    if os.path.exists(out_apk):
        os.remove(out_apk)
    zin = zipfile.ZipFile(ORIG, "r")
    zout = zipfile.ZipFile(out_apk, "w", zipfile.ZIP_DEFLATED, compresslevel=6)
    replaced, dropped = set(), set()
    for item in zin.infolist():
        if item.filename in drops:
            dropped.add(item.filename)
            continue
        if item.filename in replacements:
            data = open(replacements[item.filename], "rb").read()
            replaced.add(item.filename)
        else:
            data = zin.read(item.filename)
        zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
        zi.compress_type = item.compress_type
        zi.external_attr = item.external_attr
        zi.internal_attr = item.internal_attr
        zi.create_system = item.create_system
        zout.writestr(zi, data)
    zout.close()
    zin.close()
    missing = set(replacements) - replaced
    return missing


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "instapro-patched.apk")
    reps, drops = {}, set()
    for a in sys.argv[2:]:
        if a.startswith("!"):
            drops.add(a[1:])
        else:
            entry, path = a.split("=", 1)
            reps[entry] = path.rstrip("\r")  # tolerate CRLF in arg strings
    os.makedirs(os.path.dirname(out), exist_ok=True)

    missing = splice(out, reps, drops)
    if missing:
        print("!! entries not found in APK:", missing)
    if drops:
        print(f"dropped {len(drops)} entries: {', '.join(sorted(drops))}")

    aligned = out + ".aligned"
    if os.path.exists(aligned):
        os.remove(aligned)
    env = dict(os.environ)
    # Local Windows build: put the bundled JDK on PATH. On CI, setup-java
    # already provides java + JAVA_HOME.
    if os.path.isdir(JDK):
        env["PATH"] = JDK + os.pathsep + env.get("PATH", "")
        env["JAVA_HOME"] = os.path.dirname(JDK)

    def tool(name):
        # Windows distro ships name.exe / name.bat, Linux ships a bare name.
        for cand in (name, name + ".exe", name + ".bat"):
            p = os.path.join(BT, cand)
            if os.path.exists(p):
                return p
        return os.path.join(BT, name)

    r = subprocess.run([tool("zipalign"), "-p", "-f", "4", out, aligned],
                       capture_output=True, text=True, env=env)
    if r.returncode:
        print("zipalign FAILED:", r.stdout, r.stderr)
        return 1
    print("zipalign ok")

    sign = [tool("apksigner"), "sign",
            "--ks", KS, "--ks-key-alias", ALIAS, "--ks-pass", f"pass:{PASSWORD}",
            "--key-pass", f"pass:{PASSWORD}", "--v1-signing-enabled", "true",
            "--v2-signing-enabled", "true", "--v3-signing-enabled", "true",
            "--out", out, aligned]
    if KS_TYPE:
        sign[2:2] = ["--ks-type", KS_TYPE]
    r = subprocess.run(sign, capture_output=True, text=True, env=env)
    if r.returncode:
        print("apksigner FAILED:", r.stdout, r.stderr)
        return 1
    print("sign ok")
    os.remove(aligned)

    r = subprocess.run([tool("apksigner"), "verify", "--print-certs", out],
                       capture_output=True, text=True, env=env)
    print(r.stdout.strip()[:600] or r.stderr.strip()[:600])
    h = hashlib.sha256(open(out, "rb").read()).hexdigest()
    print(f"SIZE {os.path.getsize(out)/1e6:.1f} MB   SHA256 {h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
