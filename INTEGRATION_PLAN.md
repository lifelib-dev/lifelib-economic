# Plan: draft lifelib's economic library here, then merge it into lifelib

*Written 2026-11-21 and revised twice the same day: after this repository was renamed from
lifelib-g2pp to lifelib-economic, and when the decisions of §5 were made. Follows decision 6
in [PLAN.md](PLAN.md) §11. Based on lifelib v0.17.3 (lifelib-dev/lifelib@d44068e). lifelib's
`main` has since moved on to d17cfb7, with the fixes for #182 and #183, but nothing has
changed in `economic`'s folders, `pyproject.toml` or `doc/source/conf.py`. Steps A to C
were done on 2026-11-21 (§8).*

## 1. Goal

This repository is where lifelib's `economic` library is drafted before it is merged into
lifelib. Once it is merged:

- `lifelib.create("economic", ...)` gives `BasicHullWhite`, as it does now, plus
  `BasicG2PP`, the TVOG example `CashValue_ME_G2PP`, the input workbook they share, two
  notebooks and the library's test suite.
- The library's documentation pages are MyST Markdown, and describe the new models in the
  same form as `BasicHullWhite`.

**Decided on 2026-11-21**

1. **Name**: the repository and its local folder are named lifelib-economic. GitHub
   redirects the old URL.
2. **Mirrored path**: the library lives at `lifelib/libraries/economic/`, its path in
   lifelib, so that nothing is renamed when it moves.
3. **Base**: the library starts as a copy of lifelib's `economic` library. The draft then
   holds the whole library, and differs from lifelib only by what the merge will change.
4. **TVOG example**: `CashValue_ME_G2PP` goes into `economic` under its current name,
   instead of into `savings` as `CashValue_ME_EX5`. It shares `g2pp_input.xlsx` with
   `BasicG2PP`.

§5 records the seven decisions that followed.

## 2. What lifelib expects

A survey of lifelib's `main`, and what each finding means for the draft:

