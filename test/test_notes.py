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


import pytest
import sh
from .helpers import (make_hg_commit, make_git_commit, clone_repo,
    assert_git_count, assert_git_messages, assert_git_notes)


def test_basic_clone_with_notes(git_dir, hg_repo):
    '''Ensures that a clone of an upstream hg repository with only one branch
    and a couple commits contains the appropriate structure.'''

    sh.cd(hg_repo)
    make_hg_commit("b")
    hgsha1s = sh.hg.log(template='{node}\n').stdout.splitlines()

    git_repo = clone_repo(git_dir, hg_repo)

    assert git_repo.exists()
    assert git_repo.joinpath('test_file').exists()
    assert git_repo.joinpath('.git').isdir()

    sh.cd(git_repo)
    assert_git_count(2)
    assert_git_messages(['b', 'a'])
    assert len(sh.git.status(short=True).stdout) == 0
    assert_git_notes(hgsha1s)


def test_basic_pull_with_notes(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(hg_repo)
    make_hg_commit("b")
    hgsha1s = sh.hg.log(template='{node}\n').stdout.splitlines()
    sh.cd(git_repo)
    sh.git.pull()

    assert_git_count(2)
    assert_git_messages(["b", "a"])
    assert_git_notes(hgsha1s)


def test_pull_rename_remote(git_dir, hg_repo):
    git_repo = git_dir.joinpath("hg_repo")
    sh.git.init(git_repo)
    sh.cd(git_repo)
    sh.git.remote("add", "--fetch", "the-remote", "gitifyhg::" + hg_repo)
    sh.git.pull("the-remote", "master")
    assert_git_count(1)
    sh.cd(hg_repo)
    make_hg_commit("b")
    make_hg_commit("c")
    sh.cd(git_repo)
    sh.git.fetch("the-remote")
    assert_git_count(3, ref="the-remote/master")

    sh.cd(hg_repo)
    make_hg_commit("d")
    hgsha1s = sh.hg.log(template='{node}\n').stdout.splitlines()

    sh.cd(git_repo)
    sh.git.remote("rename", "the-remote", "new-remote-name")
    sh.git.pull("new-remote-name", "master")
    assert_git_count(4)
    assert_git_notes(hgsha1s)


@pytest.mark.xfail
def test_simple_push_updates_notes(hg_repo, git_dir):
    """Issue #30: don't know how to apply notes without triggering error
       message when there are no other commits in fast-import stream"""
    git_repo = clone_repo(git_dir, hg_repo)
    make_git_commit("b")
    sh.git.push()
    sh.cd(hg_repo)
    hgsha1s = sh.hg.log(template='{node}\n').stdout.splitlines()
    sh.cd(git_repo)
    fetch_stderr = sh.git.fetch().stderr
    assert not 'error' in fetch_stderr
    assert_git_count(2, ref='origin')
    assert_git_notes(hgsha1s)


def test_simple_push_updates_notes_after_contentful_pull(hg_repo, git_dir):
    """Issue #30: check that notes are eventually applied"""
    git_repo = clone_repo(git_dir, hg_repo)
    make_git_commit("b")
    sh.git.push()
    sh.cd(git_repo)
    fetch_stderr = sh.git.fetch().stderr
    assert not 'error' in fetch_stderr
    assert_git_count(2, ref='origin')
    sh.cd(hg_repo)
    sh.hg.update()
    make_hg_commit("c")
    hgsha1s = sh.hg.log(template='{node}\n').stdout.splitlines()
    sh.cd(git_repo)
    fetch_stderr = sh.git.pull().stderr
    assert not 'error' in fetch_stderr
    assert_git_count(3, ref='origin')
    assert_git_notes(hgsha1s)
