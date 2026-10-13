#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de banner padrao do portfolio "IA RESEARCH" de Euzebio Soares.

Gera um SVG 1200x400 com:
  - fundo em gradiente escuro
  - moldura de destaque
  - rotulo "IA RESEARCH"
  - titulo do repositorio
  - subtitulo (descricao curta)
  - linha de formula / keyword teorica (opcional)
  - assinatura do autor + link do GitHub
  - tags (opcional)

Uso:
    python gen_banner.py --config banners.json --out-root ..
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import sys

W, H = 1200, 400

# Paleta derivada do banner original de IA-RESEARCH-Logica.
PALETTE = {
    "bg0": "#0d1b2a",
    "bg1": "#1b2a41",
    "frame": "#4cc9f0",
    "label": "#4cc9f0",
    "title": "#e0e6f0",
    "subtitle": "#90e0ef",
    "formula": "#ffd166",
    "author": "#8ecae6",
    "tag": "#4cc9f0",
}

FONT_STACK = "Segoe UI, Helvetica, Arial, sans-serif"
MONO_STACK = "Consolas, Menlo, monospace"


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def fit(text: str, max_width: int, start: int, minimum: int = 18) -> int:
    """Reduz a fonte ate o texto caber em `max_width` px (aprox. 0.55em por char)."""
    size = start
    while size > minimum and len(text) * size * 0.55 > max_width:
        size -= 1
    return size