| Topic | lifelib convention | Consequence |
|---|---|---|
| Library layout | Model folders, notebooks and `plot_*.py` gallery scripts sit at the library root. `economic` holds `BasicHullWhite`, `hull-white-simulation.ipynb`, `plot_ex1` to `plot_ex3`, and `README.txt`, the heading of the library's gallery section. | `BasicG2PP/`, `CashValue_ME_G2PP/` and one `g2pp_input.xlsx` go to the library root. Both models find the workbook as `_model.path.parent / input_file`, so neither needs a change. `CashValue_ME_G2PP` keeps its tables in its own folder and needs nothing from `savings`. |
| Packaging | `setup.py` ships every `.py`, `.ipynb`, `.xlsx`, `.json`, `.csv`, `.pickle` and `.md` file under `lifelib/libraries`, except dot-folders and `_research/`, which `MANIFEST.in` also prunes. | No packaging change. Every file the two models, the notebooks and the tests need is of a type that ships; only `README.txt`, the gallery heading, stays out, as it does now (checked in step B). |
| Dependencies | `pyproject.toml` and `setup.py` both require only `modelx>=0.32`. The README and the FAQ say that lifelib installs nothing else, and leave pandas, numpy and openpyxl to the user. The `test` extra adds pytest, pandas, numpy and openpyxl. | Both models take the normal distribution from `scipy.stats`: `BasicG2PP`'s Validation space, and `formula_gmab_g2pp` in `CashValue_ME_G2PP`. Decision 1 makes scipy a dependency of lifelib. |
| modelx format | `BasicHullWhite` is serializer 5. Our two models are serializer 8, which modelx writes from 0.32. PyPI has 0.33.0, and CI installs modelx `main`. | lifelib's minimum, modelx 0.32, reads them. Check this once in a clean environment with modelx 0.32. |
| Tests | `testpaths` covers `lifelib/tests` and `lifelib/libraries/*/tests`. Seven libraries carry in-library suites, which `lifelib.create` copies with the library; `economic` has none yet. Shared names go in a uniquely named module such as `uk_registry.py`, because `conftest.py` and other common module names collide when several suites run together. The options include `--strict-markers` and `--strict-config`. The markers `slow`, `integration` and `unit` are registered, and slow tests run unless deselected with `-m "not slow"`. No repository-level test lists `economic`'s files. | Our suite becomes `economic/tests/`. Rename `helpers.py` to `g2pp_registry.py`, give the test modules names of their own, and keep only fixtures in `conftest.py`. Replace our `--runslow` option with the `slow` marker. This repository's `pytest.ini` copies lifelib's options, so the suite runs here as it will in lifelib. |
| Docs | Each library has an index page in `doc/source/libraries/<lib>/`: a toctree of models, a table of notebooks with Colab badges, and a table of contents. Each documented model has a page with an autosummary per space (template `llmodule.rst`). Pages are RST or MyST Markdown: `conf.py` loads `myst_parser` with no MyST extension enabled, and 321 pages are `.md`, among them the index pages of `ifrs17a`, `economic_curves` and the country libraries. `economic`'s pages are RST. Autosummary and sphinx-gallery write their pages at build time into `generated*/` folders, which git ignores. Notebooks are linked with `.nblink` files. The RST pages take their badges from `banners.rst`, and `notebooks.rst` lists every notebook. sphinx-gallery collects `plot_*.py` from every library folder, in file-name order. | Decision 7 rewrites `economic`'s pages in MyST, by the conventions in §7, which also lists the new pages and rows. New gallery scripts need no configuration, and generated pages are never committed. |
| Colab | Badges open notebooks at the `current` tag of lifelib-dev/lifelib. Near its top, after an overview, each notebook has a Colab badge and a cell that, on Colab, installs lifelib, runs `lifelib.create` and changes to the library folder. | Our notebooks get the same cell. They become runnable on Colab once a release moves the `current` tag. |
| Research notes | `libraries/<lib>/_research/` stays in the repository and out of the distributions (delib uses it). | A design note made from PLAN.md goes to `economic/_research/`. |
| Line endings | `.gitattributes` stores text files with LF and checks them out with LF on every platform. | The same `.gitattributes` goes to this repository's root, so files here match lifelib's byte for byte. |
| Releases | `doc/source/releases/relnotes_v0.17.rst` holds the v0.17 patch releases; v0.17.3 added twelve models to uslib. | Adding two models fits a v0.17.4 patch release (decision 5). |
| CI | Ubuntu, Windows and macOS × Python 3.10 to 3.14, on pushes to `main`, `feature/**` and `fix/**` and on pull requests. | Our suite takes about 21 s with its slow tests, which peak near 1 GB of memory. That fits the runners. |

## 3. How this repository mirrors lifelib

```
lifelib-economic/
├── lifelib/libraries/economic/      the library, merged into lifelib
│   ├── BasicHullWhite/ and the rest of lifelib's library, from the base commit
│   ├── BasicG2PP/, CashValue_ME_G2PP/, g2pp_input.xlsx
│   ├── g2pp-simulation.ipynb, g2pp-tvog.ipynb
│   ├── plot_ex4_g2pp_rate_fan.py, plot_ex5_g2pp_martingale.py
│   ├── tests/
│   └── _research/g2pp_design.md
├── doc/source/libraries/economic/   the library's docs pages, in MyST, merged into lifelib
├── scripts/                         bootstrap scripts
├── pytest.ini, .gitattributes       lifelib's settings, for running the suite here
└── README.md, PLAN.md, INTEGRATION_PLAN.md, LICENSE, .gitignore
```

Everything outside the two library folders stays here.

- **Base commit**: lifelib's `lifelib/libraries/economic/` and `doc/source/libraries/economic/`
  at d44068e are copied in with `git archive`, in a commit of their own that names the
  source commit: e292f34 here. Their blobs equal lifelib's.
- **MyST rewrite**: a later commit of its own rewrites the two RST pages, `index.rst` and
  `BasicHullWhite.rst`, as `index.md` and `BasicHullWhite.md`, without changing what they
  render (decision 7). From then on, `git diff <base> -- lifelib doc` shows exactly what the
  pull request to lifelib will change.
