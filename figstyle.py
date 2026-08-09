"""Publication figure style and export helpers (INFORMS / M&SOM).

Why this module exists
----------------------
INFORMS journals (M&SOM included) require *vector* art for plots. From the
INFORMS LaTeX style instructions, Sec. 9.1: "the preferred formats are PDF or
EPS, whenever they can guarantee the vector format (drawing, not image)"; the
author portal adds that "bitmap files (i.e., files with a BMP or PNG extension)
are not acceptable" and that submitted PDFs must have "fonts embedded". Print
copies are converted to grayscale by default, so a figure has to stay readable
with the colour removed -- hence the linestyle/marker/hatch encodings below.

Usage
-----
    import sys; sys.path.append('..')          # repo root on the path
    from figstyle import use_publication_style, save_figure

    use_publication_style()                    # AFTER any seaborn set_style call
    ...
    save_figure("../outputs/figures/kappa")    # writes kappa.pdf and kappa.png

`save_figure` takes a path with or without an extension; the extension is
ignored and one file per entry in `formats` is written. The PDF is the artifact
that goes to the journal; the PNG is a convenience preview for the README, the
web app, and quick viewing in the notebook.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from cycler import cycler

__all__ = [
    "use_publication_style",
    "save_figure",
    "figure_size",
    "TEXT_WIDTH_IN",
    "policy_style",
    "bar_style",
    "label_text_color",
    "POLICY_KEYS",
    "POLICY_COLORS",
    "POLICY_MARKERS",
    "POLICY_LINESTYLES",
    "SEQUENTIAL_CMAP",
    "CHOROPLETH_CMAP",
    "HATCHES",
    "FIGURE_FORMATS",
]

# Formats written by save_figure. PDF is the submission artifact; PNG is a
# preview only and is never what gets uploaded to the journal.
FIGURE_FORMATS = ("pdf", "png")
PNG_PREVIEW_DPI = 200

# \textwidth of botswana_paper/main.tex (11pt article, 1in margins) = 469.755pt.
# Authoring figures at the width they will be *printed* is the whole trick behind
# consistent text size: if a figure is drawn 18in wide and then included at
# 0.9\textwidth, LaTeX shrinks it 3.1x and a 12pt label lands on the page at 3.9pt.
# Draw at printed size and the point size in the code is the point size on paper.
TEXT_WIDTH_IN = 6.5

# \textheight is 650.43pt = 9.0in. A float also needs room for its caption (a few
# double-spaced 11pt lines) plus \textfloatsep, so cap the art itself well short
# of the full page -- otherwise LaTeX reports "Overfull \vbox ... while \output is
# active" and the figure runs down over the page number.
MAX_FIGURE_HEIGHT_IN = 7.6

# Perceptually uniform, colourblind-safe, and monotone in luminance, so it
# survives the grayscale conversion INFORMS applies to the print edition.
# Reversed so that "more" (more unmet demand, higher cost) reads as "darker".
SEQUENTIAL_CMAP = "viridis_r"
CHOROPLETH_CMAP = SEQUENTIAL_CMAP

# The three allocation policies are the recurring series across the paper, in
# the order they are plotted. Colour alone does not distinguish them in print,
# so every policy also carries a linestyle and a marker.
POLICY_KEYS = ("deterministic", "static_robust", "aro_adr")
POLICY_COLORS = {
    "deterministic": "#4C72B0",
    "static_robust": "#DD8452",
    "aro_adr": "#55A868",
}
POLICY_LINESTYLES = {
    "deterministic": "--",
    "static_robust": "-.",
    "aro_adr": "-",
}
POLICY_MARKERS = {
    "deterministic": "o",
    "static_robust": "s",
    "aro_adr": "^",
}
# Grayscale-safe fills for grouped/paired bar charts, in draw order.
HATCHES = ("", "///", "...", "xxx", "\\\\\\", "|||")

# Six (colour, linestyle) pairs so that even the six-compartment SEIR panels
# stay distinguishable in grayscale without per-call styling.
_COLOR_CYCLE = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860"]
_LINESTYLE_CYCLE = ["-", "--", "-.", ":", (0, (3, 1, 1, 1)), (0, (5, 1))]

_POLICY_ALIASES = {
    "deterministic": "deterministic",
    "det": "deterministic",
    "static robust": "static_robust",
    "static_robust": "static_robust",
    "static-robust": "static_robust",
    "rob": "static_robust",
    "aro-adr": "aro_adr",
    "aro_adr": "aro_adr",
    "aro adr": "aro_adr",
    "adr": "aro_adr",
}


def _canonical_policy(name: str) -> str:
    key = str(name).strip().lower()
    if key not in _POLICY_ALIASES:
        raise KeyError(
            f"unknown policy {name!r}; expected one of {sorted(set(_POLICY_ALIASES.values()))}"
        )
    return _POLICY_ALIASES[key]


def latex_available() -> bool:
    """True when a LaTeX toolchain usable by text.usetex is on PATH."""
    return shutil.which("latex") is not None and shutil.which("dvipng") is not None


def use_publication_style(usetex: bool | None = None) -> None:
    """Apply the INFORMS-facing rcParams.

    Call this *after* any ``seaborn.set_style`` / ``seaborn.set_theme`` call --
    seaborn resets rcParams wholesale and would otherwise undo the font and
    grid settings.

    Parameters
    ----------
    usetex
        Force LaTeX text rendering on or off. The default (None) enables it
        when a LaTeX install is detected and silently falls back to matplotlib's
        Computer Modern mathtext otherwise, so the notebooks still run on a
        machine without TeX.
    """
    if usetex is None:
        usetex = latex_available()

    mpl.rcParams.update(
        {
            # --- vector output, embedded fonts -------------------------------
            # Type 42 (TrueType) instead of matplotlib's default Type 3, which
            # publishers' preflight checks routinely reject. With usetex the
            # text is set in Type 1 Computer Modern, which is already fine.
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "pdf.compression": 6,
            "savefig.format": "pdf",
            # NOT "tight": a tight bounding box crops the figure to its ink, so
            # the saved file is smaller than the figsize and \includegraphics
            # then scales it back up -- taking all the text with it. Keeping the
            # standard bbox means drawn size == printed size == scale 1.0, which
            # is what makes point sizes consistent across figures. Use
            # tight_layout()/constrained_layout to manage space *inside* the
            # figure, and keep legends inside the canvas.
            "savefig.bbox": "standard",
            "savefig.pad_inches": 0.02,
            "savefig.transparent": False,
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
            # --- typography --------------------------------------------------
            "text.usetex": usetex,
            "font.family": "serif",
            "font.serif": ["Computer Modern Roman", "CMU Serif", "DejaVu Serif"],
            "mathtext.fontset": "cm",
            # One type scale for every figure. Body text is 11pt, so 9pt labels
            # and 8pt ticks read as "slightly smaller than the text" on the page
            # -- which is what they are, once figures are drawn at printed size.
            # Per-call fontsize= overrides are what made the old figures
            # inconsistent; prefer changing these.
            "font.size": 9,
            "axes.titlesize": 9,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "figure.titlesize": 9,
            # --- grayscale-safe defaults -------------------------------------
            "axes.prop_cycle": (
                cycler(color=_COLOR_CYCLE) + cycler(linestyle=_LINESTYLE_CYCLE)
            ),
            "axes.grid": False,
            "image.cmap": SEQUENTIAL_CMAP,
            "lines.linewidth": 1.6,
            "lines.markersize": 4,
            "legend.frameon": False,
        }
    )


def figure_size(width_frac: float = 1.0, aspect: float = 0.62, *, height_in=None):
    """Figure size in inches, at the size the figure will actually be printed.

    Parameters
    ----------
    width_frac
        The figure's width in the paper as a fraction of ``\\textwidth`` -- i.e.
        whatever is in the ``\\includegraphics[width=...]`` (and multiplied by
        the enclosing ``subfigure`` width, if any).
    aspect
        Height / width. Defaults to roughly the golden ratio.
    height_in
        Explicit height in inches, overriding ``aspect``.

    Keeping this in step with the LaTeX source is what makes text the same size
    across figures: ``\\includegraphics`` then scales by ~1.0, so the point sizes
    set by ``use_publication_style`` are the point sizes on the printed page.
    """
    width = width_frac * TEXT_WIDTH_IN
    height = height_in if height_in is not None else width * aspect
    if height > MAX_FIGURE_HEIGHT_IN:
        # Too tall for the page: shrink both dimensions rather than let the
        # float overrun the text block. Narrow the \includegraphics width in the
        # LaTeX source to match, so the figure is still included at scale 1.
        width *= MAX_FIGURE_HEIGHT_IN / height
        height = MAX_FIGURE_HEIGHT_IN
    return (width, height)


def policy_style(policy: str, *, marker: bool = False, **overrides) -> dict:
    """Plot kwargs for one of the three allocation policies.

    Returns colour + linestyle (and optionally a marker) so the series stays
    separable after the print edition drops the colour.
    """
    key = _canonical_policy(policy)
    style = {
        "color": POLICY_COLORS[key],
        "linestyle": POLICY_LINESTYLES[key],
    }
    if marker:
        style["marker"] = POLICY_MARKERS[key]
        style.setdefault("markevery", 3)
    style.update(overrides)
    return style


def bar_style(index: int, policy: str | None = None, **overrides) -> dict:
    """Grayscale-safe bar kwargs: a hatch per position, plus a drawn edge."""
    style = {
        "hatch": HATCHES[index % len(HATCHES)],
        "edgecolor": "black",
        "linewidth": 0.6,
    }
    if policy is not None:
        style["color"] = POLICY_COLORS[_canonical_policy(policy)]
    style.update(overrides)
    return style


def label_text_color(value, cmap=None, vmin=0.0, vmax=1.0, missing="black") -> str:
    """Pick black or white annotation text for a filled patch.

    The choropleths label each district on top of its fill. A fixed white label
    disappears over the light end of a luminance-monotone colormap, so choose
    per patch from the fill's relative luminance (WCAG coefficients).
    """
    try:
        if value is None or value != value:  # NaN
            return missing
    except TypeError:
        return missing

    cmap = plt.get_cmap(cmap or CHOROPLETH_CMAP)
    span = (vmax - vmin) or 1.0
    r, g, b, _ = cmap(min(max((float(value) - vmin) / span, 0.0), 1.0))
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "black" if luminance > 0.55 else "white"


def fit_label_fontsize(ax, geometry, text, max_pt: float = 5.0, min_pt: float = 3.2):
    """Largest point size at which ``text`` fits inside ``geometry``, or None.

    The district choropleths label each polygon in place. Once the panels are
    drawn at printed size some districts are simply too small to hold their
    name, and fixed-size labels overlap their neighbours. Returning None lets
    the caller skip those labels rather than print a collision.

    Call this after the polygons are plotted, so the data transform is set.
    """
    lines = str(text).split("\n")
    if not lines:
        return None

    # Measure the room actually available where the label sits, not the bounding
    # box. Districts like Central and Kgalagadi are wide overall but narrow at
    # their centroid, and sizing to the box pushed their labels out over the
    # neighbouring panel.
    centroid = geometry.centroid
    x0, y0, x1, y1 = geometry.bounds
    span_x, span_y = x1 - x0, y1 - y0
    try:
        from shapely.geometry import LineString

        def _extent(line, coord_index, at):
            inter = geometry.intersection(line)
            if inter.is_empty:
                return 0.0
            parts = getattr(inter, "geoms", [inter])
            for part in parts:
                lo, hi = part.bounds[coord_index], part.bounds[coord_index + 2]
                if lo - 1e-9 <= at <= hi + 1e-9:
                    return hi - lo
            return max((p.bounds[coord_index + 2] - p.bounds[coord_index])
                       for p in parts)

        span_x = _extent(LineString([(x0, centroid.y), (x1, centroid.y)]), 0, centroid.x)
        span_y = _extent(LineString([(centroid.x, y0), (centroid.x, y1)]), 1, centroid.y)
    except Exception:
        pass  # fall back to the bounding box
    if span_x <= 0 or span_y <= 0:
        return None

    (px0, py0), (px1, py1) = ax.transData.transform(
        [(centroid.x - span_x / 2, centroid.y - span_y / 2),
         (centroid.x + span_x / 2, centroid.y + span_y / 2)]
    )
    dpi = ax.get_figure().dpi
    box_w_pt = abs(px1 - px0) * 72.0 / dpi
    box_h_pt = abs(py1 - py0) * 72.0 / dpi

    # Computer Modern averages a little over half an em per character.
    widest = max(len(line) for line in lines) or 1
    pt_from_width = 0.85 * box_w_pt / (0.55 * widest)
    pt_from_height = 0.85 * box_h_pt / (1.25 * len(lines))
    pt = min(max_pt, pt_from_width, pt_from_height)
    return pt if pt >= min_pt else None


def district_label(name: str) -> str:
    """Shorten a district name for in-map labelling."""
    return (
        str(name)
        .replace(" District", "")
        .replace("North-East", "NE")
        .replace("North-West", "NW")
        .replace("South-East", "SE")
        .replace(" ", "\n")
    )


def label_districts(
    ax,
    frame,
    value_col,
    *,
    cmap=None,
    vmin=None,
    vmax=None,
    name_col: str = "shapeName",
    max_pt: float = 5.0,
    fontweight: str = "bold",
    all_or_none: bool = True,
):
    """Label each district polygon in place, dropping labels that will not fit.

    Draws the largest districts first and skips any label that either does not
    fit its own polygon or would overlap one already placed -- at printed size
    the small south-eastern districts cannot hold their names, and fixed-size
    labels ran into each other. Text colour follows the fill's luminance.

    With all_or_none (the default), a partial result is discarded: either every
    district carries its name or none does. Labelling only the districts whose
    names happen to fit reads as though those districts were singled out for
    some substantive reason, which is worse than an unlabelled map.

    Returns the number of labels drawn. Call after the polygons are plotted.
    """
    fig = ax.get_figure()
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    ordered = frame.assign(_area=frame.geometry.area).sort_values(
        "_area", ascending=False
    )
    placed, annotations, drawn = [], [], 0
    eligible = sum(1 for _, r in ordered.iterrows()
                   if r.geometry is not None and not r.geometry.is_empty)
    for _, row in ordered.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        text = district_label(row[name_col])
        pt = fit_label_fontsize(ax, geom, text, max_pt=max_pt)
        if not pt:
            continue
        centroid = geom.centroid
        ann = ax.annotate(
            text,
            xy=(centroid.x, centroid.y),
            ha="center",
            va="center",
            fontsize=pt,
            fontweight=fontweight,
            color=label_text_color(row[value_col], cmap, vmin, vmax),
        )
        box = ann.get_window_extent(renderer).expanded(1.08, 1.15)
        # Drop the label unless it lies entirely inside its own district. Testing
        # against the bounding box is not enough: districts like Kgalagadi are
        # wide overall but narrow where the centroid sits, so a label can be
        # inside the box and still hang over the border into a neighbour.
        try:
            from shapely.geometry import box as shapely_box

            inv = ax.transData.inverted()
            (lx0, ly0), (lx1, ly1) = inv.transform([(box.x0, box.y0), (box.x1, box.y1)])
            label_poly = shapely_box(min(lx0, lx1), min(ly0, ly1),
                                     max(lx0, lx1), max(ly0, ly1))
            if not geom.contains(label_poly):
                ann.remove()
                continue
        except Exception:
            pass  # shapely unavailable: keep the label rather than lose it
        if any(box.overlaps(other) for other in placed):
            ann.remove()
            continue
        placed.append(box)
        drawn += 1
        annotations.append(ann)

    if all_or_none and drawn < eligible:
        for ann in annotations:
            ann.remove()
        return 0
    return drawn


def save_figure(
    path,
    fig=None,
    formats=FIGURE_FORMATS,
    png_dpi: int = PNG_PREVIEW_DPI,
    close: bool = False,
    **savefig_kwargs,
):
    """Write a figure as vector PDF (for the journal) plus a PNG preview.

    ``path`` may carry any extension; it is stripped and replaced. Parent
    directories are created if needed. Returns the list of paths written.
    """
    stem = Path(path).with_suffix("")
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig = fig or plt.gcf()

    written = []
    for fmt in formats:
        out = stem.with_suffix(f".{fmt}")
        kwargs = dict(savefig_kwargs)
        if fmt == "png":
            kwargs.setdefault("dpi", png_dpi)
        fig.savefig(out, format=fmt, **kwargs)
        written.append(out)

    if close:
        plt.close(fig)
    return written
