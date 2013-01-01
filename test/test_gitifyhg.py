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
import pytest
import sh


@pytest.fixture
def hg_repo(tmpdir):
    '''Fixture that creates an hg repository in a temporary directory
    gitifyhg can then be tested by cloaning that repo

    :param tmpdir: A temporary directory for the current test
    :return: a py.path inside the test's temporary directory that contains
        an initialized hg repository with a single commit'''
    tmpdir = p(tmpdir).abspath()
    hg_base = tmpdir.joinpath('hg_base')  # an hg repo to clone from
    hg_base.mkdir()
    sh.cd(hg_base)
    write_to_test_file('a\n')
    sh.hg.init()
    sh.hg.add('test_file')
    sh.hg.commit(message="a")
    sh.cd('..')

    return hg_base


@pytest.fixture
def git_dir(tmpdir):
    '''Fixture that creates a subdirectory in the tmpdir to hold the git clone.

    :param tmpdir: the temporary directory for the current test
    :return: a py.path inside the test's temporary directory that is an empty
        but existing directory.'''
    tmpdir = p(tmpdir).abspath()
    git_dir = tmpdir.joinpath('git_dir')
    git_dir.mkdir()
    return git_dir


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


def clone_repo(git_dir, hg_repo):
    '''Simple helper for the common task of cloning the given mercurial
    repository into the git directory. Changes the current working directory
    into the repository and returns the full path to the repository.'''
    sh.cd(git_dir)
    sh.git.clone("gitifyhg::" + hg_repo)
    git_repo = git_dir.joinpath('hg_base')
    sh.cd(git_repo)
    return git_repo


def assert_git_count(count):
    '''Assuming you are in a git repository, assert that ``count`` commits
    have been made to that repo.'''
    assert sh.git.log(pretty='oneline').stdout.count(b'\n') == count


def assert_git_messages(expected_lines):
    '''Assert that logging all git messages in order provides the given lines
    of output.

    :param expected_lines: The a list of str messages  that were passed into
        git or hg when commited, in reverser order
        (ie: most recent commits at the top or left)
    :return True if the message lines match the git repo in the current directory
        False otherwise.'''
    actual_lines = sh.git('--no-pager', 'log', pretty='oneline', color='never'
        ).strip().split('\n')
    actual_lines = [l.partition(' ')[-1] for l in actual_lines]
    assert actual_lines == expected_lines


def assert_hg_count(count):
    '''Assuming you are in an hg repository, assert that ``count`` commits
    have been made to that repo.'''
    assert sh.grep(sh.hg.log(), 'changeset:').stdout.count(b'\n') == count


# THE ACTUAL TESTS
# ================
def test_basic_clone(git_dir, hg_repo):
    '''Ensures that a clone of an upstream hg repository with only one branch
    and a couple commits contains the appropriate structure.'''

    sh.cd(hg_repo)
    write_to_test_file("b")
    sh.hg.commit(message="b")

    git_repo = clone_repo(git_dir, hg_repo)

    assert git_repo.exists()
    assert git_repo.joinpath('test_file').exists()
    assert git_repo.joinpath('.git').isdir()

    sh.cd(git_repo)
    assert_git_count(2)
    assert_git_messages(['b', 'a'])
    assert len(sh.git.status(short=True).stdout) == 0


def test_clone_linear_branch(git_dir, hg_repo):
    '''One branch after the other, no multiple parents.'''
    sh.cd(hg_repo)
    sh.hg.branch("featurebranch")
    write_to_test_file("b")
    sh.hg.commit(message="b")

    git_repo = clone_repo(git_dir, hg_repo)

    assert git_repo.exists()
    assert git_repo.joinpath('test_file').exists()
    with git_repo.joinpath('test_file').open() as file:
        assert file.read() == "a\nb"

    assert_git_count(2)
    assert_git_messages(['b', 'a'])
    print sh.git.branch(remote=True)
    assert sh.git.branch(remote=True).stdout == """  origin/HEAD -> origin/master
  origin/branches/default
  origin/branches/featurebranch
  origin/master
"""


def test_clone_simple_branch(git_dir, hg_repo):
    '''Two divergent branches'''
    sh.cd(hg_repo)
    sh.hg.branch("featurebranch")
    write_to_test_file("b")
    sh.hg.commit(message="b")
    sh.hg.update("default")
    write_to_test_file("c", "c")
    sh.hg.add('c')
    sh.hg.commit(message="c")

    clone_repo(git_dir, hg_repo)

    assert_git_count(2)
    assert_git_messages(['c', 'a'])
    sh.git.checkout("origin/branches/featurebranch")
    assert_git_messages(['b', 'a'])
    assert_git_count(2)


def test_clone_merged_branch(git_dir, hg_repo):
    sh.cd(hg_repo)
    sh.hg.branch("featurebranch")
    write_to_test_file("b")
    sh.hg.commit(message="b")
    sh.hg.update("default")
    write_to_test_file("c", "c")
    sh.hg.add('c')
    sh.hg.commit(message="c")
    sh.hg.merge('featurebranch')
    sh.hg.commit(message="merge")
    write_to_test_file("d")
    sh.hg.commit(message="d")

    clone_repo(git_dir, hg_repo)

    assert_git_count(5)
    assert_git_messages(['d', 'merge', 'c', 'b', 'a'])
    sh.git.checkout("origin/branches/featurebranch")
    assert_git_messages(['b', 'a'])
    assert_git_count(2)


