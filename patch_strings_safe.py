#!/usr/bin/env python3
"""Rewrite every visible "InstaPro" string in resources.arsc to "InstaNi".

Length-preserving: each replacement is padded with trailing spaces to the exact
byte length of the original, so the string pool keeps its layout — no offsets
move, no padding is inserted, no chunk header changes. Patching the pool with a
shorter string and re-padding is what corrupted earlier builds.

Usage: python patch_strings_safe.py <in.arsc> <out.arsc> ["Old=New", ...]
"""
import struct
import sys


def find_pool(buf):
    off = 12
    while off < len(buf):
        t, h, size = struct.unpack_from("<HHI", buf, off)
        if t == 0x0001:
            return off
        off += 8 + size
    raise SystemExit("no string pool in chunk list")


def read_pool(buf, pos):
    (_t, _h, _sz, count, _sc, flags, sStart, _ss) = struct.unpack_from("<HHIIIIII", buf, pos)
    return count, flags, pos + sStart, pos + 28


def read_str(buf, data, styles, idx, flags):
    o = struct.unpack_from("<I", buf, styles + 4 * idx)[0]
    at = data + o
    if flags & (1 << 8):  # UTF-8
        q = at
        n = buf[q]; q += 2 if n & 0x80 else 1
        ln = buf[q]; q += 1
        if ln & 0x80:
            ln = ((ln & 0x7F) << 8) | buf[q]; q += 1
        return q, ln, True
    ln = struct.unpack_from("<H", buf, at)[0]
    return at + 2, ln, False


def patch(src, dst, pairs):
    buf = bytearray(open(src, "rb").read())
    pos = find_pool(buf)
    count, flags, data, styles = read_pool(buf, pos)
    done = []
    for old, new in pairs:
        hits = 0
        for i in range(count):
            b_off, ln, utf8 = read_str(buf, data, styles, i, flags)
            raw = bytes(buf[b_off:b_off + ln])
            try:
                cur = raw.decode("utf-8" if utf8 else "utf-16-le")
            except Exception:
                continue
            if cur != old:
                continue
            nb = new.encode("utf-8" if utf8 else "utf-16-le")
            if len(nb) > ln:
                raise SystemExit(f"replacement longer than original: {old!r} -> {new!r}")
            nb = nb + b" " * (ln - len(nb))          # pad, never resize
            buf[b_off:b_off + ln] = nb
            hits += 1
        if hits:
            done.append((old, new, hits))
        else:
            print(f"  !! not found: {old!r}")
    open(dst, "wb").write(buf)
    return done


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    pairs = []
    for arg in sys.argv[3:]:
        old, new = arg.split("=", 1)
        pairs.append((old, new))
    for old, new, n in patch(src, dst, pairs):
        print(f"  {n:3d}x  {old!r} -> {new!r}")
    print(f"  wrote {dst}")
