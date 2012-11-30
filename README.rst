gitifyhg
========

This tiny app does the dirty work of setting up a git repo inside an existing
hg repo so that you can work in git and push to remote hg repositories. If you
don't want to do this, it's because you don't understand how amazing git really
is.

gitifyhg has been tested on Python 3.3. It might work on other interpreters.

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

These packages will be installed automatically by `easy_install`, 
`pip`, or `setup.py install`.

gitifyhg also expects the following to be installed on your os:

* `Mercurial <http://mercurial.selenic.com/>`_
* `git <http://git-scm.com/>`_
* `hg-git <http://hg-git.github.com/>`_


Install
-------

gitifyhg is a properly designed Python package. You can get it from
`pypi <https://pypi.python.org>`_ using either ::

  pip install gitifyhg

or ::

  easy_install gitifyhg

gitifyhg works in a `virtualenv `http://www.virtualenv.org/>`_, but you're
probably just as well off to install it at the system level.

You can also install manually by ::

  git clone https://github.com/buchuki/gitifyhg.git
  python setup.py install

If you want to hack on it, use ``setup.py develop`` instead. In this case, you
probably **are** better off using ``virtualenv``

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

A good workflow is to:

* Never commit to master. Create a new branch in git.
* When you are ready to merge that branch, first ``git hpull`` into master
* Rebase your working branch onto master. If you don't know about
  ``git rebase -i``, learn.
* ``git hpush`` to push your changes upstream.
* `hgview <http://www.logilab.org/project/hgview/>`_ is a terrific extension
  for viewing hg history. It even shows your hggit branch location.
  I recommend it over the git browsers because your colleagues are probably
  using hg branches.
* If you need to track other hg branches, bookmark it and track it using
  (I haven't tested this much)::
    hg bookmark hg/branchname -r branchname
    git branch --track branchname hg/branchname
