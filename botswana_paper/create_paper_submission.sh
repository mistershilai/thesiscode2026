#!/bin/bash
# Build the upload archive(s) for a paper.
#
# Usage:
#   ./create_paper_submission.sh MAINFILE [TARGET]
#
# MAINFILE: base name of the main LaTeX file (e.g. "main", without extension).
# TARGET:   siopt | arxiv | all   (default: all)
#
# siopt  -> ships .tex + .bib + .bbl + .pdf + cls/bst/figures separately.
#           Archive: <NAME>-siopt.tar.gz; folder: submission/siopt/final/.
# arxiv  -> latexpand flattens .bbl into .tex (single source file).
#           Archive: <NAME>-arxiv.tar.gz (under build/arxiv-archive/).
#
# Requires latexmk, latexpand. .bbl and .pdf must already exist (run
# `latexmk -pdf MAINFILE.tex` first). The -pdf flag is required when no
# global ~/.latexmkrc forces pdf mode; otherwise latexmk defaults to DVI
# and fails on PDF figures.

set -eu

usage() {
    echo "Usage: $0 MAINFILE [TARGET]"
    echo "  TARGET: siopt | arxiv | all   (default: all)"
    exit 1
}

[ $# -lt 1 ] && usage
NAME="${1%.*}"
TARGET="${2:-all}"

ORIG_DIR="$(pwd)"

[ -f "$NAME.tex" ] || { echo "Error: $NAME.tex not found"; exit 1; }
[ -f "$NAME.bbl" ] || { echo "Error: $NAME.bbl not found. Run 'latexmk $NAME.tex' first."; exit 1; }
[ -f "$NAME.pdf" ] || { echo "Error: $NAME.pdf not found. Run 'latexmk $NAME.tex' first."; exit 1; }

copy_aux_files() {
    # Copy class/style/clo files actually loaded by the active build (via
    # latexmk's .fls record), plus the .bst recorded in .blg. Filtering this
    # way avoids dragging in sibling style files from other paper versions
    # (e.g. llncs.cls, splncs04.bst for an IPCO branch).
    local dest="$1"

    if [ -f "$NAME.fls" ]; then
        # Pull local cls/sty/clo names from the .fls file.
        grep -E "^INPUT .*\.(cls|sty|clo)$" "$NAME.fls" \
            | awk '{print $2}' | sed 's|^\./||' | sort -u \
            | while read -r f; do
                case "$f" in /*) continue ;; esac   # skip system paths
                [ -f "$f" ] && cp "$f" "$dest/"
            done
    else
        echo "    Warning: $NAME.fls not found; copying all local cls/sty/clo files."
        for ext in cls sty clo; do
            for f in *.$ext; do
                [ -f "$f" ] || continue
                cp "$f" "$dest/"
            done
        done
    fi

    if [ -f "$NAME.blg" ]; then
        local bst
        bst="$(grep -E "^The style file: " "$NAME.blg" | sed 's|^The style file: ||')"
        [ -n "$bst" ] && [ -f "$bst" ] && cp "$bst" "$dest/"
    else
        for f in *.bst; do
            [ -f "$f" ] || continue
            cp "$f" "$dest/"
        done
    fi
}

copy_assets() {
    # Copy figures/ and data/ subtrees into $1 if they exist.
    local dest="$1"
    if [ -d figures ]; then
        mkdir -p "$dest/figures"
        # Vector art (what INFORMS wants for every plot).
        cp figures/*.pdf "$dest/figures/" 2>/dev/null || true
        # Genuine images (photographs, the hand-drawn logistics diagram) stay
        # raster. A .png with no .pdf twin is a plot that was never regenerated
        # as vector -- ship it so the build still works, but say so.
        for f in figures/*.png figures/*.jpg figures/*.jpeg; do
            [ -f "$f" ] || continue
            if [ -f "${f%.*}.pdf" ]; then
                continue   # vector twin already copied
            fi
            case "$f" in
                *.png) echo "    Warning: $f has no .pdf twin (INFORMS rejects bitmap plots)" ;;
            esac
            cp "$f" "$dest/figures/"
        done
    fi
    if [ -d data ]; then
        mkdir -p "$dest/data"
        cp data/*.csv "$dest/data/" 2>/dev/null || true
    fi
}

build_siopt() {
    echo "==> Building SIOPT archive..."
    local DEST="submission/siopt/final"
    rm -rf "$DEST"
    mkdir -p "$DEST"

    # Ship the unflattened .tex, the .bib, the .bbl, and the PDF.
    cp "$NAME.tex" "$NAME.bbl" "$NAME.pdf" "$DEST/"
    for f in *.bib; do
        [ -f "$f" ] || continue
        cp "$f" "$DEST/"
    done
    # Other .tex sources the main file inputs (e.g. definitions.tex).
    # Skip the main file itself and any sibling top-level drafts (main_*.tex).
    for f in *.tex; do
        [ -f "$f" ] || continue
        [ "$f" = "$NAME.tex" ] && continue
        case "$f" in ${NAME}_*.tex) continue ;; esac
        cp "$f" "$DEST/"
    done
    copy_aux_files "$DEST"
    copy_assets "$DEST"

    # Sanity-check: archive must build standalone.
    ( cd "$DEST" \
        && latexmk -C "$NAME.tex" >/dev/null 2>&1 \
        && latexmk -pdf -quiet "$NAME.tex" >/dev/null \
        && latexmk -c "$NAME.tex" >/dev/null 2>&1 \
        && rm -f "$NAME.synctex.gz" "$NAME.thm" )

    ( cd "$DEST" \
        && COPYFILE_DISABLE=1 tar -czf "$ORIG_DIR/$NAME-siopt.tar.gz" * )

    echo "    Folder:  $DEST/"
    echo "    Archive: $NAME-siopt.tar.gz"
}

build_arxiv() {
    echo "==> Building arXiv archive (flattened .bbl)..."
    local TEMP="build/arxiv-archive"
    rm -rf "$TEMP"
    mkdir -p "$TEMP"

    latexpand --expand-bbl "$NAME.bbl" "$NAME.tex" > "$TEMP/$NAME.tex"
    copy_aux_files "$TEMP"
    copy_assets "$TEMP"

    # Sanity-check: archive must build standalone.
    ( cd "$TEMP" \
        && latexmk -pdf -quiet "$NAME.tex" >/dev/null \
        && latexmk -c "$NAME.tex" >/dev/null 2>&1 \
        && rm -f "$NAME.synctex.gz" "$NAME.thm" "$NAME.pdf" )

    ( cd "$TEMP" \
        && COPYFILE_DISABLE=1 tar -czf "$ORIG_DIR/$NAME-arxiv.tar.gz" * )

    echo "    Folder:  $TEMP/"
    echo "    Archive: $NAME-arxiv.tar.gz"
}

case "$TARGET" in
    siopt) build_siopt ;;
    arxiv) build_arxiv ;;
    all)   build_siopt; build_arxiv ;;
    *)     usage ;;
esac

echo "Done."
