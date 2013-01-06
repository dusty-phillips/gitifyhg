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
This git remote allows you to do local development in a git repository and push 
changes to an upstream mercurial repository. It does this seamlessly and allows
pushing and pulling to named branches in the upstream repository.

It tries not to affect the upstream mercurial repo in any way. Thus, only a
restricted git workflow is available to you. 

gitifyhg does not rely on hg-git, and allows you to push and pull to and from
a mercurial repository from right inside git. You do not need to adapt your
git workflow in any way aside from cloning a gitifyhg url.

This is the most robust and usable git to hg bridge currently available. I have
studied as many other projects as I could find, and have covered as many use
cases as possible. It has a large test suite (over 650 lines and 33 tests),
better documentation. I've tested it on several large mercurial repositories
that break other projects.

That said, gitifyhg is not yet complete. Pull requests are higly desirable.
There are 7 tests currently marked as expected failures documenting low hanging
fruit if you want to help out with the project. Some of the features that
are not fully working include:

* anonymous branches are dropped, only the tip of a named branch is kept
* tags can be cloned and pulled, but not pushed
* bookmarks can be cloned and pushed, but not pulled reliably

However, if you're looking for a git-svn type of workflow that allows you to
clone mercurial repositories, work in local git branches, and rebase your
branches, you've found it. Further, all of these problems are fixable.
 
URLS
----
* `source <https://github.com/buchuki/gitifyhg>`_
* `issues <https://github.com/buchuki/gitifyhg/issues>`_
* `pypi package <https://pypi.python.org/pypi/gitifyhg/>`_
* `Dusty Phillips <https://archlinux.me/dusty>`_
* `Inspired by Felipe Contreras
  <https://felipec.wordpress.com/2012/11/13/git-remote-hg-bzr-2/>`_

Dependencies
------------
gitifyhg explicitly depends on:

* `path.py <https://github.com/jaraco/path.py>`_
* `Mercurial <http://mercurial.selenic.com/>`_

These packages will be installed automatically by ``easy_install``, 
``pip``, ``setup.py install``, or ``setup.py develop``.

gitifyhg also expects the following to be installed on your os:

* `python2 <http://python.org/>`_
* `git <http://git-scm.com/>`_

Supports
--------
``gitifyhg`` has been tested to run on cPython 2.6 and 2.7. Any python that
supports Mercurial should be supported. Sadly, this excludes both pypy and
cPython 3.

It has only been tested with Mercurial version 2.4.1. Because it uses
Mercurial's internal APIs, it IS likely to break with other versions.

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
gitifyhg is a git remote. Once installed, you can clone any Mercurial repo
using ::

    git clone gitifyhg::<any mercurial url>

Now run ``git branch -r`` to see the list of Mercurial branches. If it was
a named branch upstream, it will be named branches/<branchname> in git.
Bookmarks are referred to directly by their name. For now, I recommend only interacting with named branches.

``master`` automatically tracks the default branch. You can check out any
named mercurial branch using ::

  git checkout --track origin/branches/<branchname>

As a standard git practice, I recommend creating your own local branch
to work on. Then change to the tracked branch and ``git pull`` to get
upstream changes. Rebase your working branch onto that branch before pushing ::

  git checkout -b working_<branchname>
  # hack add commit ad naseum
  git checkout branches/<branchname>
  git pull
  git checkout working_<branchname>
  git rebase branches/<branchname>
  git checkout branches/<branchname>
  git merge working_<branchname>
  git push

You can create new named upstream branches by giving them the ``branches/``
prefix ::

  git checkout -b "branches/my_new_branch"
  # hack add commit
  git push --set_upstream origin branches/my_new_branch

And that's really it, you just have to use standard git commands and the remote
takes care of the details. Just don't do any octopus merges and you should be
good to go.

Note that Mercurial allows spaces in branch, bookmark, and tag names, while
git does not. To keep git from choking if upstream has spaces in names, gitifyhg
will replace them with three underscores and has the sense to convert between
the two formats when pushing and pulling.

If you have any trouble, please let me know via the issue tracker, preferably
with pull requests containing test cases.

Development
-----------
You can hack on gitifyhg by forking the
`github <https://github.com/buchuki/gitifyhg>`_ repository. All the code is
in the ``gitifyhg.py`` file, and tests are in the ``test`` directory.

I recommend developing in a `virtualenv <http://www.virtualenv.org/>`_ ::

  cd gitifyhg
  virtualenv -p python2.7 venv
  . venv/bin/activate
  python setup.py develop

There is currently a problem where if you have a development version of gitifyhg
in an active virtualenv and a stable version installed at the system level, git
will pick the system level gitifyhg regardless ofthe PATH setting in the
virtualenv. The only workaround I have found is to temporarily uninstall the
system virtualenv.

You can use `tox <http://tox.testrun.org/>`_ to set up a test environment ::

  pip install tox
  tox -e py27

Or install the test dependencies manually and run
`py.test <http://pytest.org/>`_ directly in the virtualenv ::

  pip install pytest
  pip install sh
  py.test -k <name of test>

If you want debugging information out of gitifyhg, set the GITIFYHG_DEBUG=on 
environment variable. This is done automatically if you are running the test
suite.

The gitifyhg remote is called by git and commands are passed on stdin.
Output is sent to stdout. The protocol is described at
https://www.kernel.org/pub/software/scm/git/docs/git-remote-helpers.html
The git remote prints INPUT and OUTPUT lines for each of these to help
introspect the protocol.

License
-------

gitifyhg is copyright 2012-2013 Dusty Phillips and is licensed under the
`GNU General Public License <https://www.gnu.org/licenses/gpl.html>`_