#!/usr/bin/env python3
"""Assemble one decoded smali_classesN directory into a standalone dex.

apktool's own `b` refuses to finish because Instagram's resources can never be
recompiled, but it writes the dex files before it reaches that step. Doing it in
a throwaway one-directory project is the same trick without the 20-minute wait
and without the stale-cache problem.

Usage: python assemble_one.py <smali_classesN> <out.dex>
"""
import os
import shutil
import subprocess
import sys

# Windows layout kept as the default; CI overrides via env.
ROOT = os.environ.get("INSTANI_ROOT", r"Z:\hermes\instapro")
JAVA = os.environ.get("JAVA_BIN") or shutil.which("java") or \
    r"Z:\hermes\jdk17\jdk17.0.20_10\bin\java.exe"
APKTOOL = os.environ.get("APKTOOL_JAR") or os.path.join(ROOT, "tools", "apktool.jar")
# Where `apktool d` output lives; CI decompiles into ./decoded (fresh checkout).
SRC = os.environ.get("DECODED_DIR", os.path.join(ROOT, "decoded"))
MANIFEST = ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
            'package="com.instapro.android" android:versionCode="1" android:versionName="1"/>\n')


def assemble(smali_dir, out_dex):
    work = os.path.join(ROOT, "build", "mini_" + smali_dir)
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    shutil.copy2(os.path.join(SRC, "apktool.yml"), os.path.join(work, "apktool.yml"))
    with open(os.path.join(work, "AndroidManifest.xml"), "w", encoding="utf-8") as f:
        f.write(MANIFEST)
    shutil.copytree(os.path.join(SRC, smali_dir), os.path.join(work, smali_dir))
    r = subprocess.run([JAVA, "-Xmx4g", "-jar", APKTOOL, "b", work, "-o",
                        os.path.join(work, "out.apk")],
                       capture_output=True, text=True)
    # apktool names the output after the smali dir (classes3.dex), not classes.dex
    apkg = os.path.join(work, "build", "apk")
    dexes = [f for f in os.listdir(apkg) if f.endswith(".dex")] if os.path.isdir(apkg) else []
    if not dexes:
        print(r.stdout[-3000:], r.stderr[-2000:])
        raise SystemExit(f"assembly failed for {smali_dir}")
    built = os.path.join(apkg, dexes[0])
    errs = [ln for ln in r.stdout.splitlines()
            if "error" in ln.lower() and not ln.startswith("I:")]
    os.makedirs(os.path.dirname(out_dex), exist_ok=True)
    shutil.copy2(built, out_dex)
    print(f"  {smali_dir} -> {out_dex}  ({os.path.getsize(out_dex):,} bytes)"
          + (f"  [{len(errs)} smali warnings]" if errs else ""))
    for e in errs[:5]:
        print("     ", e)


if __name__ == "__main__":
    assemble(sys.argv[1], sys.argv[2])
