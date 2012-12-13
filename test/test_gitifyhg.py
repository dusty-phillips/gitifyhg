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


from gitifyhg import clone
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


# THE ACTUAL TESTS
# ================
def test_clone(hg_repo, git_dir):
    '''Ensures that a clone of an upstream hg repository contains the
    appropriate structure.'''
    sh.cd(git_dir)
    clone(hg_repo)
    git_repo = git_dir.joinpath('hg_base')
    hg_clone = git_repo.joinpath('.gitifyhg/hg_clone')

    assert git_repo.exists()
    assert git_repo.joinpath('test_file').exists()
    assert git_repo.joinpath('.git').isdir()
    assert hg_clone.joinpath('test_file').exists()
    assert hg_clone.joinpath('.hg').isdir()
    assert git_repo.joinpath('.gitifyhg/patches/').isdir()
    assert len(git_repo.joinpath('.gitifyhg/patches/').listdir()) == 0

    sh.cd(git_repo)
    assert sh.git.log(pretty='oneline').stdout.count(b'\n') == 1
    assert len(sh.git.status(short=True).stdout) == 0

    sh.cd(hg_clone)
    assert sh.grep(sh.hg.log(), 'changeset:').stdout.count(b'\n') == 1
    assert len(sh.hg.status().stdout) == 0

