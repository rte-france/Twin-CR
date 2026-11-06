Building DHTML Docs
===================

The GameMaster documentation uses `Sphinx <https://www.sphinx-doc.org/>`_ to
generate static HTML (sometimes referred to as **DHTML**) output. The
``docs/game_master`` directory already contains a ``conf.py`` and a set of
reStructuredText sources. Follow the steps below to preview or publish the docs.

1. **Install tooling**

   .. code-block:: bash

      python -m pip install --upgrade sphinx sphinx-rtd-theme

   The ``sphinx_rtd_theme`` dependency matches the default theme configured in
   ``conf.py``. You can substitute another theme by setting the
   ``SPHINX_HTML_THEME`` environment variable.

2. **Run ``sphinx-build``**

   From the repository root, execute:

   .. code-block:: bash

      sphinx-build -b html docs/game_master docs/_build/game_master

   The HTML output will be placed under ``docs/_build/gamemaster``. Open the
   generated ``index.html`` in a browser to explore the docs.

3. **Continuous editing**

   For a live-reload experience, install ``sphinx-autobuild`` and run:

   .. code-block:: bash

      sphinx-autobuild docs/game_master docs/_build/game_master

   This watches the ``docs/game_master`` tree and refreshes the browser when
   sources change.

Publishing Tips
---------------

* Commit the ``docs/game_master`` sources (``*.rst``, ``conf.py``) but not the
  generated HTML. CI pipelines can call ``sphinx-build`` and upload the
  contents of ``docs/_build/gamemaster`` to any static hosting solution.
* To integrate with Read the Docs, point the RTD project to
  ``docs/game_master/conf.py`` and enable the ``html`` builder.
* When documenting new Python APIs, extend :doc:`routers`, :doc:`domain`,
  :doc:`services`, or :doc:`utilities` with additional ``automodule`` sections
  so the rendered documentation stays comprehensive.
