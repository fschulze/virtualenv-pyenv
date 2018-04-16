virtualenv-pyenv
================

Create shims to wrap `virtualenv`_ for use with `pyenv`_.


Why?
----

With `pyenv-virtualenv`_ one can not create virtualenvs in any directory.


Usage
-----

Once you have one or more Python versions installed, use one of them to run ``shims.py``.
It will download and unpack virtualenv in the current directory.
Lastly it will create small shell scripts in the current directories ``bin`` sub directory for each Python x.y version.
Either add that ``bin`` directory to you ``PATH``,
or copy the scripts somewhere that is already in your ``PATH``.

.. _`virtualenv`: https://pypi.org/project/virtualenv
.. _`pyenv`: https://github.com/pyenv/pyenv
.. _`pyenv-virtualenv`: https://github.com/pyenv/pyenv-virtualenv
