from gitifyhg import gitifyhg
from path import path as p

import sh


def pytest_funcarg__hg_repo(request):
    '''funcarg hg_repo that creates an hg repository in a temporary directory
    and clones it. This allows testing of pulls and pushes between
    repositories.

    :param request: The pytest_funcarg request object'''
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
    '''Ensure that gitifyhg has done it's job.'''
    gitifyhg()

    assert hg_repo.joinpath('.git').isdir()
    assert sh.git.alias().stdout == (
        b'hgpull = !gitifyhg hgpull\nhgpush = !gitifyhg hgpush\n')
    # There is one commit in both hg and git
    assert sh.git.log(pretty='oneline').stdout.count(b'\n') == 1
    assert sh.grep(sh.hg.log(), 'changeset:').stdout.count(b'\n') == 1
    # both hg and git have nothing unexpected in the working directory
    assert len(sh.hg.status().stdout) == 0
    assert len(sh.git.status(short=True).stdout) == 0