- **Changes in lifelib meanwhile**: the library folder last changed in lifelib in December
  2023, and the docs folder in May 2026, when `makedocs/` became `doc/`. Before the merge,
  `git diff d44068e main -- lifelib/libraries/economic doc/source/libraries/economic` in
  lifelib shows any change since the base. The paths match, so `git apply` here takes that
  patch as it is, except for a change to the two RST pages, which is ported by hand to their
  `.md` pages.
- **Merge**: in a lifelib clone, on a new branch, `git fetch <this repository> main`, then
  `git restore --source=FETCH_HEAD --staged --worktree -- lifelib/libraries/economic
  doc/source/libraries/economic`. In its default no-overlay mode, `git restore` makes both
  folders match the draft exactly, deletions included, so lifelib's two RST pages go and
  their `.md` pages come in. The pages keep their document names,
  `libraries/economic/index` and `libraries/economic/BasicHullWhite`, and with them their
  URLs and every link to them. lifelib's history gets the result as new commits, and the
  drafting history stays here.
- **Shared files**: files that other libraries use too (`banners.rst`, `notebooks.rst`,
  `libraries/index.rst`, the release notes, `README.rst`, the FAQ, `pyproject.toml`,
  `setup.py`) are edited only in lifelib, on the same branch, so the draft never holds stale
  copies of them.
- **`import lifelib` here**: when the repository root is on `sys.path`, as with
  `python -m pytest` run from the root, Python imports the root `lifelib/` folder as an
  empty namespace package instead of the installed lifelib. A check on 2026-11-21 found
  `lifelib.__file__` to be None in that case. So the tests find `BasicHullWhite` and
  appliedlife's curve file as sibling folders of the library, never through
  `import lifelib`, and `pytest.ini` leaves out lifelib's `pythonpath = ["."]`. The scripts
  run as files, which keeps the root off `sys.path`, and their `--source` option names the
  lifelib file to read.

## 4. Where each piece goes

| Now | After step A, at its lifelib path | Changes on the way (§6) |
|---|---|---|
| lifelib v0.17.3 | `lifelib/libraries/economic/`: `BasicHullWhite/`, `hull-white-simulation.ipynb`, `plot_ex1` to `plot_ex3`, `README.txt` | none |
| lifelib v0.17.3 | `doc/source/libraries/economic/`: `index.rst`, `BasicHullWhite.rst`, `hull-white-simulation.nblink` | the two pages rewritten as `index.md` and `BasicHullWhite.md` (decision 7); new rows and pages (§7) |
| `BasicG2PP/` | `lifelib/libraries/economic/BasicG2PP/` | docstring links |
| `CashValue_ME_G2PP/` | `lifelib/libraries/economic/CashValue_ME_G2PP/` | docstring links |
| `g2pp_input.xlsx` | `lifelib/libraries/economic/g2pp_input.xlsx`, read by both models | the Notes sheet names both models |
| `notebooks/g2pp_scenarios.ipynb` | `lifelib/libraries/economic/g2pp-simulation.ipynb`, named like `hull-white-simulation.ipynb` | Colab cell |
| `notebooks/tvog_example.ipynb` | `lifelib/libraries/economic/g2pp-tvog.ipynb` | Colab cell |
| `tests/` | `lifelib/libraries/economic/tests/` | registry module; module names; `slow` marker; sibling folders |
| `PLAN.md` | stays here; before the merge, `lifelib/libraries/economic/_research/g2pp_design.md` is made from it | without the drafting-only parts: phases, status and scripts |
| `pytest.ini` | stays here | lifelib's pytest options, with `testpaths` set to the library's suite |
| (new) | `.gitattributes`, kept here | lifelib's file |
| `scripts/` | stay here | they write into the library folder |
| `README.md`, `INTEGRATION_PLAN.md`, `LICENSE`, `.gitignore` | stay here | the README describes the mirror and the merge |

## 5. Decisions

Made on 2026-11-21, after the four in §1.

1. **scipy**: scipy becomes a dependency of lifelib, next to modelx, in `pyproject.toml`'s
   `dependencies` and `setup.py`'s `install_requires`, so installing lifelib installs it.
   Both models, the TVOG notebook and the tests keep `scipy.stats` as they are. lifelib's
   README and FAQ say that lifelib installs only modelx, so step D updates them too (§7).
