from gitifyhg import gitifyhg
from path import path as p

import sh


def pytest_funcarg__hg_repo(request):
    tmpdir = p(str(request.getfuncargvalue('tmpdir')))
    hg_base = tmpdir.joinpath('hg_base')  # an hg repo to clone from
    hg_base.mkdir()  # could be on the above line if jaraco would release a bugfix
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
    return tmpdir.joinpath('cloned_repo')


def test_gitify(hg_repo):
    gitifyhg()

    assert hg_repo.joinpath('.git').isdir()
    assert sh.git.alias().stdout == (
        b'hgpull = !gitifyhg hgpull\nhgpush = !gitifyhg hgpush\n')
    print(sh.git.log(pretty='oneline'))
    assert sh.git.log(pretty='oneline').stdout.count(b'\n') == 1
