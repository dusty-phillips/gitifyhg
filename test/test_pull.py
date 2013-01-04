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
from .helpers import (make_hg_commit, clone_repo, assert_git_count,
    assert_git_messages)


def test_basic_pull(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(hg_repo)
    make_hg_commit("b")
    sh.cd(git_repo)
    sh.git.pull()

    assert_git_count(2)
    assert_git_messages(["b", "a"])


def test_pull_from_named_branch(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.branch("feature")
    make_hg_commit("b")
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(hg_repo)
    sh.hg.update("feature")
    make_hg_commit("c")
    sh.cd(git_repo)
    sh.git.checkout("origin/branches/feature", track=True)
    assert_git_messages(["b", "a"])
    sh.git.pull()

    assert_git_count(3)
    assert_git_messages(["c", "b", "a"])


def test_pull_from_named_branch_with_spaces(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.branch("feature one")
    make_hg_commit("b")
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(hg_repo)
    sh.hg.update("feature one")
    make_hg_commit("c")
    sh.cd(git_repo)
    sh.git.checkout("origin/branches/feature___one", track=True)
    assert_git_messages(["b", "a"])
    sh.git.pull()

    assert_git_count(3)
    assert_git_messages(["c", "b", "a"])


@pytest.mark.xfail
def test_pull_from_bookmark(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.bookmark('feature')
    make_hg_commit("b")
    sh.hg.update(rev=0)
    sh.hg.bookmark('feature2')
    make_hg_commit("c")

    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    sh.git.checkout("origin/feature", track=True)
    assert_git_messages(["b", "a"])

    sh.cd(hg_repo)
    sh.hg.update('feature')
    make_hg_commit("d")
    sh.hg.update('feature2')
    make_hg_commit("e")

    sh.cd(git_repo)
    sh.git.pull()
    assert_git_messages(["d", "b", "a"])
    sh.git.checkout("origin/feature2", track=True)
    assert_git_messages(["c", "a"])
    sh.git.pull()
    assert_git_messages(["e", "c", "a"])
    # TODO: Pulling into a bookmark doesn't seem to be working. Find the
    # problem and fix.


@pytest.mark.xfail
def test_pull_from_bookmark_with_spaces(git_dir, hg_repo):
    assert False
    # TODO: Once pulling to a bookmark works, make sure it also works with spaces


def test_pull_tags(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(hg_repo)
    sh.hg.tag("tag1")
    sh.cd(git_repo)
    sh.git.pull()
    assert "tag1" in sh.git.tag()


def test_pull_tag_with_spaces(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(hg_repo)
    sh.hg.tag("tag one")
    sh.cd(git_repo)
    sh.git.pull()
    assert "tag___one" in sh.git.tag()
