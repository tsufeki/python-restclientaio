========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis| |appveyor|
        | |coveralls|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|

.. |docs| image:: https://readthedocs.org/projects/python-restclientaio/badge/?style=flat
    :target: https://readthedocs.org/projects/python-restclientaio
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/tsufeki/python-restclientaio.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/tsufeki/python-restclientaio

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/tsufeki/python-restclientaio?branch=master&svg=true
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/tsufeki/python-restclientaio

.. |coveralls| image:: https://coveralls.io/repos/tsufeki/python-restclientaio/badge.svg?branch=master&service=github
    :alt: Coverage Status
    :target: https://coveralls.io/r/tsufeki/python-restclientaio

.. |version| image:: https://img.shields.io/pypi/v/restclientaio.svg
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/restclientaio

.. |commits-since| image:: https://img.shields.io/github/commits-since/tsufeki/python-restclientaio/v0.1.0.svg
    :alt: Commits since latest release
    :target: https://github.com/tsufeki/python-restclientaio/compare/v0.1.0...master

.. |wheel| image:: https://img.shields.io/pypi/wheel/restclientaio.svg
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/restclientaio

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/restclientaio.svg
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/restclientaio

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/restclientaio.svg
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/restclientaio


.. end-badges

Async ORM-like library for accessing RESTful APIs.

* Free software: BSD license

Installation
============

::

    pip install restclientaio

Documentation
=============

https://python-restclientaio.readthedocs.io/

Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
