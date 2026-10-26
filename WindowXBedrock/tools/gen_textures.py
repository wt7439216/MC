# -*- coding: utf-8 -*-
"""生成最小 UI 贴图（纯色 RGBA PNG，九宫格友好），避免依赖美术资源。

输出: resource_packs/windowxResource/textures/ui/windowx/*.png
"""
from __future__ import print_function

import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
OUT_DIR = os.path.join(PROJECT, 'resource_packs', 'windowxResource', 'textures', 'ui', 'windowx')

SIZE = 16

TEXTURES = {
    'bg':        (0x12, 0x16, 0x1C, 0xE6),
    'titlebar':  (0x1E, 0x2A, 0x38, 0xFF),
    'content':   (0x0A, 0x0E, 0x13, 0xFF),
    'shadow':    (0x00, 0x00, 0x00, 0x66),
    'btn':       (0x2A, 0x36, 0x46, 0xFF),
}


def _chunk(tag, data):
    return (struct.pack('>I', len(data)) + tag + data +
            struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png(path, w, h, rgba):
    row = bytearray()
    for _ in range(w):
        row.extend(rgba)
    raw = b''.join(b'\x00' + bytes(row) for _ in range(h))
    png = b'\x89PNG\r\n\x1a\n'
    png += _chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
    png += _chunk(b'IDAT', zlib.compress(raw, 9))
    png += _chunk(b'IEND', b'')
    fh = open(path, 'wb')
    try:
        fh.write(png)
    finally:
        fh.close()


def main():
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    for name, rgba in TEXTURES.items():
        path = os.path.join(OUT_DIR, name + '.png')
        write_png(path, SIZE, SIZE, rgba)
        print('[OK]', path, os.path.getsize(path), 'bytes')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
