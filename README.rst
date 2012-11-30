gitifyhg
========

This little app does the dirty work of setting up a git repo inside an existing
hg repo so that you can work in git and push to remote hg repositories.
Don't ask me why you would want to do this. If you don't know,
I'm not gonna preach to you.

gitifyhg has been tested on Python 3.3. It might work on other interpreters.

You'll want to perform these steps before running gitify:

* ``pip install gitifyhg``. gitifyhg doesn't depend on ``hg-git`` because you
  will want it installed in the same environment as hg proper.

* Tell your ``~/.hgignore`` to ignore ``.git``. I suggest doing this in the
  global ignore so sensitive mercurial users don't get too tetchy about the
  fact that you think it's good to rewrite history.

* Add ``syntax: glob`` to the top of your ``.hgignore`` file and change
  patterns to glob format. ``gitifyhg`` will link your .hgignore to your
  ``.gitignore``, and git prefers the glob syntax.

* ``pip install gitifyhg``

Now you can run ``gitifyhg`` in any hg directory and a local git repo is
created. You can use the ``git hgpull`` and ``git hgpush`` commands to push
your changes into the remote hg repository.

A good workflow is to:

* Never commit to master. Create a new branch in git.
* When you are ready to merge that branch, first ``git hpull`` into master
* Rebase your branch onto master. If you don't know about ``git rebase -i``, learn.
* ``git hpush`` to push your changes upstream
* `hgview <http://www.logilab.org/project/hgview/>`_ is a terrific extension
  for viewing hg history. It even shows your hggit branch location.
  I recommend it over the git browsers because your colleagues are probably
  using hg branches.
* If you need to track other hg branches, bookmark it and track it using
  (I haven't tested this much)::
    hg bookmark hg/branchname -r branchname
    git branch --track branchname hg/branchname
