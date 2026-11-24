"""
Builds the SVGs in assets/ that the profile README is made of.

GitHub loads no web fonts, so all text is converted to outlines from the
portfolio's own fonts (Rubik and the UnifontEX subset). Each graphic comes in
a dark and a light version; the README picks one with <picture>.

    pip install fonttools brotli uharfbuzz
    python scripts/generate.py [path/to/rmatsuda21.github.io]

The portfolio checkout needs `npm install` to have been run (for Rubik).
"""

import io
import sys
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.basePen import BasePen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
PORTFOLIO = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "rmatsuda21.github.io"
OUT = ROOT / "assets"

RUBIK = PORTFOLIO / "node_modules/@fontsource-variable/rubik/files/rubik-latin-wght-normal.woff2"
PIXEL = PORTFOLIO / "src/assets/fonts/unifontex-subset.woff2"

W = 800  # every full-width graphic shares this viewBox width
MUTED = 0.66
RULE = 0.24
GRID = 0.07

# ── Content ──────────────────────────────────────────────────────────────

NAME = "Reo Matsuda"
SPEC = [("Role", "Software Engineer, Full Stack"), ("Base", "Jersey City, NJ"), ("Main", "Jigglypuff (SSBU)")]
STACK = ["React", "Next.js", "TypeScript", "GraphQL", "Sass", "Django", "Python"]
BUTTONS = [("portfolio", "Portfolio", True), ("linkedin", "LinkedIn", False), ("email", "Email", False)]
HEADERS = [("experience", "02", "Experience", "Nextdoor · GOAT Group"), ("work", "03", "Work", "3 entries")]
FIGURES = [
    ("25M", "Weekly users", "Nextdoor"),
    ("2.2M", "Page visits a month", "Nextdoor events"),
    ("1M+", "Global users", "GOAT Black Friday"),
    ("55K+", "Daily users", "GOAT checkout"),
]
PROJECTS = [
    ("001", "Smash Ranker", "Custom graphics for Smash Bros. tournaments", "React · TS · GraphQL"),
    ("002", "CSTAT Gacha Com", "Web viewer with a full codex, card search and offers", "Next · TS · Sass"),
    ("003", "Pitch.io", "Relative pitch and chord trainer", "React · Webpack"),
]

THEMES = {
    # fg, page colour (for text knocked out of a filled shape), revision label
    "dark": ("#ffffff", "#0d1117", "2.0"),
    "light": ("#000000", "#ffffff", "2.1"),
}

# ── Text to outlines ─────────────────────────────────────────────────────


class PathPen(BasePen):
    """Absolute M/L/Q/C/Z only, so two weights of a glyph can be morphed."""

    def __init__(self, glyph_set):
        super().__init__(glyph_set)
        self.out = []

    @staticmethod
    def _n(v):
        return f"{v:.1f}".rstrip("0").rstrip(".")

    def _pt(self, p):
        return f"{self._n(p[0])} {self._n(p[1])}"

    def _moveTo(self, p):
        self.out.append(f"M{self._pt(p)}")

    def _lineTo(self, p):
        self.out.append(f"L{self._pt(p)}")

    def _qCurveToOne(self, a, p):
        self.out.append(f"Q{self._pt(a)} {self._pt(p)}")

    def _curveToOne(self, a, b, p):
        self.out.append(f"C{self._pt(a)} {self._pt(b)} {self._pt(p)}")

    def _closePath(self):
        self.out.append("Z")

    def d(self):
        return "".join(self.out)


def glyph_d(glyph_set, name, scale, x, baseline):
    pen = PathPen(glyph_set)
    glyph_set[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, baseline)))
    return pen.d()


class Rubik:
    _cache = {}

    def __new__(cls, weight):
        if weight not in cls._cache:
            self = super().__new__(cls)
            font = instancer.instantiateVariableFont(TTFont(RUBIK), {"wght": weight})
            font.flavor = None
            buf = io.BytesIO()
            font.save(buf)
            self.font = font
            self.hb = hb.Font(hb.Face(buf.getvalue()))
            self.upm = font["head"].unitsPerEm
            self.cap = font["OS/2"].sCapHeight / self.upm
            self.glyphs = font.getGlyphSet()
            self.order = font.getGlyphOrder()
            cls._cache[weight] = self
        return cls._cache[weight]

    def shape(self, text, tracking=0.0):
        """[(glyph name, x, advance)] in font units, and the total width."""
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {"kern": True})
        x, run = 0, []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            run.append((self.order[info.codepoint], x, pos.x_advance))
            x += pos.x_advance + tracking * self.upm
        return run, x - tracking * self.upm

    def width(self, text, size, tracking=0.0):
        return self.shape(text, tracking)[1] * size / self.upm

    def path(self, text, x, baseline, size, tracking=0.0, anchor="start"):
        run, width = self.shape(text, tracking)
        s = size / self.upm
        if anchor == "end":
            x -= width * s
        return "".join(glyph_d(self.glyphs, n, s, x + gx * s, baseline) for n, gx, _ in run)


