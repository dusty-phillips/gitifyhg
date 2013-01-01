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


@pytest.fixture
def git_repo(git_dir, hg_repo):
    '''Fixture that clones the hg repository into the given git dir

    :param git_dir: the directory to clone the git repo into
    :param hg_repo: the hg_repo fixture
    '''
    sh.cd(git_dir)
    sh.git.clone("gitifyhg::" + hg_repo, '.')
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


def assert_git_branch(branch_name):
    '''Assert that the git repo is on the named branch'''
    assert '* {0}'.format(branch_name) in sh.git.branch().stdout.decode('UTF-8')


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

    sh.cd(git_dir)
    sh.git.clone("gitifyhg::" + hg_repo)
    git_repo = git_dir.joinpath('hg_base')

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

    sh.cd(git_dir)
    sh.git.clone("gitifyhg::" + hg_repo)
    git_repo = git_dir.joinpath('hg_base')
    assert git_repo.exists()
    assert git_repo.joinpath('test_file').exists()
    with git_repo.joinpath('test_file').open() as file:
        assert file.read() == "a\nb"

    sh.cd(git_repo)
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

    sh.cd(git_dir)
    sh.git.clone("gitifyhg::" + hg_repo, "gitrepo")
    git_repo = git_dir.joinpath('gitrepo')
    sh.cd(git_repo)
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

    sh.cd(git_dir)
    sh.git.clone("gitifyhg::" + hg_repo)
    git_repo = git_dir.joinpath('hg_base')
    sh.cd(git_repo)
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

    sh.cd(git_dir)
    sh.git.clone("gitifyhg::" + hg_repo)
    sh.cd(git_dir.joinpath('hg_base'))

    result = sh.git.branch(remote=True)
    print result.stdout
    assert result.stdout == """  origin/HEAD -> origin/master
  origin/branches/default
  origin/featurebookmark
  origin/master
"""


def test_simple_push_from_master(hg_repo, git_repo):
    sh.cd(git_repo)
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
    # cloning bookmarks
    # cloning bookmarks that aren't at the tip of their branch
    # cloning tags
    # cloning empty repo
    # pushing to empty repo
    # pushing tags
    # pushing branches to named branches
    # pushing branches to bookmarks
    # pushing new branch
