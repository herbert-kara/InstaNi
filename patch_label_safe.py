#!/usr/bin/env python3
"""Rename the app in resources.arsc WITHOUT changing the file's structure.

The usual approach (shorten the string, then re-pad the pool) corrupts the
string pool: later string offsets and the following chunk both shift, and while
aapt2 tolerates the result, Instagram's own resource loading at runtime does
not -- the app dies on launch.

So: keep the string exactly the same byte length and overwrite it in place.
Only the two length fields and the bytes themselves change; every offset, every
chunk size and the table header stay bit-identical.

Usage: python patch_label_safe.py <in.arsc> <out.arsc> <old> <new>
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
    raise SystemExit("no string pool found")


def main(src, dst, old, new):
    buf = bytearray(open(src, "rb").read())
    pos = find_pool(buf)
    (_t, _h, _size, sCount, _sc, flags, sStart, _ss) = struct.unpack_from(
        "<HHIIIIII", buf, pos)
    if not flags & (1 << 8):
        raise SystemExit("pool is UTF-16; this patcher only handles UTF-8 pools")
    data = pos + sStart
    old_b, new_b = old.encode("utf-8"), new.encode("utf-8")
    if len(new_b) != len(old_b):
        raise SystemExit(f"length must match exactly: {len(old_b)} vs {len(new_b)} "
                         f"(pad the new name with spaces to {len(old_b)} bytes)")

    patched = 0
    for i in range(sCount):
        o = struct.unpack_from("<I", buf, pos + 28 + 4 * i)[0]
        at = data + o
        p2 = at
        n = buf[p2]; p2 += 1
        if n & 0x80:
            p2 += 1
        ln = buf[p2]; p2 += 1
        if ln & 0x80:
            ln = ((ln & 0x7F) << 8) | buf[p2]; p2 += 1
        if bytes(buf[p2:p2 + ln]) == old_b:
            n_new = len(new)                       # UTF-16 units
            assert n_new < 0x80 and ln < 0x80, "patcher assumes 1-byte length fields"
            buf[at] = n_new
            buf[p2 - 1] = len(new_b)
            buf[p2:p2 + ln] = new_b
            print(f"  string #{i} @ {at}: {old!r} -> {new!r}  "
                  f"(utf16 {n}->{n_new}, utf8 {ln}->{len(new_b)})")
            patched += 1

    if not patched:
        raise SystemExit(f"string {old!r} not found in the pool")
    open(dst, "wb").write(bytes(buf))
    print(f"  wrote {dst} ({len(buf)} bytes, {patched} string(s) patched, "
          f"structure unchanged)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
