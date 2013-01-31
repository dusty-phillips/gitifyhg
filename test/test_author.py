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
import sys
import os
from path import path as p
from .helpers import (make_hg_commit, clone_repo, assert_git_count,
    assert_hg_count, assert_git_messages, assert_git_author, write_to_test_file,
    assert_git_notes)

def test_author_no_email(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b", user="noemailsupplied")

    clone_repo(git_dir, hg_repo)
    assert_git_author(author='noemailsupplied <unknown>')


def test_author_no_space_before_email(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b", user="nospace<email@example.com>")

    clone_repo(git_dir, hg_repo)
    assert_git_author(author='nospace <email@example.com>')