_pixel = TTFont(PIXEL)
_pixel_glyphs = _pixel.getGlyphSet()
_pixel_cmap = _pixel.getBestCmap()
_pixel_upm = _pixel["head"].unitsPerEm
PIXEL_TRACK = 0.04


def pixel_width(text, size=16):
    names = [_pixel_cmap[ord(c)] for c in text.upper()]
    s = size / _pixel_upm
    return sum(_pixel_glyphs[n].width for n in names) * s + PIXEL_TRACK * size * (len(names) - 1)


def pixel(text, x, baseline, size=16, anchor="start"):
    """UnifontEX is a 16px bitmap face: keep `size` at whole multiples of 16."""
    s = size / _pixel_upm
    if anchor == "end":
        x -= pixel_width(text, size)
    elif anchor == "middle":
        x -= pixel_width(text, size) / 2
    out = []
    for c in text.upper():
        name = _pixel_cmap[ord(c)]
        out.append(glyph_d(_pixel_glyphs, name, s, x, baseline))
        x += _pixel_glyphs[name].width * s + PIXEL_TRACK * size
    return "".join(out)


def svg(width, height, fg, body, label, style=""):
    n = PathPen._n
    style = f"<style>{style}</style>" if style else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n(width)} {n(height)}" '
        f'width="{n(width)}" height="{n(height)}" fill="{fg}" role="img" aria-label="{label}">'
        f"<title>{label}</title>{style}{body}</svg>\n"
    )


def path(d, opacity=None, extra=""):
    o = f' opacity="{opacity}"' if opacity else ""
    return f'<path d="{d}"{o}{extra}/>'


def rect(x, y, w, h, opacity=None, extra=""):
    n = PathPen._n
    o = f' opacity="{opacity}"' if opacity else ""
    return f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}"{o}{extra}/>'


def box(x, y, w, h):
    """A 1px outline that stays crisp at 1:1."""
    n = PathPen._n
    return (
        f'<rect x="{n(x + 0.5)}" y="{n(y + 0.5)}" width="{n(w - 1)}" height="{n(h - 1)}" '
        f'fill="none" stroke="currentColor" stroke-width="1"/>'
    )


# ── Graphics ─────────────────────────────────────────────────────────────


def banner(fg, bg, rev):
    """
    The name, as on the portfolio: every few seconds a ripple runs through
    the letters, thinning each from weight 800 to 300 and back.
    """
    heavy, thin = Rubik(800), Rubik(300)
    track = -0.045
    run, width = heavy.shape(NAME, track)
    size = (W + 6) / (width / heavy.upm)  # +6 cancels the R's side bearing
    s = size / heavy.upm
    thin_run, _ = thin.shape(NAME, track)

    label_base = 28
    name_base = label_base + 30 + heavy.cap * size
    rule_y = name_base + 28
    spec_base = rule_y + 31
    rule2_y = spec_base + 13
    height = round(rule2_y + 17)  # room below, so the README needs no spacer

    cycle, stagger = 9, 0.07
    static, moving, i = [], [], 0
    for (name, gx, adv), (_, _, thin_adv) in zip(run, thin_run):
        x = -3 + gx * s
        h = glyph_d(heavy.glyphs, name, s, x, name_base)
        if not h:
            continue
        t = glyph_d(thin.glyphs, name, s, x + (adv - thin_adv) * s / 2, name_base)
        static.append(h)
        same_shape = [c for c in h if c.isalpha()] == [c for c in t if c.isalpha()]
        if not same_shape:
            moving.append(path(h))
            continue
        moving.append(
            f'<path d="{h}"><animate attributeName="d" dur="{cycle}s" begin="{i * stagger:.2f}s" '
            f'repeatCount="indefinite" calcMode="spline" keyTimes="0;0.035;0.12;1" '
            f'keySplines=".3 0 .2 1;.2 .8 .2 1;0 0 1 1" values="{h};{t};{h};{h}"/></path>'
        )
        i += 1

    grid = "".join(rect(W * c / 12, 0, 1, rule_y, GRID) for c in range(1, 12))
    labels = pixel("Sheet 01 — Subject", 0, label_base) + pixel(
        f"RM—GitHub · Rev {rev}", W, label_base, anchor="end"
    )

    # First entry flush left, last flush right, the rest spread between.
    widths = [pixel_width(dt) + 12 + pixel_width(dd) for dt, dd in SPEC]
    free = (W - sum(widths)) / (len(SPEC) - 1)
    spec_dt, spec_dd, x = "", "", 0
    for (dt, dd), width in zip(SPEC, widths):
        spec_dt += pixel(dt, x, spec_base)
        spec_dd += pixel(dd, x + pixel_width(dt) + 12, spec_base)
        x += width + free

    body = (
        grid
        + path(labels, MUTED)
        + f'<g class="still">{path("".join(static))}</g>'
        + f'<g class="moving">{"".join(moving)}</g>'
        + rect(0, rule_y, W, 1)
        + path(spec_dt, MUTED)
        + path(spec_dd)
        + rect(0, rule2_y, W, 1, RULE)
    )
    style = ".still{display:none}@media (prefers-reduced-motion:reduce){.still{display:inline}.moving{display:none}}"
    return svg(W, height, fg, body, NAME, style)


