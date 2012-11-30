'''This script does the dirty work of setting up a git repo inside an existing
hg repo so that you can work in git and push to hg. To make it work you'll need
to do several steps. These all oporate on the global hg and git configurations
so you only need to do it once. After that, you just need to run gitify.py in
an hg clone directory and all will be well.

* pip install hg-git (not in a virtualenv, since hg needs to find it)

* Enable a couple of hg extensions in your `~/.hgrc`:

    hggit =
    bookmarks =

* Tell your `~/.hgrc` to initialize hggit git repositiors in the same
    directory. Without this, .git will go in .hg, which is kinda silly.

    [git]
    intree=1

* Add a couple nifty aliases to your `.gitconfig`:

    [alias]
        hpull = !"hg pull ; hg gexport"
        hpush = !"hg gimport ; hg update ; hg push"

* Tell your `~/.hgignore to ignore '.git'

Now you can run python -m gitify in any hg directory and a git repo is created.

A good workflow is to:

* Never commit to master. Create a new branch in git.
* When you are ready to merge that branch, first `git hpull` into master
* Rebase your branch onto master.
    If you don't know about `git rebase -i`, learn.
* `git hpush` to push your changes upstream
* `hgview <http://www.logilab.org/project/hgview/>`_ is a terrific extension
    for viewing hg history. It even shows your hggit branch location.
    I recommend it over the git browsers because your colleagues are probably
    using hg branches.
* If you need to track other hg branches, bookmark it and track it using
    (I haven't tested this much):
    hg bookmark hg/branchname -r branchname
    git branch --track branchname hg/branchname
'''

import sh
from path import path as p
import sys

if not p('.hg').isdir():
    sys.exit('There is no .hg directory. Are you at the top of the repository?')

sh.git.init()
sh.hg.bookmark('hg/default', '-r', 'default')
sh.hg.gexport()
sh.git.branch('--track', 'master', 'hg/default')
sh.git.reset('--hard')
sh.git.config('core.excludesfile', p('.hgignore'))
with p('.git/info/exclude').open('a') as f:
    f.write('.hg*\n')
