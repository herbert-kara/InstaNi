#!/usr/bin/env python3
"""Replace whole showMessage() methods in the mod's DevMsg classes with no-ops.

The earlier targeted insert produced a duplicate .locals directive; replacing
the entire method body avoids that. Also blanks the pastebin URL.
"""
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"Z:\hermes\instapro\decoded\smali_classes20"
# '/' works as a separator on both Windows and Linux; os.path.join normalizes.
FILES = ["com/sammods4h/task/DevMsg.smali",
         "com/apksam/task/DevMsg.smali",
         "com/apksam2/task/DevMsg.smali",
         "com/OM7753/task/DevMsg.smali"]

# the entry points are spelled differently per copy: show(...) and showMessage(...)
METHOD = re.compile(
    r"^\.method[^\n]*\b(?:showMessage|show)\b[^\n]*\n.*?^\.end method\s*$",
    re.M | re.S)


def repl(m):
    decl = m.group(0).split("\n", 1)[0]
    decl = decl.replace(" native ", " ", 1)
    if decl.rstrip().endswith("native"):
        decl = decl.rstrip()[: -len("native")].rstrip()
    return decl + "\n    .locals 0\n\n    return-void\n.end method"


def main():
    for rel in FILES:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            print(f"  MISSING {rel}")
            continue
        txt = open(p, encoding="utf-8", errors="ignore").read()
        new, n = METHOD.subn(repl, txt)
        if n:
            open(p, "w", encoding="utf-8", newline="").write(new)
        note = ""
        if "pastebin" in new:
            new2 = re.sub(r'"https://pastebin\.com[^"]*"', '""', new)
            open(p, "w", encoding="utf-8", newline="").write(new2)
            note = ", pastebin URL blanked"
            new = new2
        print(f"  {rel}: {n} showMessage method(s) replaced{note}")


if __name__ == "__main__":
    main()