def svg_banner(cfg: dict) -> str:
    """Monta o banner com layout calculado de baixo para cima.

    Garante: (1) bloco de conteudo nunca invade as tags/assinatura,
    (2) tags nunca invadem a assinatura, (3) tudo dentro da moldura.
    """
    title = cfg["title"]
    subtitle = cfg.get("subtitle", "")
    formula = cfg.get("formula", "")
    author = cfg.get("author", "Euzébio Soares — github.com/ebiossanto")
    label = cfg.get("label", "IA RESEARCH")
    tags = cfg.get("tags", [])

    title_size = fit(title, 1080, 62, 34)
    subtitle_size = fit(subtitle, 1080, 29, 18)
    formula_size = fit(formula, 1080, 30, 18)
    author_size = fit(author, 1080, 24, 15)

    # ---- rodape (assinatura + tags), ancorado na base ----
    y_author = H - 34                       # baseline da assinatura
    author_top = y_author - author_size * 0.80
    if tags:
        tags_bottom = author_top - 16
        tags_top = tags_bottom - 30
        content_bottom = tags_top - 18
    else:
        tags_top = tags_bottom = None
        content_bottom = author_top - 18

    # ---- bloco de conteudo: alturas + gaps internos ----
    gap_label_title, gap_lines = 40, 34
    heights = [36 + gap_label_title + title_size]      # rotulo + titulo
    if subtitle:
        heights.append(gap_lines + subtitle_size)
    if formula:
        heights.append(gap_lines + formula_size)
    block_h = sum(heights)

    content_top = content_bottom - block_h
    if content_top < 34:                    # nao cabe: compacta os gaps
        excess = 34 - content_top
        shrink = min(excess, gap_label_title - 20, (len(heights) - 1) * (gap_lines - 14))
        if shrink > 0:
            gap_label_title -= min(shrink, gap_label_title - 20)
            rest = shrink - (40 - gap_label_title)
            if rest > 0:
                gap_lines = max(14, gap_lines - rest // max(1, len(heights) - 1))
            heights = [36 + gap_label_title + title_size]
            if subtitle:
                heights.append(gap_lines + subtitle_size)
            if formula:
                heights.append(gap_lines + formula_size)
            block_h = sum(heights)
            content_top = content_bottom - block_h

    # ---- linhas verticais ----
    y = content_top
    label_top = y
    y_label = label_top + 25                # baseline dentro da caixa
    y_title = label_top + 36 + gap_label_title + title_size * 0.80
    y = y_title
    y_subtitle = None
    if subtitle:
        y += gap_lines + subtitle_size * 0.80
        y_subtitle = y
    y_formula = None
    if formula:
        y += gap_lines + formula_size * 0.80
        y_formula = y

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="{esc(label)} — {esc(title)}">'
    )

    # ---- defs ----
    parts.append("  <defs>")
    parts.append(
        '    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{PALETTE["bg0"]}"/>'
        f'<stop offset="0.55" stop-color="{PALETTE["bg1"]}"/>'
        f'<stop offset="1" stop-color="{PALETTE["bg0"]}"/>'
        "</linearGradient>"
    )
    parts.append(
        '    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{PALETTE["frame"]}"/>'
        f'<stop offset="1" stop-color="#7b2ff7"/>'
        "</linearGradient>"
    )
    parts.append(
        '    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">'
        '<feGaussianBlur stdDeviation="4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        "</filter>"
    )
    parts.append("  </defs>")

    # ---- fundo + malha decorativa ----
    parts.append(f'  <rect width="{W}" height="{H}" fill="url(#bg)"/>')
    parts.append(f'  <g opacity="0.12" stroke="{PALETTE["frame"]}" stroke-width="1" fill="none">')
    for i in range(0, W + 1, 100):
        parts.append(f'    <line x1="{i}" y1="0" x2="{i}" y2="{H}"/>')
    for j in range(0, H + 1, 100):
        parts.append(f'    <line x1="0" y1="{j}" x2="{W}" y2="{j}"/>')
    parts.append("  </g>")
    parts.append(
        f'  <rect x="12" y="12" width="{W - 24}" height="{H - 24}" fill="none" '
        f'stroke="{PALETTE["frame"]}" stroke-width="2" opacity="0.7"/>'
    )

    # ---- rotulo "IA RESEARCH" ----
    label_w = len(label) * 15 + 44
    parts.append(
        f'  <rect x="{(W - label_w) / 2:.1f}" y="{label_top:.1f}" width="{label_w:.1f}" '
        f'height="36" rx="18" fill="none" stroke="url(#accent)" stroke-width="2"/>'
    )
    parts.append(
        f'  <text x="{W / 2}" y="{y_label:.1f}" text-anchor="middle" '
        f'font-family="{FONT_STACK}" font-size="17" font-weight="700" '
        f'letter-spacing="4" fill="url(#accent)">{esc(label)}</text>'
    )

    # ---- titulo ----
    parts.append(
        f'  <text x="{W / 2}" y="{y_title}" text-anchor="middle" font-family="{FONT_STACK}" '
        f'font-size="{title_size}" font-weight="700" fill="{PALETTE["title"]}" '
        f'filter="url(#glow)">{esc(title)}</text>'
    )

    # ---- subtitulo ----
    if subtitle:
        parts.append(
            f'  <text x="{W / 2}" y="{y_subtitle}" text-anchor="middle" font-family="{FONT_STACK}" '
            f'font-size="{subtitle_size}" fill="{PALETTE["subtitle"]}">{esc(subtitle)}</text>'
        )

    # ---- formula ----
    if formula:
        parts.append(
            f'  <text x="{W / 2}" y="{y_formula}" text-anchor="middle" font-family="{MONO_STACK}" '
            f'font-size="{formula_size}" fill="{PALETTE["formula"]}">{esc(formula)}</text>'
        )

    # ---- tags ----
    if tags:
        tag_h, gap, tag_font = 30, 16, 14
        def tag_metrics(font: int):
            ws = [len(t) * font * 0.58 + 26 for t in tags]
            return ws, sum(ws) + gap * max(0, len(tags) - 1)

        widths, total = tag_metrics(tag_font)
        avail = W - 56
        while total > avail and tag_font > 11:
            tag_font -= 1
            widths, total = tag_metrics(tag_font)
        if total > avail and len(tags) > 1:
            gap = max(6, gap - (total - avail) // (len(tags) - 1))
            widths, total = tag_metrics(tag_font)

        x = (W - total) / 2
        y_tag = tags_top
        for t, w in zip(tags, widths):
            parts.append(
                f'  <rect x="{x:.1f}" y="{y_tag}" width="{w}" height="{tag_h}" rx="{tag_h / 2}" '
                f'fill="none" stroke="{PALETTE["tag"]}" stroke-width="1" opacity="0.8"/>'
            )
            parts.append(
                f'  <text x="{x + w / 2:.1f}" y="{y_tag + 20}" text-anchor="middle" '
                f'font-family="{FONT_STACK}" font-size="{tag_font}" fill="{PALETTE["tag"]}">{esc(t)}</text>'
            )
            x += w + gap

    # ---- assinatura do autor ----
    parts.append(
        f'  <text x="{W / 2}" y="{y_author}" text-anchor="middle" font-family="{FONT_STACK}" '
        f'font-size="{author_size}" fill="{PALETTE["author"]}">{esc(author)}</text>'
    )

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="JSON com {repo: cfg}")
    ap.add_argument("--out-root", default="..", help="raiz onde fica cada repo")
    ap.add_argument("--only", nargs="*", help="gera apenas para estes repos")
    args = ap.parse_args()

    root = pathlib.Path(args.out_root).resolve()
    cfgs = json.loads(pathlib.Path(args.config).read_text(encoding="utf-8"))

    for repo, cfg in cfgs.items():
        if args.only and repo not in args.only:
            continue
        dest = root / repo / "assets"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "banner.svg").write_text(svg_banner(cfg), encoding="utf-8")
        print(f"[ok] {repo}/assets/banner.svg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