def button(text, filled, fg, bg):
    label = f"{text} ↗"
    pad, height = 16, 40
    width = round(pixel_width(label) + pad * 2)
    glyphs = pixel(label, pad, 26)
    if filled:
        body = rect(0, 0, width, height) + path(glyphs, extra=f' fill="{bg}"')
    else:
        body = f'<g color="{fg}">{box(0, 0, width, height)}</g>' + path(glyphs)
    return svg(width, height, fg, body, text)


def ruler(fg, bg):
    """The stack as a ruler; a wave runs along the graduations."""
    minor = 3
    slot = W / len(STACK)
    step = slot / (minor + 1)
    base = 78
    ticks, labels = [], ""
    for i, tech in enumerate(STACK):
        labels += pixel(tech, i * slot, base + 26)
        for m in range(minor + 1):
            index = i * (minor + 1) + m
            h = 22 if m == 0 else 10
            ticks.append(
                f'<rect class="t" x="{PathPen._n(index * step)}" y="{base - h}" width="1" height="{h}" '
                f'style="animation-delay:{index * 0.06:.2f}s"/>'
            )
    ticks.append(rect(W - 1, base - 22, 1, 22))
    head = pixel("Stack", 0, 28)
    count = pixel(f"{len(STACK):02d} / {len(STACK):02d}", W, 28, anchor="end")
    body = path(head + count, MUTED) + "".join(ticks) + rect(0, base, W, 1) + path(labels)
    style = (
        ".t{transform-box:fill-box;transform-origin:50% 100%;animation:w 6s cubic-bezier(.3,0,.2,1) infinite}"
        "@keyframes w{0%,12%,100%{transform:scaleY(1)}5%{transform:scaleY(1.9)}}"
        "@media (prefers-reduced-motion:reduce){.t{animation:none}}"
    )
    return svg(W, base + 40, fg, body, "Stack: " + ", ".join(STACK), style)


def header(no, title, meta, fg, bg):
    base = 56
    font = Rubik(700)
    body = (
        rect(0, 0, W, 1)
        + path(pixel(no, 0, base) + pixel(meta, W, base, anchor="end"), MUTED)
        + path(font.path(title, 40, base, 44, -0.03))
    )
    return svg(W, base + 20, fg, body, f"{no} {title}")


def figures(fg, bg):
    gap, height = 12, 116
    tile = (W - gap * (len(FIGURES) - 1)) / len(FIGURES)
    boxes, values, labels, sources = "", "", "", ""
    for i, (value, label, source) in enumerate(FIGURES):
        x = i * (tile + gap)
        boxes += box(x, 0, tile, height)
        values += pixel(value, x + 16, 50, 32)
        labels += pixel(label, x + 16, 78)
        sources += pixel(source, x + 16, 98)
    body = f'<g color="{fg}">{boxes}</g>' + path(values) + path(labels) + path(sources, MUTED)
    alt = "; ".join(f"{v} {l.lower()}, {s}" for v, l, s in FIGURES)
    return svg(W, height, fg, body, alt)


def project(no, title, tagline, stack, fg, bg):
    height = 92
    body = (
        path(pixel(no, 0, 40) + pixel(stack, W - 56, 40, anchor="end"), MUTED)
        + path(Rubik(700).path(title, 56, 42, 30, -0.02))
        + path(Rubik(400).path(tagline, 56, 68, 16), MUTED)
        + path(pixel("↗", W - 4, 50, 32, anchor="end"))
        + rect(0, height - 1, W, 1, RULE)
    )
    return svg(W, height, fg, body, f"{no} {title}: {tagline}. {stack}")


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()

    for theme, (fg, bg, rev) in THEMES.items():
        files = {"banner": banner(fg, bg, rev), "stack": ruler(fg, bg), "figures": figures(fg, bg)}
        for slug, text, filled in BUTTONS:
            files[f"btn-{slug}"] = button(text, filled, fg, bg)
        for slug, no, title, meta in HEADERS:
            files[f"head-{slug}"] = header(no, title, meta, fg, bg)
        for no, title, tagline, stack in PROJECTS:
            files[f"work-{no}"] = project(no, title, tagline, stack, fg, bg)
        for name, content in files.items():
            (OUT / f"{name}-{theme}.svg").write_text(content)

    total = sum(f.stat().st_size for f in OUT.glob("*.svg"))
    print(f"{len(list(OUT.glob('*.svg')))} files, {total / 1024:.0f} KB")


if __name__ == "__main__":
    main()