@pytest.mark.xfail
def test_clone_anonymous_branch(git_dir, hg_repo):
    sh.cd(hg_repo)
    write_to_test_file("b")
    sh.hg.commit(message="b")
    sh.hg.update(rev=0)
    write_to_test_file("c")
    sh.hg.commit(message="c")

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
    write_to_test_file("b")
    sh.hg.commit(message="b")
    write_to_test_file("c")
    sh.hg.commit(message="c")
    sh.hg.update(rev=1)
    write_to_test_file("d")
    sh.hg.commit(message="d")
    sh.hg.update('default')
    write_to_test_file("e")
    sh.hg.commit(message="e")

    sh.cd(git_dir)
    result = sh.git.clone("gitifyhg::" + hg_repo)
    assert "more than one head" in result.stderr

    sh.cd(git_dir.joinpath('hg_base'))
    result = sh.git.branch(remote=True)
    print result.stdout
    assert result.stdout == """  origin/HEAD -> origin/master
  origin/branches/default
  origin/branches/featurebranch
  origin/master
"""

    # TODO: same more than one head issue as in test_clone_anonymous_branch
    assert False


def test_clone_bookmark(hg_repo, git_dir):
    sh.cd(hg_repo)
    sh.hg.bookmark("featurebookmark")
    write_to_test_file("b")
    sh.hg.commit(message="b")

    clone_repo(git_dir, hg_repo)

    result = sh.git.branch(remote=True)
    print result.stdout
    assert result.stdout == """  origin/HEAD -> origin/master
  origin/branches/default
  origin/featurebookmark
  origin/master
"""
    sh.git.checkout('origin/featurebookmark')
    assert_git_count(2)
    sh.git.checkout('master')
    assert_git_count(2)


def test_clone_divergent_bookmarks(hg_repo, git_dir):
    sh.cd(hg_repo)
    sh.hg.bookmark("bookmark_one")
    write_to_test_file("b")
    sh.hg.commit(message="b")
    sh.hg.update(rev=0)
    write_to_test_file("c")
    sh.hg.commit(message="c")
    sh.hg.bookmark("bookmark_two")
    write_to_test_file("d")
    sh.hg.commit(message="d")

    clone_repo(git_dir, hg_repo)

    result = sh.git.branch(remote=True)
    print result.stdout
    assert result.stdout == """  origin/HEAD -> origin/master
  origin/bookmark_one
  origin/bookmark_two
  origin/branches/default
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
    write_to_test_file("b")
    sh.hg.commit(message="b")
    sh.hg.update(rev=0)
    sh.hg.bookmark("bookmark_one")
    sh.hg.update('tip')

    clone_repo(git_dir, hg_repo)

    result = sh.git.branch(remote=True)
    print result.stdout
    assert result.stdout == """  origin/HEAD -> origin/master
  origin/bookmark_one
  origin/branches/default
  origin/master
"""

    sh.git.checkout("origin/bookmark_one")
    assert_git_count(1)
    assert_git_messages(['a'])

    sh.git.checkout("master")
    assert_git_count(2)
    assert_git_messages(['b', 'a'])


def test_clone_tags(git_dir, hg_repo):
    sh.cd(hg_repo)
    write_to_test_file("b")
    sh.hg.commit(message="b")
    sh.hg.tag("THIS_IS_TAGGED")
    write_to_test_file("c")
    sh.hg.commit(message="c")

    clone_repo(git_dir, hg_repo)

    result = sh.git.tag()
    print result.stdout
    assert result.stdout == "THIS_IS_TAGGED\n"


@pytest.mark.xfail
def test_clone_tag_with_spaces(git_dir, hg_repo):
    sh.cd(hg_repo)
    write_to_test_file("b")
    sh.hg.commit(message="b")
    sh.hg.tag("THIS IS TAGGED")
    write_to_test_file("c")
    sh.hg.commit(message="c")

    # TODO: hg allows tags with spaces, but git thinks that is an attrocious
    # thing to do. We need to either escape spaces in the tag in some way
    # or discard the tag with an appropriate warning message, not fail on the
    # clone.
    clone_repo(git_dir, hg_repo)

    result = sh.git.tag()
    assert result.stdout == "THIS_IS_TAGGED\n"


def test_clone_empty(tmpdir):
    tmpdir = p(tmpdir).abspath()
    hg_base = tmpdir.joinpath('hg_base')  # an hg repo to clone from
    hg_base.mkdir()
    sh.cd(hg_base)
    sh.hg.init()

    sh.cd(tmpdir)
    sh.git.clone("gitifyhg::" + hg_base, "git_clone")

    sh.cd("git_clone")
    assert_git_count(0)



def test_simple_push_from_master(hg_repo, git_dir):
    clone_repo(git_dir, hg_repo)
    write_to_test_file("b")
    sh.git.add("test_file")
    sh.git.commit(message="b")
    sh.git.push()

    sh.cd(hg_repo)
    assert_hg_count(2)
    sh.hg.update()
    with hg_repo.joinpath("test_file").open() as file:
        assert file.read() == "a\nb"


# Need to test:
    # cloning empty repo
    # pushing to empty repo
    # pushing tags
    # pushing branches to named branches
    # pushing branches to bookmarks
    # pushing new branch
