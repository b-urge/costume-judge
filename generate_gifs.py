#!/usr/bin/env python3
"""Generate self-contained pixel-art animated GIF decorations."""
from pathlib import Path

OUT = Path(__file__).parent / 'static' / 'gifs'
OUT.mkdir(parents=True, exist_ok=True)
PALETTE = [
    (0, 0, 0), (255, 255, 255), (210, 210, 210), (90, 90, 110),
    (255, 92, 0), (255, 214, 0), (255, 242, 130), (95, 255, 30),
    (85, 35, 130), (30, 10, 45),
]


def lzw(indices, min_code_size=4):
    clear = 1 << min_code_size
    end = clear + 1
    codes = [clear]
    table = {(i,): i for i in range(clear)}
    next_code = end + 1
    phrase = (indices[0],)
    for value in indices[1:]:
        candidate = phrase + (value,)
        if candidate in table:
            phrase = candidate
            continue
        codes.append(table[phrase])
        if next_code < 4096:
            table[candidate] = next_code
            next_code += 1
        else:
            codes.append(clear)
            table = {(i,): i for i in range(clear)}
            next_code = end + 1
        phrase = (value,)
    codes.extend([table[phrase], end])

    code_size = min_code_size + 1
    next_code = end + 1
    table = {(i,): i for i in range(clear)}
    bits = []
    for code in codes:
        bits.extend((code >> i) & 1 for i in range(code_size))
        if code == clear:
            table = {(i,): i for i in range(clear)}
            next_code = end + 1
            code_size = min_code_size + 1
        elif code != end:
            if next_code < 4096:
                next_code += 1
                if next_code == (1 << code_size) and code_size < 12:
                    code_size += 1
    packed = bytearray((len(bits) + 7) // 8)
    for i, bit in enumerate(bits):
        packed[i // 8] |= bit << (i % 8)
    return bytes(packed)


def gif(name, width, height, frames, delay=14):
    # GIF89a with 16-color global palette and transparent index 0.
    data = bytearray(b'GIF89a')
    data += width.to_bytes(2, 'little') + height.to_bytes(2, 'little')
    data += bytes([0xF3, 0, 0])
    for r, g, b in PALETTE:
        data += bytes([r, g, b])
    data += b'!\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00'
    for frame in frames:
        data += b'!\xf9\x04\x05' + delay.to_bytes(2, 'little') + b'\x00\x00'
        data += b',' + b'\x00\x00\x00\x00' + width.to_bytes(2, 'little') + height.to_bytes(2, 'little') + b'\x00'
        compressed = lzw(frame)
        data += b'\x04'
        for i in range(0, len(compressed), 255):
            chunk = compressed[i:i + 255]
            data += bytes([len(chunk)]) + chunk
        data += b'\x00'
    data += b';'
    (OUT / name).write_bytes(data)


def frame(width, height):
    return [[0] * width for _ in range(height)]


def put(canvas, x, y, color):
    if 0 <= y < len(canvas) and 0 <= x < len(canvas[0]):
        canvas[y][x] = color


def block(canvas, x, y, w, h, color):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            put(canvas, xx, yy, color)


def flatten(canvas):
    return [value for row in canvas for value in row]


# Spinning skull
skulls = []
for offset in (0, 1, 0, -1):
    c = frame(32, 32)
    block(c, 8 + offset, 5, 16, 16, 1)
    block(c, 10 + offset, 21, 12, 5, 2)
    for x in (11 + offset, 19 + offset): block(c, x, 11, 3, 4, 0)
    block(c, 15 + offset, 16, 3, 3, 3)
    for x in range(11 + offset, 22 + offset, 3): block(c, x, 23, 1, 3, 0)
    skulls.append(flatten(c))
gif('spinning-skull.gif', 32, 32, skulls)

# Flying bat
bats = []
for wings in (0, 1, 2, 1):
    c = frame(48, 28)
    y = 9 + wings
    for x, h in ((4, 4 - wings), (9, 7 - wings), (14, 10 - wings), (29, 10 - wings), (34, 7 - wings), (39, 4 - wings)):
        block(c, x, y + (10 - h), 5, h, 8)
    block(c, 20, 11, 9, 8, 8)
    put(c, 22, 10, 8); put(c, 26, 10, 8); put(c, 22, 14, 1); put(c, 26, 14, 1)
    bats.append(flatten(c))
gif('flying-bat.gif', 48, 28, bats, 10)

# Flickering flames
flames = []
for flicker in (0, 2, 4, 1):
    c = frame(30, 42)
    for x in range(3, 28, 5):
        block(c, x, 25 - (flicker if x % 2 else 0), 4, 15 + flicker, 4)
        block(c, x + 1, 19 - (flicker if x % 2 else 0), 2, 9 + flicker, 5)
        block(c, x + 1, 25, 2, 10, 6)
    flames.append(flatten(c))
gif('flickering-flames.gif', 30, 42, flames, 11)

# Dancing skeleton
skeletons = []
for shift, arm, leg in ((0, 0, 0), (1, -3, 2), (0, 2, -2), (-1, -3, 2)):
    c = frame(34, 48)
    block(c, 12 + shift, 3, 10, 10, 1)
    block(c, 14 + shift, 6, 2, 2, 0); block(c, 19 + shift, 6, 2, 2, 0); block(c, 17 + shift, 10, 2, 1, 0)
    block(c, 16 + shift, 14, 3, 17, 1)
    for y in (17, 21, 25): block(c, 12 + shift, y, 10, 1, 1)
    # arms and legs
    block(c, 7 + shift, 17 + arm, 9, 2, 1); block(c, 19 + shift, 17 - arm, 9, 2, 1)
    block(c, 9 + shift, 18 + arm, 2, 8, 1); block(c, 24 + shift, 18 - arm, 2, 8, 1)
    block(c, 12 + shift + leg, 30, 2, 12, 1); block(c, 20 + shift - leg, 30, 2, 12, 1)
    block(c, 9 + shift + leg, 41, 6, 2, 1); block(c, 20 + shift - leg, 41, 6, 2, 1)
    skeletons.append(flatten(c))
gif('dancing-skeleton.gif', 34, 48, skeletons, 12)

print('Generated:', ', '.join(sorted(p.name for p in OUT.glob('*.gif'))))
