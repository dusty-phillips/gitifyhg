..
  Copyright 2012 Dusty Phillips

  This file is part of gitifyhg.
  gitifyhg is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.
 
  gitifyhg is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
 
  You should have received a copy of the GNU General Public License
  along with gitifyhg.  If not, see <http://www.gnu.org/licenses/>.


gitifyhg
========
This app allows you to do local development in a git repository and push your
changes to an upstream mercurial repository.

It tries not to affect the upstream mercurial repo in any way. Thus, only a
restricted git workflow is available to you. 

``gitifyhg`` communicates between the two repos using patches. These are
applied using ``hg export``, ``hg import``, ``git format-patch``,
and ``git am``.

Currently, gitifyhg does import upstream hg branches at all and it's primary
purpose is to keep master synced up with default in the mercurial repository.
It can rebase master onto the hg upstream, and it can push patches from master
to upstream.

URLS
----
* `source <https://github.com/buchuki/gitifyhg>`_
* `pypi package <https://pypi.python.org/pypi/gitifyhg/>`_
* `Dusty Phillips <https://archlinux.me/dusty>`_

Dependencies
------------
gitifyhg explicitly depends on:

* `path.py <https://github.com/jaraco/path.py>`_
* `sh <http://amoffat.github.com/sh/>`_
* `six <http://packages.python.org/six/>`_

These packages will be installed automatically by ``easy_install``, 
``pip``, ``setup.py install``, or ``setup.py develop``.

gitifyhg also expects the following to be installed on your os:

* `python <http://python.org/>`_
* `Mercurial <http://mercurial.selenic.com/>`_
* `git <http://git-scm.com/>`_

Supports
--------
``gitifyhg`` has been tested to run on:

* cPython 2.6
* cPython 2.7
* cPython 3.3
* pypy

It has only been tested on Arch Linux. I expect all Linux operating systems
to work fine with it and I suspect MacOS will also react well. All bets are
off with Windows, but please let me know if it works or you fixed it.

Install
-------
``gitifyhg`` is a properly designed Python package. You can get it from
`pypi <https://pypi.python.org>`_ using either ::

  pip install gitifyhg

or ::

  easy_install gitifyhg

gitifyhg works in a `virtualenv <http://www.virtualenv.org/>`_, but you're
probably just as well off to install it at the system level.

You can also install manually with ::

  git clone https://github.com/buchuki/gitifyhg.git
  python setup.py install

If you want to hack on it, use ``setup.py develop``, instead. In this case, you
probably **are** better off using a ``virtualenv``.

Instructions
------------
* Get your Mercurial default branch into a reasonable state and push all your
  changes.
* Run ``gitifyhg clone <mercurial repository url>``. This will create a new
  git repository just like ``git clone``. There will be a hidden ``.gitifyhg``
  directory in there that holds a working mercurial clone of the upstream repo
  and an intermediate directory for patches.
* ``cd repo_name``
* Set up your ``.gitignore``. You'll probably want to add ``.gitignore`` itself
  to the list of ignored files, as you don't want to tip upstream off that you
  are using a superior DVCS. You'll also want to add ``.gitifyhg``, as well
  as any patterns that are in the ``.hgignore`` from the original repo. You
  *can* symlink ``.gitignore`` to ``.hgignore`` provided the ``.hgignore``
  uses glob syntax. See http://www.selenic.com/mercurial/hgignore.5.html for
  more information.
* ``git checkout -b working_branch_name``. You *can* work directly on master,
  but I would avoid it to makes recovering from problems easier.
* Use git however you see fit. Use
  `git flow <http://jeffkreeftmeijer.com/2010/why-arent-you-using-git-flow/>`_,
  use ``rebase -i``, use ``commit --amend``, use ``add -p``.
  Use all the wonderful git tools that
  you have been aching to have available while being forced to work on mercurial
  repositories.
* At some point, you'll be ready to publish your changes to the hg repository.
  First run ``git hgrebase`` to pull in changes from mercurial ``default`` and
  have them appended to git ``master``. If you have patches on master,
  they will be rebased onto the new patches from upstream.
* Rebase your working branch onto ``master`` and then merge it into master (or
  use git-flow for more sensible commands)::
    
    git checkout working_branch_name
    git rebase master
    git checkout master
    git merge master

* ``git hgpush`` to push your patches upstream. It will present an error if
  there were upstream changes while you were doing the rebase step, so you
  don't have to worry too much about merge fail.

License
-------

gitifyhg is copyright 2012 Dusty Phillips and is licensed under the
`GNU General Public License <https://www.gnu.org/licenses/gpl.html>`_