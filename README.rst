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

This tiny app does the dirty work of setting up a git repo inside an existing
hg repo so that you can work in git and push to remote hg repositories.

``gitifyhg`` has been tested on Python 3.3, 2.7, and 2.6. It might work on other
interpreters.

It tries not to affect the upstream mercurial repo in any way. Thus, only a
restricted git workflow is available to you. Right now, only the most basic
tasks can be accomplished; you can sync up mercurial default with git master.
This allows a similar pipeline to ``git-svn``, but I'm still testing things with
branches and the like.

The git and hg repositories operate on the same working files. This can allow
stuff to get out of sync, where ``hg status`` shows changes that are already
committed in git and vice versa. Try not to use mercurial at all.

URLS
----
* `source <https://github.com/buchuki/gitifyhg>`_
* `pypi package <https://pypi.python.org/pypi/indico/>`_
* `Dusty Phillips <https://archlinux.me/dusty>`_

Dependencies
------------
gitifyhg explicitly depends on:

* `path.py <https://github.com/jaraco/path.py>`_
* `sh <http://amoffat.github.com/sh/>`_
* `six <http://packages.python.org/six/>`_

These packages will be installed automatically by `easy_install`, 
`pip`, or `setup.py install`.

gitifyhg also expects the following to be installed on your os:

* `Mercurial <http://mercurial.selenic.com/>`_
* `git <http://git-scm.com/>`_
* `hg-git <http://hg-git.github.com/>`_


Install
-------

``gitifyhg`` is a properly designed Python package. You can get it from
`pypi <https://pypi.python.org>`_ using either ::

  pip install gitifyhg

or ::

  easy_install gitifyhg

gitifyhg works in a `virtualenv `http://www.virtualenv.org/>`_, but you're
probably just as well off to install it at the system level.

You can also install manually with ::

  git clone https://github.com/buchuki/gitifyhg.git
  python setup.py install

If you want to hack on it, use ``setup.py develop``, instead. In this case, you
probably **are** better off using a ``virtualenv``.

Instructions
------------

In addition to installing the hg-git dependency (I expect you have hg and 
git installed already), you'll want to perform these steps before running
gitifyhg:

* Tell your ``~/.hgignore`` to ignore ``.git``. I suggest doing this in the
  global ignore so sensitive mercurial users don't get too tetchy about the
  fact that you think it's good to rewrite history. It would be possible to
  make ``gitifyhg`` automatically add .git to the repo's .hgignore, but I have
  tried to keep gitifyhg from requiring major changes to the repo.

* Clone an hg repo if you don't have one you want to work in.

* Add ``syntax: glob`` to the top of your ``.hgignore`` file and change
  patterns to glob format. ``gitifyhg`` will link your .hgignore to your
  ``.gitignore``, and git prefers the glob syntax. If you choose not to do this,
  you may have to unlink the gitignore

Now you can run ``gitifyhg`` in any hg directory and a local git repo is
created. You can use the ``git hgpull`` and ``git hgpush`` commands to push
your changes into the remote hg repository.

These commands are rather dangerous. They basically try to sync up the hg
default and git master branches. When you run ``git hgpull`` changes are pulled
into ``default`` from the upstream mercurial repository and git master is
hard reset to point at it. It's probably better if you don't have changes on
master that you didn't want obliterated.

``git hgpush`` does basically the opposite, it tries to sync up the hg default
branch with whatever commits have been pushed onto master, and then pushes it
to the remote repository.

A good workflow is to:

* Never commit to master. Create a new branch in git.
* When you are ready to merge that branch, first ``git hgpull`` to sync master
  with the upstream mercurial repository.
* Rebase your working branch onto master. If you don't know about
  ``git rebase -i``, learn.
* Merge your working branch into master and delete the working branch. If you
  don't delete it, hg-git will create a new bookmark for that git branch. That
  won't hurt anything, but if you have git branches that have changes on them
  that are not merged into master, those changes will also be pulled into
  mercurial. This is probably not good because you probably don't want those
  commits pushed upstream as an unnamed branch.
* ``git hpush`` to push your changes upstream.
* `hgview <http://www.logilab.org/project/hgview/>`_ is a terrific extension
  for viewing hg history. It even shows your hggit branch location.
  I recommend it over the git browsers because your colleagues are probably
  using hg branches.
* ``hg strip`` from the mercurial queues extension is useful if your git
  commits foul up your hg repository. ``git reset --hard master`` is also
  necessary sometimes. I'm hoping to make this more seamless in the future.

License
-------

gitifyhg is copyright 2012 Dusty Phillips and is licensed under the
`GNU General Public License <https://www.gnu.org/licenses/gpl.html>`_