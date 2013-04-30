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

To the best of our knowledge, this is the most robust and usable git to hg bridge
currently available. It has a large test suite and better documentation than
the `alternatives we know about <https://github.com/buchuki/gitifyhg/wiki/List-of-git-hg-bridges>`_.
It has been tested on several large mercurial repositories (including that
of mercurial itself and the pypy repository) that break with various other
git-to-hg bridge projects and is used daily in normal workflow scenarios.

That said, gitifyhg is not yet complete. Some of the features that
are not fully working include:

* anonymous branches are dropped, only the tip of a named branch iqs kept
* remote branch and bookmark tracking is not 100% stable
* pushing octopus merges is not supported
* cloning mercurial branches that are subdirectories of other branches fails
* cloning duplicate case sensitive names on case insensitive filesystems (mac, windows) fails

However, if you are looking for a git-svn type of workflow that allows you to
clone mercurial repositories, work in local git branches, rebase those
branches and push them back to mercurial, you have found it. It works. Try it.
 
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
``gitifyhg`` has been tested to run on CPython 2.6 and 2.7. Any python that
supports Mercurial should be supported. Sadly, this excludes both pypy and
CPython 3.

``gitifyhg`` requires at least Mercurial 1.9, older versions are currently
not supported. We perform continuous testing against various Mercurial
versions ranging from 1.9 to 2.5. However, this does not completely rule
out the possibility of compatibility issues, so we recommend using Mercurial
2.4.x or 2.5.x, as this is what ``gitifyhg`` is primarily developed for.
Should you actually encounter any compatibility issues with any older or
newer Mercurial versions, please submit an issue.

It has been tested on Arch Linux and Mac OS X. In general it should
work equally well on other Unix-like operating systems like *BSD or Solaris.
All bets are off with Windows, but please let us know if it works or you fixed
it.

``gitifyhg`` explicitly depends on:

* `path.py <https://github.com/jaraco/path.py>`_
* `Mercurial <http://mercurial.selenic.com/>`_

These packages will be installed automatically by ``easy_install``, 
``pip``, ``setup.py install``, or ``setup.py develop``.

``gitifyhg`` also expects the following to be installed on your OS:

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
  # hack add commit ad nauseam
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
  git push --set-upstream origin branches/my_new_branch

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

By default, gitifyhg ignores branches that have been closed in Mercurial. This
supplies a substantial cloning speedup on large repos, and alleviates a few
issues we are still working out in conflicting branch names. If you would like
to clone a repository including closed branches, first set the
GITIFYHG_ALLOW_CLOSED_BRANCHES environment variable.

If you have any trouble, please let us know via the issue tracker, preferably
with pull requests containing test cases.

Communicating with Mercurial Users
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
One problem with using git to access Mercurial repos is that the sha identifiers
in the two DVCSs are different. This makes it difficult to discuss or share
patches on mailing lists or other mediums.

Gitifyhg alleviates this by storing Mercurial's sha1 identifiers in a git-notes
ref. If you need to discuss SHA1s with upstream Mercurial users, issue
the following commands::

  $ ls .git/refs/notes/
  hg  hg-ceda6818a39a022ef11ba5ee2d7964f57cb3accf
  # note the SHA1 above and adapt the following command
  git symbolic-ref refs/notes/hg refs/notes/hg-ceda6818a39a022ef11ba5ee2d7964f57cb3accf
  git config core.notesRef refs/notes/hg

From now on, your git-log output will include lines that look like the
following for each pulled ref::

  Notes (hg):
    e6eabc9d7e24f55e829d0848380f6645e57f4b6a

That is the Mercurial SHA1 identifier of the commit in question; you can paste
that into an e-mail or chat message to discuss a specific commit with other
users.

If somebody else mentions a commit by it's hg SHA1 identifier, you can search
for that commit in git using::

  git log --grep=<HGSHA1>

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
will pick the system level gitifyhg regardless of the PATH setting in the
virtualenv. The only workaround I have found is to temporarily uninstall the
system version.

If you want debugging information out of gitifyhg, set the DEBUG_GITIFYHG=on 
environment variable. This is done automatically if you are running the test
suite.

The gitifyhg remote is called by git and commands are passed on stdin.
Output is sent to stdout. The protocol is described at
https://www.kernel.org/pub/software/scm/git/docs/git-remote-helpers.html
The git remote prints INPUT and OUTPUT lines for each of these to help
introspect the protocol.

We expect pep8 compliance on contributions. If possible, enable highlighting
of pep8 violations in your editor before committing.

The gitifyhg mailing list is hosted on 
`Google groups <https://groups.google.com/group/gitifyhg>`_, but we
prefer the `issue tracker <https://github.com/buchuki/gitifyhg/issues>`_
for most development and decision-making related discussions.

Testing
=======

Tests are continuously run by Travis-CI: |BuildStatus|_

.. |BuildStatus| image:: https://secure.travis-ci.org/buchuki/gitifyhg.png
.. _BuildStatus: http://travis-ci.org/buchuki/gitifyhg

Note that testing has recently changed. We used to use `py.test <http://pytest.org/>`_
and `tox <http://tox.testrun.org/>`_ to run our tests. We've recently switched to
`sharness <https://github.com/mlafeldt/sharness>`_ both because it's easier to
test command-line tools with and because it is the same infrastructure used by
git itself.

To test with sharness, simply `cd test` and run `make`. You can run individual
test files with `./test-name.t`.

License
-------

gitifyhg is copyright 2012-2013 Dusty Phillips and is licensed under the
`GNU General Public License <https://www.gnu.org/licenses/gpl.html>`_

Credits
-------
Dusty Phillips is the primary author of ``gitifyhg``.

The current version was heavily inspired by and borrows code from Felipe Contreras's
`git-remote-hg <https://felipec.wordpress.com/2012/11/13/git-remote-hg-bzr-2/>`_
project.

Other contributors include (alphabetical order):

* Alex Sydell
* Jason Chu
* Jed Brown
* Max Horn
* Paul Price
