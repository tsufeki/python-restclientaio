# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.extlinks',
    'sphinx.ext.ifconfig',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinxcontrib.asyncio',
    'sphinx_autodoc_typehints',
]
if os.getenv('SPELLCHECK'):
    extensions += 'sphinxcontrib.spelling',
    spelling_show_suggestions = True
    spelling_lang = 'en_US'

source_suffix = '.rst'
master_doc = 'index'
project = 'restclientaio'
year = '2017'
author = 'tsufeki'
copyright = '{0}, {1}'.format(year, author)
version = release = '0.1.0'

default_role = 'py:obj'
pygments_style = 'trac'
templates_path = ['.']
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'aiohttp': ('https://aiohttp.readthedocs.io/en/stable', None),
}
extlinks = {
    'issue': ('https://github.com/tsufeki/python-restclientaio/issues/%s', '#'),
    'pr': ('https://github.com/tsufeki/python-restclientaio/pull/%s', 'PR #'),
}

# on_rtd is whether we are on readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only set the theme if we're building docs locally
    html_theme = 'sphinx_rtd_theme'

html_last_updated_fmt = '%b %d, %Y'
html_split_index = False
html_sidebars = {
   '**': ['searchbox.html', 'globaltoc.html', 'sourcelink.html'],
}
html_short_title = '%s-%s' % (project, version)

napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False

nitpick_ignore = [
    ('py:obj', 'R'),
    ('py:obj', 'S'),
    ('py:obj', 'T'),
    ('py:obj', 'U'),
    ('py:obj', 'D'),
    ('py:class', 'restclientaio.relation.Relation'),
    ('py:class', 'restclientaio.relation.RelationSerializer'),
    ('py:class', 'restclientaio.hydrator.BaseAnnotationDescriptor'),
]
