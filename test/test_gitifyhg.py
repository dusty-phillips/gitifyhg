from gitifyhg import gitifyhg, hgpull
from path import path as p

import sh

# FUNCARGS
# ========
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
    sh.hg.commit(message="a")
    sh.cd('..')

    # Now clone that repo and run gitify
    sh.hg.clone('hg_base', 'cloned_repo')
    sh.cd('cloned_repo')
    return tmpdir.joinpath('cloned_repo')


# ASSERTION HELPERS
# =================
def assert_empty_status():
    '''Assert that git and hg repos have no changes in them.'''
    assert len(sh.hg.status().stdout) == 0
    assert len(sh.git.status(short=True).stdout) == 0


def assert_commit_count(count):
    '''Assert that git and hg both have exactly ``count`` commits
    in their log.
    :param count: the number of commits expected in the git and hg logs'''
    assert sh.git.log(pretty='oneline').stdout.count(b'\n') == count
    assert sh.grep(sh.hg.log(), 'changeset:').stdout.count(b'\n') == count


# TESTS
# =====
def test_gitify(hg_repo):
    '''Ensure that gitifyhg has done it's job.'''
    gitifyhg()

    assert hg_repo.joinpath('.git').isdir()
    assert sh.git.alias().stdout == (
        b'hgpull = !gitifyhg hgpull\nhgpush = !gitifyhg hgpush\n')
    # There is one commit in both hg and git

    # both hg and git have nothing unexpected in the working directory
    assert_empty_status()
    assert_commit_count(1)


def test_basic_hg_pull(hg_repo):
    '''When commits are made on the upstream repo and there is nothing
    unexpected in the cloned hg or git repos, hg pull will sync everything up.
    '''
    gitifyhg()
    # Add a commit to the upstream repo
    hg_base = hg_repo.joinpath('../hg_base')
    sh.cd(hg_base)
    with hg_base.joinpath('test_file').open('a') as file:
        file.write('b')
    sh.hg.commit(message="b")

    sh.cd(hg_repo)
    hgpull()
    assert_empty_status()
    assert_commit_count(2)