2. **The `ESG` copy**: `CashValue_ME_G2PP` keeps `ESG`, its own copy of `G2PP`, so each
   model folder stays self-contained. `test_structure`, which fails when the two differ,
   runs in lifelib's CI with the rest of the library's suite.
3. **Gallery scripts**: `economic` gets `plot_ex4_g2pp_rate_fan.py` and
   `plot_ex5_g2pp_martingale.py`, after BasicHullWhite's three, so that G2++ appears in the
   docs gallery.
4. **Docs**: the pages in `doc/source/libraries/economic/` are drafted here, next to the
   models and in the same review, and built in lifelib at the merge, where any build errors
   show up (step D).
5. **Release**: v0.17.4, a patch release, as v0.17.3 was for uslib's models.
6. **This repository after the merge**: it stays the workspace for later `economic` work.
   Each round starts from a fresh base taken from lifelib (step F), so lifelib stays the
   source of truth.
7. **Docs in Markdown**: the library's pages are MyST Markdown, as 321 of lifelib's pages
   already are. Step A rewrites lifelib's two RST pages as `index.md` and
   `BasicHullWhite.md`, and the new pages are written as `.md`. §7 gives the conventions and
   what stays RST.

## 6. Changes to the contents

**In `BasicG2PP`**

- **Docstring links**: the model docstring links `:mod:`~BasicG2PP.G2PP``, which becomes
  `:mod:`~economic.BasicG2PP.G2PP``. `fund_logvar` cites "PLAN.md section 4" for the
  closed-form GMAB value; it links instead to `formula_gmab_g2pp`, whose docstring gives
  that formula.

**In `CashValue_ME_G2PP`**

- **Docstring links**: the model docstring links
  `:func:`~CashValue_ME_G2PP.Projection.result_tvog``, which becomes
  `~economic.CashValue_ME_G2PP.Projection.result_tvog`. The Projection docstring and the
  `esg` attribute say "BasicG2PP's G2PP space", which becomes a link to
  `economic.BasicG2PP.G2PP`.
- **`ESG`**: it carries the same `fund_logvar` docstring as `G2PP`. Rebuild it from the
  changed `G2PP`, so that `test_structure` still passes.
- **Upstream fixes**: lifelib fixed #182 and #183 on `main` after v0.17.3 (01e0561 and
  f89a631), and both issues are closed. Nothing needs carrying over: `CashValue_ME_G2PP`
  has its own `check_pv_net_cf` and no `formula_option_put`. Two of its docstrings said
  that EX4's `check_pv_net_cf` fails, which stops being true once v0.17.4 ships the fix;
  step C rewrote them, and removed a stale link to `scen_id` from `inv_return_mth`'s.

**In the workbook**: the Notes sheet says "Input to the BasicG2PP model"; it should name
both models.

**In the notebooks**

- **Paths** (step A): read the models as `mx.read_model("BasicG2PP")` and
  `mx.read_model("CashValue_ME_G2PP")`, from the library folder, instead of
  `Path.cwd().parent`. The TVOG notebook's mention of `tests/test_cashvalue.py` follows the
  module's rename.
- **Colab**: add lifelib's Colab badge and setup cell after the overview, as in
  `hull-white-simulation.ipynb`, with `lib = 'economic'`.
- **Text**: replace mentions of "the project folder" and of this repository's tests with
  the library folder and the library's suite.
- **Outputs**: re-run both notebooks, so their saved outputs come from the moved models,
  without the run times that nbconvert stores in each cell by default.

**In the tests**

- **Registry module**: `helpers.py` becomes `g2pp_registry.py`. Its `ROOT` becomes the
  library folder, found from the test file: `Path(__file__).resolve().parents[1]`.
