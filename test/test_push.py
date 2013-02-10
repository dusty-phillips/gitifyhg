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


from path import path as p
import sys
import pytest
import sh
from .helpers import (make_hg_commit, make_git_commit, clone_repo,
    assert_hg_count, assert_git_count, assert_hg_messages,
    assert_hg_author, assert_git_author)


def test_simple_push_from_master(hg_repo, git_dir):
    clone_repo(git_dir, hg_repo)
    make_git_commit("b")
    sh.git.push()

    sh.cd(hg_repo)
    assert_hg_count(2)
    sh.hg.update()
    with hg_repo.joinpath("test_file").open() as file:
        assert file.read() == "a\nb"


def test_simple_push_updates_remote(hg_repo, git_dir):
    clone_repo(git_dir, hg_repo)
    make_git_commit("b")
    sh.git.push()
    sh.git.fetch()
    assert_git_count(2, ref='origin')


def test_empty_repo(tmpdir):
    tmpdir = p(tmpdir.strpath).abspath()
    hg_base = tmpdir.joinpath('hg_base')
    hg_base.mkdir()
    sh.cd(hg_base)
    sh.hg.init()

    sh.cd(tmpdir)
    sh.git.clone("gitifyhg::" + hg_base, "git_clone")

    sh.cd("git_clone")
    assert "Initial commit" in sh.git.status().stdout
    make_git_commit("a")

    sh.git.push("origin", "master")

    sh.cd(hg_base)
    assert_hg_count(1)
    sh.hg.update()
    with open(hg_base.joinpath('test_file')) as file:
        assert file.read() == "a"


