..
  Copyright 2012-2013 Dusty Phillips

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

``gitifyhg`` does not rely on hg-git, and allows you to push and pull to and from
a mercurial repository from right inside git. You do not need to adapt your
git workflow in any way aside from cloning a gitifyhg url.

This is the most robust and usable git to hg bridge currently available.
It has a large test suite (over 70 tests) and better
better documentation. I've tested it on several large mercurial repositories
that break with various other git-to-hg bridge projects. It has been tested
daily in normal workflow scenarios.

That said, gitifyhg is not yet complete. Some of the features that
are not fully working include:

* anonymous branches are dropped, only the tip of a named branch is kept
* remote bookmark support is sketchy
* remote branch tracking is not 100% stable

However, if you're looking for a git-svn type of workflow that allows you to
clone mercurial repositories, work in local git branches, rebase those
branches and push them back to mercurial,, you've found it. It works. Try it.
 
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
``gitifyhg`` has been tested to run on cPython 2.6 and 2.7. Any python that
supports Mercurial should be supported. Sadly, this excludes both pypy and
cPython 3.

``gitifyhg`` requires at least Mercurial 1.9, older versions are curently
not supported. We perform continuous testing against various Mercurial
versions ranging from 1.9 to 2.5. However, this does not completely rule
out the possibility of compatibility issues, so we recommend using Mercurial
2.4.x or 2.5.x, as this is what ``gitifyhg`` is primarily developed for.
Should you actually encounter any compatibility issues with any older or
newer Mercurial versions, please submit ann issue.

It has been tested on Arch Linux and Mac OS X. In general it should
work equally well on other Unix-like operating systems like *BSD or Solari.
All bets are off with Windows, but please let us know if it works or you fixed
it.

``gitifyhg`` explicitly depends on:

* `path.py <https://github.com/jaraco/path.py>`_
* `Mercurial <http://mercurial.selenic.com/>`_

These packages will be installed automatically by ``easy_install``, 
``pip``, ``setup.py install``, or ``setup.py develop``.

``gitifyhg`` also expects the following to be installed on your os:

* `python2 <http://python.org/>`_
* `git <http://git-scm.com/>`_

Install
-------
``gitifyhg`` is a properly designed Python package. You can get it from
`pypi <https://pypi.python.org>`_ using either ::

  pip install gitifyhg

or ::

  easy_install gitifyhg

``gitifyhg`` works in a `virtualenv <http://www.virtualenv.org/>`_, but you're
probably just as well off to install it at the system level.

You can also install ``gitifyhg`` manually with ::

  git clone https://github.com/buchuki/gitifyhg.git
  python setup.py install

If you want to hack on it, use ``setup.py develop``, instead. In this case, you
probably **are** better off using a ``virtualenv``.

Instructions
------------
``gitifyhg`` is a git remote. Once installed, you can clone any Mercurial repo
using ::

    git clone gitifyhg::<any mercurial url>

Now run ``git branch -r`` to see the list of Mercurial branches. If it was
a named branch upstream, it will be named branches/<branchname> in git.
Bookmarks are referred to directly by their name.
For now, we recommend only interacting with named branches.

``master`` automatically tracks the default branch. You can check out any
named mercurial branch using ::

  git checkout --track origin/branches/<branchname>

As a standard git practice, we recommend creating your own local branch
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

And that's really it, you just use standard git commands and the remote
takes care of the details. Just be cautious of incoming anonymous branches,
don't do any octopus merges and you should be set.

Caveats
~~~~~~~
Mercurial allows spaces in branch, bookmark, and tag names, while
git does not. To keep git from choking if upstream has spaces in names, gitifyhg
will replace them with three underscores and has the sense to convert between
the two formats when pushing and pulling.

Mercurial does not support lightweight tags. Tags in mercurial that get pushed
to the remote repo require an extra commit in he mercurial history. If you push
a lightweight tag, then gitifyhg will set a default user, date, and commit
message for you. However, if you create a heavyweight tag using
``git tag <tagname> --message="commit message"``, gitifyhg will use the commit
information associated with that tag when you run ``git push --tags``.

If you have any trouble, please let us know via the issue tracker, preferably
with pull requests containing test cases.

Development
-----------
You can hack on gitifyhg by forking the
`github <https://github.com/buchuki/gitifyhg>`_ repository. All the code is
in the ``gitifyhg.py`` file, and tests are in the ``test`` directory.

We recommend developing in a `virtualenv <http://www.virtualenv.org/>`_ ::

  cd gitifyhg
  virtualenv -p python2.7 venv
  . venv/bin/activate
  python setup.py develop

There is currently a problem where if you have a development version of gitifyhg
in an active virtualenv and a stable version installed at the system level, git
will pick the system level gitifyhg regardless ofthe PATH setting in the
virtualenv. The only workaround I have found is to temporarily uninstall the
system version.

If you want debugging information out of gitifyhg, set the GITIFYHG_DEBUG=on 
environment variable. This is done automatically if you are running the test
suite.

The gitifyhg remote is called by git and commands are passed on stdin.
Output is sent to stdout. The protocol is described at
https://www.kernel.org/pub/software/scm/git/docs/git-remote-helpers.html
The git remote prints INPUT and OUTPUT lines for each of these to help
introspect the protocol.

We expect pep8 compliance on contributions. If possible, enable highlighting
of pep8 violations in your editor before commiting.

The gitifyhg mailing list is hosted on 
`Google groups <https://groups.google.com/group/gitifyhg>`_, but we
prefer the `issue tracker <https://github.com/buchuki/gitifyhg/issues>`_
for most development and decision-making related discussions.

Testing
=======

Tests are continuously run by Travis-CI: |BuildStatus|_

.. |BuildStatus| image:: https://secure.travis-ci.org/buchuki/gitifyhg.png
.. _BuildStatus: http://travis-ci.org/buchuki/gitifyhg

You can use `tox <http://tox.testrun.org/>`_ to set up a local test environment ::

  pip install tox
  tox -e py27

Or install the test dependencies manually and run
`py.test <http://pytest.org/>`_ directly in the virtualenv ::

  pip install pytest
  pip install sh
  py.test -k <name of test>

You will probably find it convenient to pass the `tb=short` switch to py.test.

License
-------

gitifyhg is copyright 2012-2013 Dusty Phillips and is licensed under the
`GNU General Public License <https://www.gnu.org/licenses/gpl.html>`_

Credits
-------
Dusty Phillips is the primary author of ``gitifyhg``. The current version
was heavily inspired by and borrows code from Felipe Contreras's 
`git-remote-hg <https://felipec.wordpress.com/2012/11/13/git-remote-hg-bzr-2/>`_
project.

Max Horn and Jed Brown are also current maintainers of the project.

Jason Chu and Alex Sydell have also contributed to ``gitifyhg``.