- **Module names**: pytest imports each test module by its file name, so two suites with
  a `test_model.py` would clash in lifelib's run. Ours get the suffix `_g2pp`, as the
  country libraries' modules get theirs (`test_term_assurance_uk.py`):
  `test_input_g2pp.py`, `test_model_g2pp.py`, `test_closed_forms_g2pp.py`,
  `test_validation_g2pp.py` and `test_cashvalue_me_g2pp.py`. No lifelib suite uses our
  current names yet, so this prevents a clash rather than fixing one.
- **Fixtures**: `conftest.py` keeps only the fixtures. The `--runslow` option goes, and the
  registered `slow` marker takes its place.
- **Sibling folders**: the BasicHullWhite cross-check reads `BasicHullWhite/` next to
  `BasicG2PP/`, and the curve test reads `appliedlife/economic_data/risk_free_202312.xlsx`
  next to the library folder. Both exist in lifelib. In this repository and in a copy made
  by `lifelib.create("economic", ...)`, the curve test skips. `lifelib_path` goes.
- **BasicHullWhite warnings**: the cross-check filters a SyntaxWarning from BasicHullWhite's
  docstrings. The filter can go if those docstrings get `r` prefixes, which would be the
  draft's only edit to lifelib's existing files apart from the MyST rewrite.

**Design note** (step C): `_research/g2pp_design.md` holds PLAN.md's design sections and
decisions, with a note that it records the design and that the model folders are the
source of truth. The tests' docstrings cited PLAN.md's sections and phases; they now cite
the design note's sections, which keep PLAN.md's numbers, with the optional extensions in
§9 in place of the phases.

## 7. Documentation

| File | Written | Change |
|---|---|---|
| `doc/source/libraries/economic/index.md` | here | rewritten from `index.rst` in step A. In step C, "one primary model" becomes three: add `BasicG2PP` and `CashValue_ME_G2PP` to the toctree, both notebooks to the notebooks table and the hidden toctree, and the workbook, notebooks and gallery scripts to the contents table |
| `doc/source/libraries/economic/BasicHullWhite.md` | here | rewritten from `BasicHullWhite.rst` in step A, and otherwise unchanged |
| `doc/source/libraries/economic/BasicG2PP.md` | here | new model page, in the form of `BasicHullWhite.md`: an overview with the dynamics, the exact monthly step, the curve fit and its no-extrapolation rule, the bond fund, the CE scenario, the Excel input and the pass rule of the Validation space (condensed from PLAN.md §4 and §5); then an autosummary of `G2PP` and of `Validation` |
| `doc/source/libraries/economic/CashValue_ME_G2PP.md` | here | new model page: what it changes in `savings`' `CashValue_ME_EX4`, how `result_tvog` computes TVOG and its standard error, and the closed-form check; then an autosummary of `Projection`, with `ESG` pointing to the `G2PP` page |
| `doc/source/libraries/economic/g2pp-simulation.nblink`, `g2pp-tvog.nblink` | here | new, pointing to the notebooks |
| `lifelib/libraries/economic/plot_ex4_g2pp_rate_fan.py`, `plot_ex5_g2pp_martingale.py` | here | new gallery scripts (decision 3); they run in the docs build in about a second each |
| `doc/source/banners.rst`, `doc/source/notebooks.rst` | lifelib | Colab badges for the two notebooks, and rows in the notebook list; both files stay RST |
| `doc/source/libraries/index.rst` | lifelib | the `economic` row says "Basic Hull-White model"; it should name the G2++ model and the TVOG example too. Its toctree entry `economic/index.rst` still finds `index.md`, as Sphinx drops the suffix, but becomes `economic/index.md`, like the `ifrs17a` and `economic_curves` entries next to it |
| `README.rst`, `doc/source/quickstart/faq.md` | lifelib | scipy in the README's list of requirements, and in the FAQ's answer to "What Python packages do I need to use lifelib?", which says that lifelib installs only modelx (decision 1) |
| `doc/source/releases/relnotes_v0.17.rst` | lifelib | a v0.17.4 section: the two models, the library's pages in Markdown, and scipy as a dependency |

The autosummary pages of the new spaces and the gallery pages are written by each build,
into folders git ignores, so they need no work.

### Writing the pages in MyST

The pages follow lifelib's existing MyST pages, except in how they write autosummaries:

- **Module targets**: each page opens with a `{module}` directive, as the `ifrs17a` and
  `economic_curves` pages do. The targets, `economic`, `economic.BasicHullWhite` and those
  of the new models, keep the `:mod:` links elsewhere in lifelib working, such as those in
  `notebooks.rst` and the v0.6.0 release notes.
- **Autosummary**: each summary goes in an `{eval-rst}` block that begins with
  `.. currentmodule::` and names the spaces relative to it, as in `~HullWhite`. Autosummary
  finds the pages to generate by scanning the sources for RST directives, so a MyST
  `{autosummary}` gets no page, and a relative name fails to import when only a MyST
  `{module}` sets the module. The full names that `economic_curves` uses work but warn
  (`autosummary.import_cycle`): lifelib's v0.17.3 build has seven such warnings, one per
  `economic_curves` page.
- **Math**: the `{math}` directive and role. lifelib enables no MyST extension, and enabling
  `dollarmath` would change `conf.py` for every page, including 62 included library pages
  that print amounts such as US$8.73.
- **Badges**: Markdown image links, as on `ifrs17a`'s index page, since MyST has no RST
  substitutions such as `|modelx badge|`. `banners.rst` keeps its substitutions for the RST
  pages.
- **Everything else**: roles as `{doc}`, `{ref}` and `{mod}`; directives such as
  `{toctree}`, `{seealso}` and `{todo}` as fenced blocks; console examples as `python` code
  blocks; tables as pipe tables.

What stays RST: the model docstrings, which autodoc reads as RST; `README.txt` and the text
of the `plot_*.py` scripts, which sphinx-gallery reads as RST, as in all eight gallery
libraries; and lifelib's shared pages in the table above. The `.nblink` files are JSON.

**Trial, 2026-11-21**: `index.rst` and `BasicHullWhite.rst`, rewritten by these rules and
built with Sphinx 8.2.3 and myst-parser 5.1.0 beside the RST originals, rendered the same
text and the same links, with no warnings. The module index listed `economic` and
`economic.BasicHullWhite`, and an RST toctree entry `economic/index.rst` found `index.md`.

**Trial of step C, 2026-11-21**: the draft's library and pages were built with lifelib's
Sphinx settings and extensions, including nbsphinx and sphinx-gallery but not the theme,
with placeholder pages for the `savings` and `appliedlife` pages that the new pages link
to. The build gave no warning except the `config.cache` warning that lifelib's
`sphinx_gallery_conf` causes in any build. It generated the autosummary pages of `G2PP`,
`Validation`, `Projection` and `HullWhite`, both notebook pages and the five gallery pages,
whose scripts ran. A nitpicky build found no unresolved link on the three pages; its other
notes come from docstrings, mostly links to `savings` pages that exist only in lifelib.
All 61 formulas on the pages parse.

## 8. Steps

Steps A to C happen here, on `main`. Steps D and E happen in lifelib, on a branch
`feature/economic-g2pp`, which CI tests on every push.

| Step | Work | Done when |
|---|---|---|
| A. Mirror lifelib | 1. Copy the base (§3) in its own commit. 2. Add lifelib's `.gitattributes` and renormalize the line endings. 3. Rewrite `index.rst` and `BasicHullWhite.rst` as `index.md` and `BasicHullWhite.md` (§7), in a commit that changes their form only. 4. `git mv` our files to their places in §4, rename the registry module and the notebooks, point `scripts/`, the tests and the notebooks at the library folder, switch to the `slow` marker, and write `pytest.ini` from lifelib's options. 5. Update README.md and PLAN.md's layout. | the base's blobs equal lifelib's at d44068e; `git diff <base> -- lifelib doc` shows the two pages replaced by `.md` pages and otherwise only added files; the suite passes with lifelib's options, slow tests included; both notebooks run from the library folder |
| B. Adapt the contents | The changes of §6, and the gallery scripts (decision 3). Re-run the notebooks. | the suite passes, both here and in a copy of the library folder on its own, as `lifelib.create` makes it; both models read and run with modelx 0.32 in a clean environment |
| C. Draft the docs | The pages of §7 that are written here, in MyST, and `_research/g2pp_design.md`. | `index.md` lists every model, notebook and script of the library; the new pages cover every space of the two models |
| D. Merge | Bring in any change lifelib made since the base (§3), then restore the two folders from the draft. Add scipy to `pyproject.toml`'s `dependencies` and `setup.py`'s `install_requires`, edit the shared files of §7, build the docs, and open a pull request to `main`. | the docs build without new warnings, the `economic` pages render as in the trial (§7), and both notebook pages render; CI passes on all 15 jobs |
| E. Release | Merge; release v0.17.4 with the release notes; move the `current` tag, so the Colab badges open the new notebooks. | `pip install lifelib --upgrade` then `lifelib.create("economic", ...)` gives the three models |
| F. Afterwards | Replace the base here with lifelib's library at the merge commit (decision 6), so the next round starts from what was released. Its pages are MyST by then, so later rounds need no rewrite. | this repository's library equals lifelib's on `main` |