def test_push_conflict_default(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(hg_repo)
    make_hg_commit("b")
    sh.cd(git_repo)
    make_git_commit("c")
    assert sh.git.push(_ok_code=1).stderr.find("master -> master (non-fast-forward)") > 0


def test_push_conflict_default_double(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(hg_repo)
    make_hg_commit("b")
    sh.cd(git_repo)
    make_git_commit("c")
    assert sh.git.push(_ok_code=1).stderr.find("master -> master (non-fast-forward)") > 0
    assert sh.git.push(_ok_code=1).stderr.find("master -> master (non-fast-forward)") > 0


def test_push_conflict_default_double_non_english(git_dir, hg_repo, monkeypatch):
    monkeypatch.setenv('LANG', 'de_DE')
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(hg_repo)
    make_hg_commit("b")
    sh.cd(git_repo)
    make_git_commit("c")
    assert sh.git.push(_ok_code=1).stderr.find("master -> master (non-fast-forward)") > 0
    assert sh.git.push(_ok_code=1).stderr.find("master -> master (non-fast-forward)") > 0


def test_push_to_named(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.branch("branch_one")
    make_hg_commit("b")
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)

    sh.git.checkout("origin/branches/branch_one", track=True)
    make_git_commit("c")
    sh.git.push()

    sh.cd(hg_repo)
    assert_hg_count(3)

    sh.hg.update('tip')

    assert sh.hg.branch().stdout.strip() == "branch_one"


def test_push_to_named_with_spaces(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.branch("branch one")
    make_hg_commit("b")
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)

    sh.git.checkout("origin/branches/branch___one", track=True)
    make_git_commit("c")
    sh.git.push()

    sh.cd(hg_repo)
    assert_hg_count(3)

    sh.hg.update('tip')

    assert sh.hg.branch().stdout.strip() == "branch one"


def test_push_named_merge(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.branch("branch_one")
    make_hg_commit("b1", "b")
    sh.hg.update("default")
    make_hg_commit("c1", "c")

    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    sh.git.merge("origin/branches/branch_one")
    sh.git.push(_err=sys.stderr)

    sh.cd(hg_repo)
    sh.hg.update()
    assert_hg_count(4)


def test_push_new_named_branch(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    sh.git.checkout("-b", "branches/branch_one")
    make_git_commit("b")
    sh.git.push('--set-upstream', 'origin', 'branches/branch_one',
        _err=sys.stderr)

    sh.cd(hg_repo)
    assert_hg_count(2)
    sh.hg.update('tip')

    assert sh.hg.branch().stdout.strip() == "branch_one"


def test_push_conflict_named_branch(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.branch("feature")
    make_hg_commit('b')
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(hg_repo)
    make_hg_commit('c')
    sh.cd(git_repo)
    sh.git.checkout("origin/branches/feature", track=True)
    make_git_commit("d")
    assert sh.git.push(_ok_code=1).stderr.find(
        "branches/feature -> branches/feature (non-fast-forward)") > 0


def test_push_to_bookmark(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.bookmark('feature')
    make_hg_commit("b")

    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    sh.git.checkout("origin/feature", track=True)
    make_git_commit("c")
    sh.git.push()

    sh.cd(hg_repo)
    sh.hg.update()
    assert_hg_count(3)

    assert "feature" in sh.hg.bookmark().stdout
    with hg_repo.joinpath("test_file").open() as file:
        assert file.read() == "a\nbc"


def test_push_to_bookmark_with_spaces(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.bookmark('feature one')
    make_hg_commit("b")

    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    sh.git.checkout("origin/feature___one", track=True)
    make_git_commit("c")
    sh.git.push()

    sh.cd(hg_repo)
    sh.hg.update()
    assert_hg_count(3)

    assert "feature" in sh.hg.bookmark().stdout
    with hg_repo.joinpath("test_file").open() as file:
        assert file.read() == "a\nbc"


def test_push_with_multiple_bookmarks(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.bookmark('feature')
    make_hg_commit("b")
    sh.hg.update(rev=0)
    sh.hg.bookmark('feature2')
    make_hg_commit("c")

    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    sh.git.checkout("origin/feature", track=True)
    make_git_commit("d")
    sh.git.push()

    sh.cd(hg_repo)
    assert_hg_count(4)
    assert_hg_count(3, "0..feature")
    assert_hg_count(2, "0..feature2")
    sh.hg.update("feature")

    assert "feature" in sh.hg.bookmark().stdout
    with hg_repo.joinpath("test_file").open() as file:
        assert file.read() == "a\nbd"


@pytest.mark.xfail
def test_fetch_after_bad_push_updates_origin_master(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(hg_repo)
    make_hg_commit("b")
    sh.cd(git_repo)
    make_git_commit("c", "c")
    try:
        sh.git.push()
    except sh.ErrorReturnCode as ret:
        print("Output from failed push:")
        print('\t' + '\n\t'.join(ret[0].splitlines()))
    sh.git.fetch()
    assert_git_count(2, ref="origin/branches/default")
    assert_git_count(2, ref="origin/master")
    sh.git.pull('--rebase')
    assert_git_count(3)         # as with test_pull_auto_merge
    sh.git.push()
    sh.cd(hg_repo)
    assert_hg_count(3)


def test_push_after_rebase(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(hg_repo)
    make_hg_commit("b")
    sh.cd(git_repo)
    make_git_commit("c", "c")
    sh.git.pull('--rebase')
    assert_git_count(3)         # as with test_pull_auto_merge
    sh.git.push()
    sh.cd(hg_repo)
    assert_hg_count(3)


def test_push_email(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    make_git_commit("b")
    sh.git.push()
    sh.cd(hg_repo)
    sh.hg.update()
    assert_hg_author()
    hg_user = "Hg Author <hg@author.test>"
    make_hg_commit("c", user=hg_user)
    assert_hg_author(hg_user)
    sh.cd(git_repo)
    sh.git.pull()
    assert_git_author(ref="HEAD^")
    assert_git_author(author=hg_user)


def test_push_after_merge(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(hg_repo)
    make_hg_commit("b")
    sh.cd(git_repo)
    make_git_commit("c", "c")
    sh.git.pull()               # automerge
    assert_git_count(4)         # as with test_pull_auto_merge
    sh.git.push()
    sh.cd(hg_repo)
    assert_hg_count(4)


def test_push_two_commits(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    make_git_commit("b")
    make_git_commit("c")
    sh.git.push()
    sh.cd(hg_repo)
    assert_hg_count(3)


@pytest.mark.xfail
def test_push_new_bookmark(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    sh.git.checkout("-b", "anewbranch")
    make_git_commit("b")
    sh.git.push('--set-upstream', 'origin', 'anewbranch')

    sh.cd(hg_repo)
    assert_hg_count(2)
    assert "anewbranch" in sh.hg.bookmark().stdout
    sh.hg.update("anewbranch")
    assert "anewbranch" in sh.hg.tip().stdout

    # TODO: Currently, it does not create a new bookmark when trying to push to
    # a branch other than master or one named branches/<name>, which is supposed
    # to create a named branch. This needs to be fixed.


def test_push_tag(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    sh.git.tag("this_is_a_tag")
    sh.git.push(tags=True, _err=sys.stderr)

    sh.cd(hg_repo)
    assert "this_is_a_tag" in sh.hg.tags().stdout
    assert_hg_count(2)


def test_push_tag_with_subsequent_commits(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    sh.git.tag("this_is_a_tag")
    make_git_commit("b")
    sh.git.push("origin", "HEAD", tags=True, _err=sys.stderr)

    sh.cd(hg_repo)
    assert "this_is_a_tag" in sh.hg.tags().stdout
    assert_hg_count(3)
    hgsha = sh.hg.id(id=True).stdout.strip()
    assert_hg_messages(['Added tag this_is_a_tag for changeset %s' % hgsha,
        'b', 'a'])


def test_push_messaged_tag(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    sh.git.tag("this_is_a_tag", message="I tagged this with a message and user")
    sh.git.push(tags=True, _err=sys.stderr)

    sh.cd(hg_repo)
    assert "this_is_a_tag" in sh.hg.tags().stdout
    assert_hg_count(2)
    assert_hg_messages(['I tagged this with a message and user', 'a'])


def test_push_tag_different_branch(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.branch("branch_one")
    make_hg_commit("b")
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    sh.git.checkout("origin/branches/branch_one", track=True)
    sh.git.tag("this_is_a_tag")
    sh.git.push(tags=True, _err=sys.stderr)

    sh.cd(hg_repo)
    assert "this_is_a_tag" in sh.hg.tags().stdout
    assert_hg_count(3)
    sh.hg.update('tip')  # tip is the commit that added the tag
    assert sh.hg.branch().stdout.strip() == "branch_one"


def test_push_tag_with_spaces(git_dir, hg_repo):
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    sh.git.tag("this___is___a___tag")
    sh.git.push(tags=True)

    sh.cd(hg_repo)
    assert "this is a tag" in sh.hg.tags().stdout
