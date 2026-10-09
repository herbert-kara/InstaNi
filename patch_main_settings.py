#!/usr/bin/env python3
"""Patch InstaNi branding into a binary AXML settings menu (any version).

Length-preserving in-place edits (padding), so the string pool layout never
moves. Rules are pattern-based, so a fresh InstaPro release with a new version
number and/or a shuffled pool is handled without touching indices:

  * any string starting with 'InstaPro '  -> same prefix changed to 'InstaNi '
  * a pool entry equal to the promo label
    '\U0001d403\U0001d40e\U0001d426\U0001d42f\U0001d41b\U0001d430\U0001d402...'  -> blanked
    (the 'Download YouTube Pro' ad; matched by the leading Douwnload-emoji run
    so it survives repacking)

Usage: python patch_main_settings.py <in.xml> <out.xml>
"""
import sys
import axml_edit as ax


def is_promo(s):
    # '𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝 𝐘𝐨𝐮𝐓𝐮𝐛𝐞 𝐏𝐫𝐨 👑' — mathematical-bold (non-ASCII) letters + crown.
    # Matched by the crown emoji tail so it survives repacking that reorders the pool.
    return s.endswith(" 👑") and len(s) > 15 and any(ord(c) > 0x1D400 for c in s)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    buf = bytearray(open(src, "rb").read())
    pool, _ = ax.parse(buf)
    hits = []
    for i in range(pool.count):
        s = pool.string(i)
        if s is None:
            continue
        if s.startswith("InstaPro"):
            # 'InstaPro ♛ V15.85' -> 'InstaNi V15.85' (drop the crown, keep spacing)
            rem = s[len("InstaPro"):]
            if rem.startswith(" ♛"):
                rem = rem[3:]
            new = "InstaNi " + rem
            pool.set_string(i, new)
            hits.append(("title", s, new))
        elif is_promo(s):
            pool.set_string(i, "")
            hits.append(("promo", s, ""))
    open(dst, "wb").write(buf)
    for kind, a, b in hits:
        print(f"  {kind}: {a!r} -> {b!r}")
    print(f"  wrote {dst} ({len(hits)} edits)")


if __name__ == "__main__":
    main()
