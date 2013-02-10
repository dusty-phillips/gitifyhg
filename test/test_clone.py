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
from path import path as p
from .helpers import (make_hg_commit, clone_repo, assert_git_count,
    assert_git_messages, write_to_test_file)


def test_basic_clone(git_dir, hg_repo):
    '''Ensures that a clone of an upstream hg repository with only one branch
    and a couple commits contains the appropriate structure.'''

    sh.cd(hg_repo)
    make_hg_commit("b")

    git_repo = clone_repo(git_dir, hg_repo)

    assert git_repo.exists()
    assert git_repo.joinpath('test_file').exists()
    assert git_repo.joinpath('.git').isdir()

    sh.cd(git_repo)
    assert_git_count(2)
    assert_git_messages(['b', 'a'])
    assert len(sh.git.status(short=True).stdout) == 0


def test_clone_relative(git_dir, hg_repo):
    '''Make sure it doesn't fail if not cloning an absolute path'''
    sh.cd(hg_repo)
    make_hg_commit("b")

    sh.cd(git_dir)
    git_repo = clone_repo(git_dir, hg_repo.relpath())

    assert git_repo.exists()
    assert git_repo.joinpath('test_file').exists()
    assert git_repo.joinpath('.git').isdir()
    with git_repo.joinpath(sh.glob('.git/hg/*/clone/.hg/hgrc')[0]).open() as file:
        assert hg_repo in file.read()

    sh.cd(git_repo)
    assert_git_count(2)
    assert_git_messages(['b', 'a'])
    assert len(sh.git.status(short=True).stdout) == 0

    sh.git.pull()


def test_clone_linear_branch(git_dir, hg_repo):
    '''One branch after the other, no multiple parents.'''
    sh.cd(hg_repo)
    sh.hg.branch("featurebranch")
    make_hg_commit("b")

    git_repo = clone_repo(git_dir, hg_repo)

    assert git_repo.exists()
    assert git_repo.joinpath('test_file').exists()
    assert_git_count(1)
    assert_git_messages(['a'])
    assert sh.git.branch(remote=True).stdout == """  origin/HEAD -> origin/master
  origin/branches/featurebranch
  origin/master
"""

    sh.git.checkout('branches/featurebranch')

    with git_repo.joinpath('test_file').open() as file:
        assert file.read() == "a\nb"
    assert_git_count(2)
    assert_git_messages(['b', 'a'])


def test_clone_simple_branch(git_dir, hg_repo):
    '''Two divergent branches'''
    sh.cd(hg_repo)
    sh.hg.branch("featurebranch")
    make_hg_commit("b")
    sh.hg.update("default")
    make_hg_commit("c", "c")

    clone_repo(git_dir, hg_repo)

    assert_git_count(2)
    assert_git_messages(['c', 'a'])
    sh.git.checkout("origin/branches/featurebranch")
    assert_git_messages(['b', 'a'])
    assert_git_count(2)


