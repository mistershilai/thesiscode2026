#!/usr/bin/env python3
"""Copy generated figures into the paper and report anything still raster.

The notebooks write to ``outputs/figures/``; the LaTeX sources in
``botswana_paper/`` include figures from ``botswana_paper/figures/`` without an
extension, so LaTeX picks the PDF whenever one exists (see the
``\\DeclareGraphicsExtensions`` line in ``main.tex``).

This script copies every generated PDF (and its PNG preview) into the paper's
figure directory, then audits every figure the paper actually includes:
INFORMS accepts vector PDF/EPS for plots and rejects bitmaps, so any included
figure without a PDF is flagged.

    python3 sync_paper_figures.py            # copy + audit
    python3 sync_paper_figures.py --check    # audit only, non-zero exit if raster

Figures that are genuine images rather than plots (the hand-drawn logistics
diagram, screenshots of the interactive folium route maps) are listed in
RASTER_EXCEPTIONS and reported separately -- those need >=300 dpi instead of
vector.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
SRC = REPO / "outputs" / "figures"
PAPER = REPO / "botswana_paper"
DEST = PAPER / "figures"
TEX_FILES = ("main.tex", "ecompanion.tex")

# Not plots -- vector conversion does not apply. These must instead be supplied
# at >=300 dpi (INFORMS author portal, raster art).
RASTER_EXCEPTIONS = {
    "logistics_diagram",  # hand-drawn schematic
    "cmstopmh",           # screenshot of gabs_route.html
    "gabsmultiechelon",   # screenshot of gaborone_cms_pmh_clinics_routes.html
    "seir",               # hand-drawn compartment diagram
    "modifiedseir",
    "betavariations",
    "seasonaldemandmultiplier",
}

INCLUDE_RE = re.compile(r"\\includegraphics(?:\[([^\]]*)\])?\{figures/([^}]+)\}")
WIDTH_RE = re.compile(r"width\s*=\s*([0-9.]*)\s*\\(?:text|line)width")
SUBFIG_RE = re.compile(r"\\begin\{subfigure\}(?:\[[^\]]*\])?\{([0-9.]*)\\textwidth\}")

# Page geometry of botswana_paper (11pt article, 1in margins): \textwidth is
# 469.755pt = 6.5in and \textheight is 650.43pt = 9.0in. A float also needs room
# for its caption, so art taller than ~7.6in overruns the text block -- that is
# the "Overfull \vbox ... while \output is active" warning, which on the page
# looks like the figure running down over the page number.
TEXT_WIDTH_IN = 6.5
MAX_ART_HEIGHT_IN = 7.6


def _includes():
    """Yield (stem, printed width in inches) for every included figure."""
    for name in TEX_FILES:
        tex = PAPER / name
        if not tex.exists():
            continue
        src = tex.read_text()
        for m in INCLUDE_RE.finditer(src):
            opts, target = m.group(1) or "", m.group(2)
            # a \linewidth inside a subfigure resolves to that subfigure's box
            box = TEXT_WIDTH_IN
            for sub in SUBFIG_RE.finditer(src[: m.start()]):
                if src.count(r"\end{subfigure}", sub.end(), m.start()) == 0:
                    box = float(sub.group(1) or 1.0) * TEXT_WIDTH_IN
            w = WIDTH_RE.search(opts)
            printed = float(w.group(1) or 1.0) * box if w else None
            yield Path(target).stem, printed


def included_figures() -> set[str]:
    """Figure stems the paper actually includes."""
    return {stem for stem, _ in _includes()}


def _pdf_size_in(path: Path):
    """Natural size of a PDF in inches, from its MediaBox."""
    data = path.read_bytes()
    boxes = re.findall(rb"/MediaBox\s*\[\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)",
                       data)
    if not boxes:
        return None
    x0, y0, x1, y1 = (float(v) for v in boxes[0])
    return (x1 - x0) / 72.0, (y1 - y0) / 72.0


def geometry_report() -> list[str]:
    """Warn about figures that will not fit, or that get rescaled on the page.

    A figure drawn at one size and included at another has all its text scaled
    with it -- that is what made point sizes inconsistent across figures. Drawing
    at printed size keeps the scale at 1.0.
    """
    problems = []
    for stem, printed_w in sorted(set(_includes())):
        pdf = DEST / f"{stem}.pdf"
        if not pdf.exists():
            continue
        size = _pdf_size_in(pdf)
        if size is None:
            continue
        nat_w, nat_h = size
        if printed_w is None:
            printed_w = nat_w
        scale = printed_w / nat_w
        printed_h = nat_h * scale
        if printed_h > MAX_ART_HEIGHT_IN + 0.05:  # slack for rounding
            problems.append(
                f"  {stem}: {printed_h:.2f}in tall on the page (max {MAX_ART_HEIGHT_IN}) "
                f"-- overruns the text block")
        if abs(scale - 1.0) > 0.05:
            problems.append(
                f"  {stem}: included at {scale:.2f}x its drawn size, so its text "
                f"renders at {scale:.2f}x the authored point size "
                f"(set width={printed_w / TEXT_WIDTH_IN:.3f}\\textwidth -> "
                f"{nat_w / TEXT_WIDTH_IN:.3f}, or redraw at {printed_w:.2f}in wide)")
    return problems


def copy_generated() -> int:
    """Copy figures the paper uses; don't dump the whole gallery into it.

    A figure qualifies if the LaTeX sources include it, or if a file with that
    stem is already in the paper's figure directory (so drafts the author put
    there by hand keep getting refreshed).
    """
    wanted = included_figures() | {p.stem for p in DEST.iterdir() if p.is_file()}
    copied = 0
    for pattern in ("*.pdf", "*.png"):
        for src in sorted(SRC.glob(pattern)):
            if src.stem not in wanted:
                continue
            dst = DEST / src.name
            if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
                continue
            shutil.copy2(src, dst)
            print(f"  copied {src.name}")
            copied += 1
    return copied


def audit() -> list[str]:
    """Return the stems of included plots that have no vector version."""
    missing = []
    for stem in sorted(included_figures()):
        if (DEST / f"{stem}.pdf").exists():
            continue
        if stem in RASTER_EXCEPTIONS:
            continue
        missing.append(stem)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="audit only; do not copy anything"
    )
    args = parser.parse_args()

    if not DEST.exists():
        print(f"error: {DEST} not found", file=sys.stderr)
        return 2

    if not args.check:
        if not SRC.exists():
            print(f"error: {SRC} not found", file=sys.stderr)
            return 2
        print(f"Syncing {SRC} -> {DEST}")
        n = copy_generated()
        print(f"  {n} file(s) updated")

    included = included_figures()
    raster_only = sorted(included & RASTER_EXCEPTIONS)
    missing = audit()

    print(f"\n{len(included)} figure(s) included by the paper.")
    if raster_only:
        print("\nRaster by nature (need >=300 dpi, not vector):")
        for stem in raster_only:
            print(f"  - {stem}")
    geometry = geometry_report()
    if geometry:
        print("\nGEOMETRY -- figures that do not fit or get rescaled on the page:")
        for line in geometry:
            print(line)

    if missing:
        print("\nNO VECTOR VERSION -- INFORMS rejects bitmap plots:")
        for stem in missing:
            print(f"  - {stem}")
        print("\nRe-run the producing notebook (see EXHIBITS.md) to generate the PDF.")
        return 1

    if geometry:
        return 1

    print("\nAll included plots have a vector PDF and fit the page at scale 1.0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