**Done**

- Step A, on 2026-11-21. The base is e292f34, the MyST rewrite 5ead21b and the move
  096e189. Every blob of the base equals lifelib's at d44068e. With lifelib's options, 106
  tests pass and the curve test skips, in about 24 s. Both notebooks run from the library
  folder and reproduce their saved outputs.
- Step B, on 2026-11-21, in d570680 (docstring links), 6303897 (Notes sheet), e81d43f
  (gallery scripts) and 242fc46 (notebooks). The suite gives the same result here, in a
  copy of the library made of the files lifelib ships, and with modelx 0.32.0 in a clean
  conda environment (Python 3.12, pandas 3.1). The re-run notebooks reproduce their
  outputs. BasicHullWhite's docstrings are unchanged, so the cross-check keeps its
  warning filter (§6).
- Step C, on 2026-11-21, in f972513 (`CashValue_ME_G2PP`'s docstrings), 398863d (the two
  model pages), 1d809cc (the index page and the notebook links) and 9908760 (the design
  note and the tests' citations). `index.md` lists the three models, the three notebooks
  and the five gallery scripts. The new pages cover the four spaces: `G2PP`, `Validation`
  and `Projection` by autosummary, and `ESG` by a pointer to the `G2PP` page. The trial
  build is in §7, and the suite gives the same result as after step B. The design note
  stays out of the files lifelib ships, which are otherwise unchanged.

## 9. Risks

| Risk | Mitigation |
|---|---|
| `CashValue_ME_G2PP`'s `ESG` and `BasicG2PP`'s `G2PP` drift apart. | `test_structure` compares every formula, and runs in lifelib's CI with the rest of the library's suite (decision 2). |
| lifelib's `economic` files change while the draft is open. | The base commit names lifelib's commit. Step D's diff finds any change, and the patch applies here because the paths match; a change to the two RST pages is ported by hand to their `.md` pages. |
| `import lifelib` in this repository finds the root `lifelib/` folder instead of the installed lifelib. | The tests use sibling folders, and the scripts run as files with `--source` (§3). |
| The docs pages can't be built here in full. | The trial builds of steps A and C built them with lifelib's settings and placeholder pages (§7); step D builds them in lifelib before the pull request (decision 4). |
| The MyST pages render differently from the RST pages they replace. | The trial rendered both with the same text and links, and step D's build checks the final pages. |
| Sphinx autodoc imports each space's `__init__.py` as a Python module, and our files contain `("IOSpec", 1)` and `("Interface", ...)` References. | Step C's trial build imported and documented all four spaces without a warning; step D's build checks it in lifelib. |
| nbsphinx executes notebooks that have no outputs, which would make the docs build slow. | Both notebooks are committed with outputs. |
| The slow tests peak near 1 GB on each of 15 CI jobs. | They take about 5 s; if a runner runs short of memory, CI can deselect them with `-m "not slow"`. |
| lifelib's minimum modelx is 0.32, and our models were written by 0.33. | In step B, the whole suite passed with modelx 0.32.0 in a clean environment. |
| A user who creates only `economic` lacks appliedlife's curve file. | The one test that reads it skips; both models need nothing outside the library. |
