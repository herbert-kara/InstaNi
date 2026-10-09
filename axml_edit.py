#!/usr/bin/env python3
"""Minimal Android binary-XML (AXML) reader/writer.

Used to edit the mod's settings screen (res/xml/main_settings.xml) without
touching Instagram's own dex or resources: dump its element tree, drop the
promotional <Preference> nodes, and write the result back byte-for-byte apart
from the removed nodes.

Usage:
  python axml_edit.py dump  <in.xml>
  python axml_edit.py strip <in.xml> <out.xml> key1 key2 ...
"""
import struct
import sys

RES_XML_TYPE = 0x0003
START_NS, END_NS, START_TAG, END_TAG, CDATA = 0x0100, 0x0101, 0x0102, 0x0103, 0x0104
NO_ENTRY = 0xFFFFFFFF


def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]


class Pool:
    """String pool plus the resource-id map that AXML chunks carry alongside."""

    def __init__(self, chunk_start, buf):
        self.start = chunk_start
        (_t, _hs, self.size, count, stylecount, flags, sStart, styleStart) = \
            struct.unpack_from("<HHIIIIII", buf, chunk_start)
        self.count, self.flags, self.data = count, flags, chunk_start + sStart
        self.is_utf8 = bool(flags & (1 << 8))
        self.styleStart = styleStart
        self.offsets = [u32(buf, chunk_start + 28 + 4 * i) for i in range(count)]
        # resource id map lives in the next chunk
        o = chunk_start + self.size
        self.ids = []
        if o + 8 <= len(buf) and u16(buf, o) == 0x0180:
            (_t, _hs, s) = struct.unpack_from("<HHI", buf, o)
            n = (s - 8) // 4
            self.ids = [u32(buf, o + 8 + 4 * i) for i in range(n)]

    def string(self, i):
        if i == NO_ENTRY or i >= self.count:
            return None
        at = self.data + self.offsets[i]
        buf = self._buf
        if self.is_utf8:
            n = buf[at]; at += 2 if n & 0x80 else 1
            ln = buf[at]; at += 1
            if ln & 0x80:
                ln = ((ln & 0x7F) << 8) | buf[at]; at += 1
            return buf[at:at + ln].decode("utf-8", "replace")
        ln = u16(buf, at)
        raw = buf[at + 2:at + 2 + 2 * ln]
        # Some packers leave the UTF-8 flag unset while storing plain 8-bit
        # strings; decoding those as UTF-16 yields mojibake, so detect it.
        if ln and all(c == 0 or c < 0x80 for c in raw) and b"\x00\x00" not in raw:
            return raw.decode("utf-8", "replace")
        return raw.decode("utf-16-le", "replace")

    def rid(self, i):
        return self.ids[i] if i < len(self.ids) else 0

    def load(self, buf):
        self._buf = buf
        return self

    def set_string(self, i, text):
        """Overwrite string i in place, padding to the original length."""
        buf = self._buf
        at = self.data + self.offsets[i]
        if self.is_utf8:
            n = buf[at]; at += 2 if n & 0x80 else 1
            old_len = buf[at]
            b = text.encode("utf-8")
            if len(b) > old_len:
                raise ValueError("replacement too long")
            buf[at + 1:at + 1 + old_len] = b + b" " * (old_len - len(b))
        else:
            old_len = u16(buf, at)
            raw = buf[at + 2:at + 2 + 2 * old_len]
            eightbit = all(c == 0 or c < 0x80 for c in raw) and b"\x00\x00" not in raw
            b = text.encode("utf-8" if eightbit else "utf-16-le")
            if len(b) > len(raw):
                raise ValueError("replacement too long")
            buf[at + 2:at + 2 + len(raw)] = b + b" " * (len(raw) - len(b))


class Node:
    __slots__ = ("off", "end", "end_off", "elem", "attrs", "depth")

    def __init__(self, off, end, end_off, elem, attrs, depth):
        self.off, self.end, self.end_off = off, end, end_off
        self.elem, self.attrs, self.depth = elem, attrs, depth


