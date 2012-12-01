# Copyright 2012 Dusty Phillips

# This file is part of gitifyhg.

# gitifyhg is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gitifyhg is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gitifyhg.  If not, see <http://www.gnu.org/licenses/>.


from gitifyhg import gitifyhg, hgpull, hgpush
from path import path as p

import sh


# FUNCARGS
# ========
def pytest_funcarg__hg_repo(request):
    '''funcarg hg_repo that creates an hg repository in a temporary directory
    and clones it. This allows testing of pulls and pushes between
    repositories. The current working directory will also be set to the
    cloned repo.

    :param request: The pytest_funcarg request object.
    :return: a path object pointing at the repo that was cloned into. It also
        has an ``hg_base`` attribute that is a path object pointing at the
        upstream repo that was cloned from.'''
    tmpdir = p(str(request.getfuncargvalue('tmpdir')))
    hg_base = tmpdir.joinpath('hg_base')  # an hg repo to clone from
    hg_base.mkdir()
    sh.cd(hg_base)
    write_to_test_file('a')
    sh.hg.init()
    sh.hg.add('test_file')
    sh.hg.commit(message="a")
    sh.cd('..')

    # Now clone that repo and run gitify
    sh.hg.clone('hg_base', 'cloned_repo')
    cloned_repo = tmpdir.joinpath('cloned_repo')
    cloned_repo.hg_base = hg_base
    sh.cd('cloned_repo')
    return cloned_repo


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


# HELPERS
# =======
def write_to_test_file(message, filename='test_file'):
    '''Append the message to the 'test_file' file in the current working
    directory or filename if it was passed. This is normally done to stage a
    commit in hg or git.

    :param message: Something to be appended to the test file. Use \\n
        judiciously.
    :param filename: A filename to commit to. If unsupplied, test_file
        will be updated.'''
    with p(filename).open('a') as file:
        file.write(message)


# THE ACTUAL TESTS
# ================
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
    sh.cd(hg_repo.hg_base)
    write_to_test_file('b')
    sh.hg.commit(message="b")

    sh.cd(hg_repo)
    hgpull()
    assert_empty_status()
    assert_commit_count(2)


def test_basic_hg_push(hg_repo):
    '''When commits are made to the local git master branch and there is nothing
    unexpected upstream or in the hg repo, and there are no extra branches in
    git, hg push will sync everything up.'''
    gitifyhg()
    # Add a git commit to the local git repo
    write_to_test_file('b')
    sh.git.commit(message='b', all=True)

    hgpush()
    assert_empty_status()
    assert_commit_count(2)

    sh.cd(hg_repo.hg_base)
    assert sh.grep(sh.hg.log(), 'changeset:').stdout.count(b'\n') == 2


def test_pull_push_no_merge(hg_repo):
    '''Test the common case that commits have been made locally and upstream.
    The local commits must be made on a separate branch, cause master gets
    mucked around by hg-git. This test illustrates how things *should* be done
    as much as it is testing things are working.'''
    gitifyhg()

    # make a change to the first file (upstream)
    sh.cd(hg_repo.hg_base)
    write_to_test_file('b')
    sh.hg.commit(message="b")

    # make a change on a new branch in the git repo
    sh.cd(hg_repo)
    sh.git.branch('c')
    sh.git.checkout('c')
    write_to_test_file('c', 'c')
    sh.git.add('c')
    sh.git.commit(message='c')

    # At this point, git and hg are out of sync. Know about it.
    # Know that if you ``hgpush`` now, your commits on ``c`` would
    # end up in your hg repo on an unnamed but bookmarked branch.

    hgpull()
    # Know that hgpull checked out master and reset master hard to upstream
    sh.git.checkout('c')
    sh.git.rebase('master')
    sh.git.checkout('master')
    sh.git.merge('c')  # It's not a real merge, it's fastforward
    hgpush()

    assert_empty_status()
    assert_commit_count(3)

    sh.cd(hg_repo.hg_base)
    assert sh.grep(sh.hg.log(), 'changeset:').stdout.count(b'\n') == 3
