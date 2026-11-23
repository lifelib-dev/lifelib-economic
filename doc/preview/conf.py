# Sphinx configuration for previewing the economic library's pages in this repository.
#
# lifelib builds its documentation with doc/source/conf.py. This file follows that
# file's settings as of lifelib-dev/lifelib@4133996 (lifelib v0.17.4), and
# _templates/llmodule.rst, _static/ and images/ are copies of lifelib's files. Only the
# economic library is built: build.py copies doc/source/libraries/economic/ into this
# folder, which stands in for lifelib's doc/source/, so the pages, the notebooks, the
# generated space pages and the gallery get the document names they have in lifelib.
# The settings that differ from lifelib's are marked "Preview:".
#
# Build with build.py, not with sphinx-build directly: build.py refreshes the copy of
# the pages first.

import os
import sys
import warnings

from sphinx.errors import NoUri
from sphinx.ext.intersphinx import missing_reference as _intersphinx_missing_reference
from sphinx.util import docname_join, logging

here = os.path.abspath(os.path.dirname(__file__))

# As in lifelib, each library folder is a top-level package for the API reference, so
# the spaces are documented as economic.BasicG2PP.G2PP and so on. The path is the same
# relative path as in lifelib, so the spaces come from this repository's draft.
sys.path.insert(0, os.path.abspath(here + "/../../lifelib/libraries"))

# Preview: autodoc imports each space's __init__.py. Leave no __pycache__ folders in the
# model folders.
sys.dont_write_bytecode = True

# -- General configuration ------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'nbsphinx',
    'nbsphinx_link',
    'sphinx_gallery.gen_gallery',
    'sphinx_design',
    'myst_parser',
    'sphinxcontrib.mermaid',
    # Preview: links to the rest of lifelib's documentation resolve to lifelib.io.
    'sphinx.ext.intersphinx',
]

templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

project = 'lifelib'
copyright = '2018-2026, lifelib Developers'
author = 'lifelib Developers'

# Preview: lifelib takes the version from the lifelib package, which this repository
# doesn't have. The title marks the pages as a preview of the draft.
version = 'economic draft'
release = version

language = 'en'

exclude_patterns = [
    '_build',
    '**.ipynb_checkpoints',
    'generated_examples/*/*.py',
    'generated_examples/*/*.ipynb'
]

pygments_style = 'sphinx'

todo_include_todos = True


# -- Options for HTML output ----------------------------------------------

html_theme = "pydata_sphinx_theme"
html_logo = "images/logo.png"
html_favicon = "_static/logo.svg"

html_title = "lifelib " + version

html_theme_options = {

    "header_links_before_dropdown": 8,
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/lifelib-dev/lifelib",
            "icon": "fab fa-github-square"
        }
    ],
    "external_links": [
        {"name": "Discussions", "url": "https://github.com/lifelib-dev/lifelib/discussions"}
    ],
}

html_static_path = ['_static']

html_last_updated_fmt = '%b %d, %Y'

html_sidebars = {
    "index": [],
    "notebooks": [],
    "download": [],
    "videos": [],
    "generated_examples/**": []
}

# Preview: lifelib's _templates/layout.html is not copied. It only adds lifelib.io's
# Google Analytics and Tag Manager tags.


# -- Options for Auto doc -----------------------------------------------
add_module_names = False

# -- Options for Auto summary -------------------------------------------
autosummary_generate = True

autodoc_default_options = {}

autodoc_member_order = 'bysource'


# -- Options for Gallery -------------------------------------------
sphinx_gallery_conf = {
    'ignore_pattern': '^(?!.*plot_)|simplelife',
    # Preview: lifelib's gallery collects every library's scripts from
    # ../../lifelib/libraries, with one subsection per library, in an order set by
    # 'subsection_order'. Here the economic library's scripts are the whole gallery,
    # and its README.txt is the gallery's header, so its pages keep their lifelib names,
    # generated_examples/economic/...
    'examples_dirs': '../../lifelib/libraries/economic',
    'gallery_dirs': 'generated_examples/economic',
    'backreferences_dir': None,
    'download_all_examples': False,
    'capture_repr': (),
    # Preview: the name of the sort key, where lifelib gives the class itself. Sphinx
    # can't cache a setting that holds a class, and warns about it (config.cache).
    'within_subsection_order': 'FileNameSortKey',
}

