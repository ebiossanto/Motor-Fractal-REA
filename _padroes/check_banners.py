#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audita os banners: detecta sobreposicao 2D real e estouro de largura."""
import re
import sys
import pathlib

sys.stdout.reconfigure(encoding="utf-8")

W, H = 1200, 400
PAD = 14
problems = 0


def text_box(m):
    """Retorna (x0, y0, x1, y1) aproximado de um <text>."""
    tag = m.group(0)
    x = float(re.search(r'\bx="([0-9.]+)"', tag).group(1))
    y = float(re.search(r'\by="([0-9.]+)"', tag).group(1))
    size = int(re.search(r'font-size="(\d+)"', tag).group(1))
    txt = m.group(1)
    plain = re.sub(r"&[a-zA-Z]+;", "X", txt)
    width = len(plain) * size * 0.56
    return (x - width / 2, y - size * 0.80, x + width / 2, y + size * 0.25, f"text[{txt[:34]}]")


def rect_box(m):
    x, y, w, h = (float(v) for v in m.groups())
    return (x, y, x + w, y + h, f"rect({w:.0f}x{h:.0f})")


def overlap(a, b, tol=2):
    return (a[0] < b[2] - tol and b[0] < a[2] - tol and
            a[1] < b[3] - tol and b[1] < a[3] - tol)


for p in sorted(pathlib.Path(".").glob("*/assets/banner.svg")):
    t = p.read_text(encoding="utf-8")
    repo = p.parts[0]
    n = 0

    boxes = [text_box(m) for m in re.finditer(r"<text[^>]*>(.*?)</text>", t, re.S)]
    for m in re.finditer(r'<rect x="([0-9.]+)" y="([0-9.]+)" width="([0-9.]+)" height="([0-9.]+)"', t):
        b = rect_box(m)
        if b[2] - b[0] > 1100 and b[3] - b[1] > 350:  # fundo
            continue
        if b[2] - b[0] > 1100:  # moldura
            continue
        boxes.append(b)

    # estouro de area util
    for b in boxes:
        if b[0] < PAD - 2 or b[2] > W - PAD + 2 or b[1] < PAD - 2 or b[3] > H - PAD + 2:
            print(f"[FORA] {repo}: {b[4]} => x[{b[0]:.0f},{b[2]:.0f}] y[{b[1]:.0f},{b[3]:.0f}]")
            problems += 1
            n += 1

    # sobreposicao 2D real (ignora texto contido em caixa de tag/rotulo)
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if not overlap(a, b):
                continue
            contained = (a[0] >= b[0] - 2 and a[2] <= b[2] + 2 and
                         a[1] >= b[1] - 2 and a[3] <= b[3] + 2)
            contained = contained or (b[0] >= a[0] - 2 and b[2] <= a[2] + 2 and
                                      b[1] >= a[1] - 2 and b[3] <= a[3] + 2)
            if contained:
                continue
            print(f"[SOPOSICAO] {repo}: {a[4]} x {b[4]}")
            problems += 1
            n += 1

    print(f"[ok] {repo}: {len(boxes)} elementos, {n} problemas")

print()
print("TOTAL DE PROBLEMAS:", problems)
sys.exit(1 if problems else 0)