def test_clone_branch_with_spaces(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.branch("feature branch")
    make_hg_commit("b")

    git_repo = clone_repo(git_dir, hg_repo)

    assert git_repo.exists()
    assert git_repo.joinpath('test_file').exists()
    assert_git_count(1)
    assert_git_messages(['a'])
    assert sh.git.branch(remote=True).stdout == """  origin/HEAD -> origin/master
  origin/branches/feature___branch
  origin/master
"""

    sh.git.checkout('branches/feature___branch')

    with git_repo.joinpath('test_file').open() as file:
        assert file.read() == "a\nb"
    assert_git_count(2)
    assert_git_messages(['b', 'a'])


def test_clone_merged_branch(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.branch("featurebranch")
    make_hg_commit("b")
    sh.hg.update("default")
    make_hg_commit("c", "c")
    sh.hg.merge('featurebranch')
    sh.hg.commit(message="merge")
    make_hg_commit("d")

    clone_repo(git_dir, hg_repo)

    assert_git_count(5)
    assert_git_messages(['d', 'merge', 'c', 'b', 'a'])
    sh.git.checkout("origin/branches/featurebranch")
    assert_git_messages(['b', 'a'])
    assert_git_count(2)


@pytest.mark.xfail
def test_clone_anonymous_branch(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b")
    sh.hg.update(rev=0)
    make_hg_commit("c")

    sh.cd(git_dir)
    result = sh.git.clone("gitifyhg::" + hg_repo)
    assert "more than one head" in result.stderr
    # TODO: 'more than one head' is the correct response for now, but a more
    # appropriate result would be to clone the extra commits, perhaps naming
    # the branch anonymous/<sha> or something. assert False to mark an expected
    # failure. (Using test cases as todos is a good thing.)
    assert False


@pytest.mark.xfail
def test_clone_named_and_anonymous_branch(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.branch("featurebranch")
    make_hg_commit("b")
    make_hg_commit("c")
    sh.hg.update(rev=1)
    make_hg_commit("d")
    sh.hg.update('default')
    make_hg_commit("e")

    sh.cd(git_dir)
    result = sh.git.clone("gitifyhg::" + hg_repo)
    assert "more than one head" in result.stderr

    sh.cd(git_dir.joinpath('hg_base'))
    result = sh.git.branch(remote=True)
    print result.stdout
    assert result.stdout == """  origin/HEAD -> origin/master
  origin/branches/featurebranch
  origin/master
"""

    # TODO: same more than one head issue as in test_clone_anonymous_branch
    assert False


def test_clone_bookmark(hg_repo, git_dir):
    sh.cd(hg_repo)
    sh.hg.bookmark("featurebookmark")
    make_hg_commit("b")

    clone_repo(git_dir, hg_repo)

    result = sh.git.branch(remote=True)
    print result.stdout
    assert result.stdout == """  origin/HEAD -> origin/master
  origin/featurebookmark
  origin/master
"""
    sh.git.checkout('origin/featurebookmark')
    assert_git_count(2)
    sh.git.checkout('master')
    assert_git_count(2)


def test_clone_bookmark_with_spaces(hg_repo, git_dir):
    sh.cd(hg_repo)
    sh.hg.bookmark("feature bookmark")
    make_hg_commit("b")

    clone_repo(git_dir, hg_repo)

    result = sh.git.branch(remote=True)
    print result.stdout
    assert result.stdout == """  origin/HEAD -> origin/master
  origin/feature___bookmark
  origin/master
"""
    sh.git.checkout('origin/feature___bookmark')
    assert_git_count(2)
    sh.git.checkout('master')
    assert_git_count(2)


def test_clone_divergent_bookmarks(hg_repo, git_dir):
    sh.cd(hg_repo)
    sh.hg.bookmark("bookmark_one")
    make_hg_commit("b")
    sh.hg.update(rev=0)
    make_hg_commit("c")
    sh.hg.bookmark("bookmark_two")
    make_hg_commit("d")

    clone_repo(git_dir, hg_repo)

    result = sh.git.branch(remote=True)
    print result.stdout
    assert result.stdout == """  origin/HEAD -> origin/master
  origin/bookmark_one
  origin/bookmark_two
  origin/master
"""

    sh.git.checkout("origin/bookmark_one")
    assert_git_count(2)
    assert_git_messages(['b', 'a'])

    sh.git.checkout("origin/bookmark_two")
    assert_git_count(3)
    assert_git_messages(['d', 'c', 'a'])


def test_clone_bookmark_not_at_tip(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b")
    sh.hg.update(rev=0)
    sh.hg.bookmark("bookmark_one")
    sh.hg.update('tip')

    clone_repo(git_dir, hg_repo)

    result = sh.git.branch(remote=True)
    print result.stdout
    assert result.stdout == """  origin/HEAD -> origin/master
  origin/bookmark_one
  origin/master
"""

    sh.git.checkout("origin/bookmark_one")
    assert_git_count(1)
    assert_git_messages(['a'])

    sh.git.checkout("master")
    assert_git_count(2)
    assert_git_messages(['b', 'a'])


# See issue #13
def test_clone_bookmark_named_master_not_at_tip(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b")
    sh.hg.update(rev=0)
    sh.hg.bookmark("master")
    sh.hg.update('tip')

    clone_repo(git_dir, hg_repo)


def test_clone_tags(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b")
    sh.hg.tag("THIS_IS_TAGGED")
    make_hg_commit("c")

    clone_repo(git_dir, hg_repo)

    result = sh.git.tag()
    print result.stdout
    assert result.stdout == "THIS_IS_TAGGED\n"


def test_clone_tag_with_spaces(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b")
    sh.hg.tag("THIS IS TAGGED")
    make_hg_commit("c")

    clone_repo(git_dir, hg_repo)

    result = sh.git.tag()
    assert result.stdout == "THIS___IS___TAGGED\n"


def test_clone_close_branch(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.branch('feature')
    make_hg_commit("b", "b")
    sh.hg.update('default')
    make_hg_commit("c")
    sh.hg.update('feature')
    write_to_test_file("d", "b")
    sh.hg.commit('--close-branch', message="d")

    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    # TODO: Perhaps it should make an archived tag instead of a branch...
    print sh.git.branch(remote=True)
    assert sh.git.branch(remote=True).stdout == """  origin/HEAD -> origin/master
  origin/branches/feature
  origin/master
"""

    assert_git_messages(['c', 'a'])
    sh.git.checkout("origin/branches/feature")
    assert_git_messages(['d', 'b', 'a'])


def test_clone_remove_file(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b")
    sh.hg.rm("test_file")
    sh.hg.commit(message="c")

    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)

    assert not p('a').exists()


# See issue #36
@pytest.mark.xfail
def test_clone_replace_file_by_dir(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b", filename="dir_or_file")
    sh.hg.rm("dir_or_file")
    sh.mkdir("dir_or_file")
    make_hg_commit("c", filename="dir_or_file/test_file")

    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)

    assert p('dir_or_file').isdir()
    assert p('dir_or_file/test_file').exists()


def test_clone_replace_dir_by_file(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.mkdir("dir_or_file")
    make_hg_commit("b", filename="dir_or_file/test_file")
    sh.hg.rm("dir_or_file/test_file")
    make_hg_commit("c", filename="dir_or_file")

    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)

    assert p('dir_or_file').isfile()


def test_clone_replace_file_by_symlink(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b", filename="link_or_file")
    sh.hg.rm("link_or_file")
    sh.ln("-s", "test_file", "link_or_file")
    sh.hg.add("link_or_file")
    sh.hg.commit(message="c")

    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)

    assert p('link_or_file').isfile()
    assert p('link_or_file').islink()


def test_clone_replace_symlink_by_file(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.ln("-s", "test_file", "link_or_file")
    sh.hg.add("link_or_file")
    sh.hg.commit(message="b")
    sh.hg.rm("link_or_file")
    make_hg_commit("c", filename="link_or_file")

    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)

    assert p('link_or_file').isfile()
    assert not p('link_or_file').islink()


# See issue #36
@pytest.mark.xfail
def test_clone_replace_symlink_by_dir(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.ln("-s", "test_file", "dir_or_link")
    sh.hg.add("dir_or_link")
    sh.hg.commit(message="b")
    sh.hg.rm("dir_or_link")
    sh.mkdir("dir_or_link")
    make_hg_commit("c", filename="dir_or_link/test_file")

    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)

    assert p('dir_or_link').isdir()
    assert p('dir_or_link/test_file').exists()


def test_clone_replace_dir_by_symlink(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.mkdir("dir_or_link")
    make_hg_commit("b", filename="dir_or_link/test_file")
    sh.hg.rm("dir_or_link/test_file")
    sh.ln("-s", "test_file", "dir_or_link")
    sh.hg.add("dir_or_link")
    sh.hg.commit(message="c")

    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)

    assert p('dir_or_link').isfile()
    assert p('dir_or_link').islink()
