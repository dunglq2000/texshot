"""
Build standalone TeX figures into SVG, PDF or JPEG for embedding into rST.

A figure with one page produces `name.svg` (`name.pdf`, `name.jpg`); a figure
with several pages produces `name-01.svg`, `name-02.svg`, ... (likewise for
JPEG). The outputs are written next to the `.tex` file, while auxiliary files
(`.aux`, `.log`, `.dvi`, ...) stay in a temporary directory.

Which files are built:

- with `-d DIR ...`: every standalone `.tex` file (one containing
  `\\documentclass`) under each directory, recursively;
- otherwise: the files listed in `figures.json` (in the current directory, or
  given with `-c`), whose keys are directories relative to the JSON file and
  whose values map an engine to file names:

      {"music": {"lualatex": ["notes"]}}

The engine of a file found with `-d` is read from a magic comment
`% !TEX program = lualatex`; without it, files using `fontspec` or `luacode`
are built with `lualatex`, the others with `pdflatex`.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from texshot import __version__

ENGINES = ("pdflatex", "lualatex")
DEFAULT_CONFIG = pathlib.Path("figures.json")


@dataclass
class Figure:
    tex: pathlib.Path   # absolute path to the `.tex` file
    engine: str

    @property
    def dir(self) -> pathlib.Path:
        return self.tex.parent

    @property
    def name(self) -> str:
        return self.tex.stem


class BuildError(Exception):
    pass


# ---------------------------------------------------------------- discovery

def strip_comments(content: str) -> str:
    # A '%' not preceded by a backslash starts a comment.
    return re.sub(r"(?<!\\)%.*", "", content)


def detect_engine(content: str) -> str:
    """Engine from `% !TEX program = ...`, else guessed from the packages."""
    m = re.search(r"^\s*%\s*!TEX\s+(?:TS-)?program\s*=\s*(\w+)", content, re.M | re.I)
    if m and m.group(1).lower() in ENGINES:
        return m.group(1).lower()
    if re.search(r"\\usepackage(\[[^\]]*\])?\{[^}]*\b(fontspec|luacode)\b", strip_comments(content)):
        return "lualatex"
    return "pdflatex"


def discover(directory: pathlib.Path) -> list[Figure]:
    """All standalone `.tex` files under `directory` (files without
    `\\documentclass`, e.g. chapters pulled in by `\\input`, are skipped)."""
    figures = []
    for tex in sorted(directory.rglob("*.tex")):
        content = tex.read_text(encoding="utf-8", errors="replace")
        if "\\documentclass" in strip_comments(content):
            figures.append(Figure(tex.resolve(), detect_engine(content)))
    return figures


def load_config(config: pathlib.Path) -> list[Figure]:
    data: dict[str, dict[str, list[str]]] = json.loads(config.read_text(encoding="utf-8"))
    figures = []
    for subdir, engines in data.items():
        for engine, names in engines.items():
            if engine not in ENGINES:
                raise BuildError(f"{config}: unsupported engine {engine!r} for {subdir}")
            for name in names:
                tex = (config.parent / subdir / f"{name}.tex").resolve()
                if not tex.is_file():
                    raise BuildError(f"{config}: file not found: {tex}")
                figures.append(Figure(tex, engine))
    return figures


# ---------------------------------------------------------------- building

def output_paths(fig: Figure, ext: str) -> list[pathlib.Path]:
    """Existing outputs `name.ext` and `name-NN.ext` of a figure."""
    pattern = re.compile(re.escape(fig.name) + r"(-\d+)?\." + ext + "$")
    return [p for p in fig.dir.glob(f"{fig.name}*.{ext}") if pattern.match(p.name)]


def is_up_to_date(fig: Figure, exts: list[str]) -> bool:
    mtime = fig.tex.stat().st_mtime
    for ext in exts:
        outputs = output_paths(fig, ext)
        if not outputs or min(p.stat().st_mtime for p in outputs) < mtime:
            return False
    return True


def remove_outputs(fig: Figure, ext: str) -> None:
    # Avoid stale `name-03.svg` when a figure shrinks from 3 pages to 1, etc.
    for p in output_paths(fig, ext):
        p.unlink()


def log_errors(log: pathlib.Path, limit: int = 6) -> str:
    """The first LaTeX error lines (`! ...` and the line after) of a log."""
    if not log.is_file():
        return "(no log file)"
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    picked = []
    for i, line in enumerate(lines):
        if line.startswith("!"):
            picked.extend(lines[i:i + 2])
            if len(picked) >= limit:
                break
    return "\n".join(picked[:limit]) or "\n".join(lines[-limit:])


def num_pages(log: pathlib.Path) -> int:
    """Number of pages from `Output written on name.dvi (N pages, ...)`."""
    m = re.search(r"Output written on .*?\((\d+) pages?", log.read_text(encoding="utf-8", errors="replace"), re.S)
    if not m:
        raise BuildError("no output was produced\n" + log_errors(log))
    return int(m.group(1))


def run_tex(fig: Figure, tmp: pathlib.Path, dvi: bool, verbose: bool) -> int:
    """Compile `fig` into `tmp` (DVI or PDF); return the number of pages."""
    if dvi:
        cmd = ["latex"] if fig.engine == "pdflatex" else ["lualatex", "--output-format=dvi"]
    else:
        cmd = [fig.engine]
    cmd += ["-interaction=nonstopmode", "-halt-on-error", f"-output-directory={tmp}", fig.tex.name]
    # Run in the figure's directory so that relative \input and images work.
    result = subprocess.run(cmd, cwd=fig.dir, stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, errors="replace")
    log = tmp / f"{fig.name}.log"
    if verbose:
        print(result.stdout)
    if result.returncode != 0:
        raise BuildError(f"{cmd[0]} failed\n" + log_errors(log))
    return num_pages(log)


def build_svg(fig: Figure, verbose: bool) -> list[pathlib.Path]:
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        pages = run_tex(fig, tmp, dvi=True, verbose=verbose)
        remove_outputs(fig, "svg")
        if pages == 1:
            out = f"--output={fig.dir / fig.name}.svg"
        else:
            out = f"--output={fig.dir / fig.name}-%2p.svg"
        cmd = ["dvisvgm", "--no-fonts", "--page=1-", out, str(tmp / f"{fig.name}.dvi")]
        result = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, errors="replace")
        if verbose:
            print(result.stderr)
        if result.returncode != 0:
            raise BuildError("dvisvgm failed\n" + result.stderr.strip())
    return output_paths(fig, "svg")


def build_pdf_jpeg(fig: Figure, pdf: bool, jpeg: bool, verbose: bool) -> list[pathlib.Path]:
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        run_tex(fig, tmp, dvi=False, verbose=verbose)
        built = tmp / f"{fig.name}.pdf"
        outputs = []
        if pdf:
            target = fig.dir / f"{fig.name}.pdf"
            shutil.copyfile(built, target)
            outputs.append(target)
        if jpeg:
            try:
                from pdf2image import convert_from_path
            except ImportError:
                raise BuildError("JPEG output needs the `pdf2image` package (and poppler)")
            images = convert_from_path(str(built), 300)
            remove_outputs(fig, "jpg")
            if len(images) == 1:
                names = [f"{fig.name}.jpg"]
            else:
                names = [f"{fig.name}-{i:02d}.jpg" for i in range(1, len(images) + 1)]
            for image, name in zip(images, names):
                image.save(fig.dir / name, "JPEG")
                outputs.append(fig.dir / name)
    return outputs


def build(fig: Figure, formats: list[str], force: bool, verbose: bool) -> tuple[Figure, str, str]:
    """Build one figure; return (figure, status, message)."""
    exts = [{"svg": "svg", "pdf": "pdf", "jpeg": "jpg"}[f] for f in formats]
    if not force and is_up_to_date(fig, exts):
        return fig, "skip", ""
    try:
        outputs = []
        if "svg" in formats:
            outputs += build_svg(fig, verbose)
        if "pdf" in formats or "jpeg" in formats:
            outputs += build_pdf_jpeg(fig, "pdf" in formats, "jpeg" in formats, verbose)
    except (BuildError, subprocess.SubprocessError, OSError) as e:
        return fig, "fail", str(e)
    return fig, "ok", ", ".join(p.name for p in sorted(outputs))


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="texshot",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--svg", action="store_true", help="build SVG (default if no format is given)")
    parser.add_argument("--pdf", action="store_true", help="build PDF")
    parser.add_argument("--jpeg", action="store_true", help="build JPEG (needs pdf2image)")
    parser.add_argument("-d", "--directory", nargs="+", type=pathlib.Path,
                        help="build every standalone .tex under these directories (recursively)\n"
                             "instead of the files listed in figures.json")
    parser.add_argument("-c", "--config", type=pathlib.Path, default=DEFAULT_CONFIG,
                        help=f"figures.json to use without -d (default: ./{DEFAULT_CONFIG})")
    parser.add_argument("-f", "--force", action="store_true", help="rebuild figures that are up to date")
    parser.add_argument("-j", "--jobs", type=int, default=1, help="number of figures built in parallel")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="print the TeX and dvisvgm output")
    args = parser.parse_args(argv)

    formats = [f for f in ("svg", "pdf", "jpeg") if getattr(args, f)] or ["svg"]

    try:
        if args.directory:
            figures = []
            for directory in args.directory:
                if not directory.is_dir():
                    raise BuildError(f"not a directory: {directory}")
                figures += discover(directory)
        else:
            if not args.config.is_file():
                raise BuildError(f"config not found: {args.config} (use -d to build a directory)")
            figures = load_config(args.config)
    except (BuildError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if not figures:
        print("Nothing to build.")
        return 0

    cwd = pathlib.Path.cwd()

    def show(path: pathlib.Path) -> str:
        try:
            return str(path.relative_to(cwd))
        except ValueError:
            return str(path)

    failed = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        jobs = [pool.submit(build, fig, formats, args.force, args.verbose) for fig in figures]
        for job in jobs:
            fig, status, message = job.result()
            label = f"{show(fig.tex)} [{fig.engine}]"
            if status == "ok":
                print(f"built   {label}: {message}")
            elif status == "skip":
                print(f"skipped {label}: up to date")
            else:
                print(f"FAILED  {label}", file=sys.stderr)
                print("        " + message.replace("\n", "\n        "), file=sys.stderr)
                failed.append(fig)

    print(f"{len(figures) - len(failed)}/{len(figures)} figures OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
