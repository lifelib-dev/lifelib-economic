"""Build a preview of the economic library's documentation pages.

Run it with a Python environment that has this folder's requirements.txt::

    python doc/preview/build.py              # build, or rebuild what changed
    python doc/preview/build.py --clean      # build everything afresh
    python doc/preview/build.py --nitpicky   # also warn about every link that doesn't resolve
    python doc/preview/build.py --open       # then open the library's page in a browser

Other options go to sphinx-build, such as ``-W --keep-going`` to fail on warnings.

The script copies the pages, doc/source/libraries/economic/, into this folder, where
conf.py and two stub pages stand in for lifelib's doc/source/, and builds them with
Sphinx into _build/html/. Warnings about the copies name the pages in doc/source/, so
edit those, never the copies. The notebooks and the gallery scripts are read from the
library folder, lifelib/libraries/economic/, as in lifelib.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PAGES = ROOT / "doc" / "source" / "libraries" / "economic"
COPY = HERE / "libraries" / "economic"
GENERATED = HERE / "libraries" / "generated"   # autosummary's space pages
GALLERY = HERE / "generated_examples"          # sphinx-gallery's pages
BUILD = HERE / "_build"
HTML = BUILD / "html"

PROBLEM = re.compile(r"\b(WARNING|ERROR|CRITICAL):")


def copy_pages():
    """Make the copy of the pages equal to doc/source/libraries/economic/.

    Only the files that differ are written, so that Sphinx rereads only those.
    """
    wanted = {p.relative_to(PAGES) for p in PAGES.rglob("*") if p.is_file()}
    if COPY.exists():
        for path in sorted(COPY.rglob("*"), reverse=True):   # files before their folders
            if path.is_file() and path.relative_to(COPY) not in wanted:
                path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
    for rel in sorted(wanted):
        source, copy = PAGES / rel, COPY / rel
        data = source.read_bytes()
        if not copy.is_file() or copy.read_bytes() != data:
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes(data)


def clean():
    """Remove the copy of the pages, every generated page and the build output."""
    for path in (COPY, GENERATED, GALLERY, BUILD):
        shutil.rmtree(path, ignore_errors=True)
    for path in HERE.glob("sg_execution_times.*"):
        path.unlink()


def run_sphinx(options):
    """Run sphinx-build, show its output with the copies' paths mapped to doc/source/,
    and return its exit code and the warnings."""
    command = [sys.executable, "-m", "sphinx", "-b", "html",
               "-d", str(BUILD / "doctrees"), str(HERE), str(HTML), *options]
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
        text=True, encoding="utf-8", errors="replace")
    problems = []
    for line in process.stdout:
        line = line.replace(str(COPY), str(PAGES))
        sys.stdout.write(line)
        if PROBLEM.search(line):
            problems.append(line.rstrip("\n"))
    return process.wait(), problems


def main():
    parser = argparse.ArgumentParser(
        description="Build a preview of the economic library's documentation pages.",
        epilog="Other options go to sphinx-build.")
    parser.add_argument("--clean", action="store_true",
                        help="build everything afresh, gallery scripts included")
    parser.add_argument("-n", "--nitpicky", action="store_true",
                        help="warn about every link that doesn't resolve")
    parser.add_argument("--open", action="store_true",
                        help="open the library's page in a browser after the build")
    args, options = parser.parse_known_args()

    if args.clean:
        clean()
    copy_pages()
    # The space pages are written again by every build, so none outlives its space.
    shutil.rmtree(GENERATED, ignore_errors=True)
    if args.nitpicky:
        options.append("-n")

    code, problems = run_sphinx(options)

    print()
    if problems:
        print(f"{len(problems)} warning{'s' if len(problems) > 1 else ''} or error"
              f"{'s' if len(problems) > 1 else ''}:")
        for line in problems:
            print("  " + line)
        print()
    page = HTML / "libraries" / "economic" / "index.html"
    if page.is_file():
        print(f"The library's page: {page.as_uri()}")
        if args.open:
            webbrowser.open(page.as_uri())
    return code


if __name__ == "__main__":
    sys.exit(main())