warnings.filterwarnings("ignore", category=UserWarning)

nbsphinx_requirejs_path = ''

mermaid_version = "11.4.1"

mermaid_height = "auto"


# -- Preview: links that leave the economic library -----------------------------------
#
# The pages link to other parts of lifelib's documentation, such as {ref}`create-a-project`
# and {mod}`appliedlife`, which are not built here. Intersphinx resolves those links to
# lifelib.io, the published documentation. lifelib.io also has the economic library's
# own pages, as last released, and a link must not resolve to those: the draft's pages are
# built here, so a link that only lifelib.io can resolve points to something the draft has
# changed or removed. Such a link warns instead, and renders as plain text. So does a link
# to a name in the economic package that neither the draft nor lifelib.io has, which
# lifelib's build would render as plain text without a warning.

intersphinx_mapping = {'lifelib': ('https://lifelib.io/', None)}

# Sphinx excludes {doc} links from intersphinx by default. Include them, so that a link
# to another library's page resolves too.
intersphinx_disabled_reftypes = []

_LIFELIB_IO = 'https://lifelib.io/'

_ECONOMIC_PAGES = (
    'libraries/economic/',
    'libraries/generated/economic.',
    'generated_examples/economic/',
    '_modules/economic/',
)

_logger = logging.getLogger(__name__)


def _resolve_outside_economic(app, env, node, contnode):
    """Resolve a link from lifelib.io, unless it leads to the economic library's pages."""
    domain, target = node.get('refdomain') or 'std', node.get('reftarget', '')
    query = node
    if domain == 'std' and node.get('reftype') == 'doc':
        # Intersphinx matches {doc} targets against document names only, so give it the
        # document name that the target, relative to the linking page, stands for.
        query = node.deepcopy()
        query['reftarget'] = docname_join(node['refdoc'], target)
    newnode = _intersphinx_missing_reference(app, env, query, contnode)
    if newnode is not None:
        uri = newnode.get('refuri', '')
        if not (uri.startswith(_LIFELIB_IO)
                and uri[len(_LIFELIB_IO):].startswith(_ECONOMIC_PAGES)):
            return newnode
        reason = 'lifelib.io has it, in the released economic library'
    elif domain == 'py' and (target == 'economic' or target.startswith('economic.')):
        reason = 'nor on lifelib.io'
    else:
        return None
    _logger.warning(
        '%s:%s reference target not found in the draft: %s (%s)',
        domain, node.get('reftype'), target, reason,
        location=node, type='ref', subtype='economic',
    )
    raise NoUri


def _scope_nbsphinx_link_rewriting_to_notebooks():
    """Keep nbsphinx's local-link rewriting off the MyST pages.

    nbsphinx registers ``RewriteLocalLinks`` with ``app.add_transform``, so it runs
    over every document rather than only over notebooks. Given a Markdown link that
    is a bare fragment -- ``[S1]: #uslib-term_life-s1``, the form the uslib citation
    blocks use -- it substitutes the current document's own filename (a workaround
    for sphinx-doc issues #11335 and #11336), lowercases the result and emits a
    ``std:ref`` to ``/<docname>.md#fragment``. No explicit MyST target matches that,
    so every such citation warns and renders as plain text. Because the node is
    replaced during the read phase, myst-parser's own resolver never sees it.

    Notebooks are what the transform is for, and it is left alone for them. Nothing
    else in this documentation needs it: MyST resolves its own ``file.md#fragment``
    links, and the one page that links to a notebook does so through ``:doc:``,
    which the std domain handles directly.
    """
    import nbsphinx

    original = nbsphinx.RewriteLocalLinks.apply

    def apply(self, *args, **kwargs):
        source = str(self.document.get("source") or "")
        if source.endswith((".ipynb", ".nblink")):
            return original(self, *args, **kwargs)

    nbsphinx.RewriteLocalLinks.apply = apply


def setup(app):
    app.add_css_file("custom-style.css")
    _scope_nbsphinx_link_rewriting_to_notebooks()
    # Preview: ahead of intersphinx's own handler, which has the default priority, 500.
    app.connect('missing-reference', _resolve_outside_economic, priority=400)
