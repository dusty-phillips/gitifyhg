from gitifyhg import gitifyhg
from path import path as p

import sh

def test_gitify(tmpdir):
    tmpdir = p(str(tmpdir)) # I prefer path.py over py.path
    hg_base = tmpdir.joinpath('hg_base') # an hg repo to clone from
    hg_base.mkdir() # could be on the above line if jaraco would release a bugfix
    with hg_base.joinpath('test_file').open('w') as file:
        file.write('a')
    sh.cd(hg_base)
    sh.hg.init()
    sh.hg.add('test_file')
    sh.hg.commit('-m', 'a')
    sh.cd('..')

    # Now clone that repo and run gitify
    sh.hg.clone('hg_base', 'cloned_repo')
    sh.cd('cloned_repo')

    gitifyhg()

    cloned_repo_path = tmpdir.joinpath('cloned_repo')
    assert cloned_repo_path.joinpath('.git').isdir()
    print(sh.git.alias().stdout)
    print(type(sh.git.alias().stdout))
    assert sh.git.alias().stdout == (
        b'hgpull = !gitifyhg hgpull\nhgpush = !gitifyhg hgpush\n')

    