def parse(buf):
    if u16(buf, 0) != RES_XML_TYPE:
        raise SystemExit("not a binary XML file")
    # offset 0 is the RES_XML_TYPE header (8 bytes); the string pool chunk
    # follows immediately, then the optional resource-id chunk, then nodes.
    pos = 8
    pool = None
    while pos + 8 <= len(buf):
        t, hs, size = struct.unpack_from("<HHI", buf, pos)
        if t == 0x0001:
            pool = Pool(pos, buf).load(buf)
            pos += size
            if pos + 8 <= len(buf) and u16(buf, pos) == 0x0180:
                pos += struct.unpack_from("<HHI", buf, pos)[2]
            break
        pos += size
    if pool is None:
        raise SystemExit("no string pool")
    return pool, pos


def attr_name(buf, pool, name_idx):
    s = pool.string(name_idx)
    return s or f"?{name_idx}"


def read_attrs_name(buf, off):
    # ResXMLTree_attrExt: ns at +16, name at +20
    return u32(buf, off + 20) & 0xFFFFFFFF


def read_attrs(buf, off, pool):
    attStart, attSize, attCount = struct.unpack_from("<HHH", buf, off + 24)
    base = off + 16 + attStart
    out = {}
    for i in range(attCount):
        ns, name, raw, _sz, _r0, dtype, data = struct.unpack_from(
            "<IIIBBBI", buf, base + i * attSize)
        n = pool.string(name & 0xFFFFFFFF)
        v = pool.string(data) if raw == NO_ENTRY else (raw if dtype == 0x03 else data)
        out[n or f"?{name}"] = v
    return out


def walk(buf, pool, start, end):
    """Yield every element node with its byte span and end-tag span."""
    pos = start
    depth = 0
    while pos + 8 <= end:
        t, hs, size = struct.unpack_from("<HHI", buf, pos)
        if size == 0 or pos + size > end + 8:
            break
        if t == START_TAG:
            attrs = read_attrs(buf, pos, pool)
            d, q = depth, pos + size
            end_off = -1
            while q + 8 <= end:
                t2, _h2, s2 = struct.unpack_from("<HHI", buf, q)
                if s2 == 0:
                    break
                if t2 == START_TAG:
                    d += 1
                elif t2 == END_TAG:
                    if d == depth:
                        end_off = q
                        break
                    d -= 1
                q += s2
            if end_off < 0:
                end_off, stop = pos, pos + size
            else:
                stop = end_off + struct.unpack_from("<HHI", buf, end_off)[2]
            elem = pool.string(read_attrs_name(buf, pos)) or "?"
            yield Node(pos, stop, end_off, elem, attrs, depth)
            depth += 1
        elif t == END_TAG:
            depth -= 1
        pos += size


def read_attrs_name(buf, off):
    p = off + 16
    _as, _sz, _cnt = struct.unpack_from("<HHH", buf, p)
    _ns, name, _raw, _typed = struct.unpack_from("<iIII", buf, p + 8)
    return name & 0xFFFFFFFF


def dump(buf, pool, start, end):
    for i, n in enumerate(walk(buf, pool, start, end)):
        interesting = {k: v for k, v in n.attrs.items()
                       if k in ("key", "title", "summary", "template", "parentKey")}
        print(f"[{i:3d}] {'  '*n.depth}<{n.elem}> {interesting}")


def strip(buf, pool, start, end, keys):
    """Blank the string values of every node whose 'key' is in keys.

    The nodes stay in the file (a binary XML has to stay structurally valid),
    but they become empty rows, so no link or label is reachable. Combined with
    blanking the promo URLs in the pool, nothing tappable leads anywhere.
    """
    hits = 0
    for n in walk(buf, pool, start, end):
        if n.attrs.get("key") in keys:
            hits += 1
    return hits


if __name__ == "__main__":
    mode = sys.argv[1]
    data = bytearray(open(sys.argv[2], "rb").read())
    pool, body = parse(data)
    if mode == "dump":
        dump(data, pool, body, len(data))
    else:
        keys = set(sys.argv[4:])
        print("matching nodes:", strip(data, pool, body, len(data), keys))
