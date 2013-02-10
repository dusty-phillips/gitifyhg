# Copyright 2012-2013 Dusty Phillips

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


import sh
from .helpers import (make_hg_commit, clone_repo, assert_git_author)


def test_author_all_good(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b", user="all is good <email@example.com>")

    clone_repo(git_dir, hg_repo)
    assert_git_author(author='all is good <email@example.com>')


def test_author_no_email(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b", user="no email supplied")

    clone_repo(git_dir, hg_repo)
    assert_git_author(author='no email supplied <unknown>')


def test_author_only_email(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b", user="<email@example.com>")

    clone_repo(git_dir, hg_repo)
    assert_git_author(author='<email@example.com>')


def test_author_only_email_no_quote(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b", user="email@example.com")

    clone_repo(git_dir, hg_repo)
    assert_git_author(author='<email@example.com>')


def test_author_no_space_before_email(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b", user="no space before email<email@example.com>")

    clone_repo(git_dir, hg_repo)
    assert_git_author(author='no space before email <email@example.com>')


# See issue #22
def test_author_no_email_quoting(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b", user="no email quoting email@example.com")

    clone_repo(git_dir, hg_repo)
    assert_git_author(author='no email quoting <email@example.com>')


# See issue #22
def test_author_missing_end_quote(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b", user="missing end quote <email@example.com")

    clone_repo(git_dir, hg_repo)
    assert_git_author(author='missing end quote <email@example.com>')


def test_author_obfuscated_email(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b", user="Author <obfuscated (at) email dot address>")

    clone_repo(git_dir, hg_repo)
    assert_git_author(author="Author <obfuscated (at) email dot address>")


# See issue #22
def test_author_abuse_quotes(git_dir, hg_repo):
    sh.cd(hg_repo)
    make_hg_commit("b", user="totally >>> bad <<< quote can be used in hg <><><")

    clone_repo(git_dir, hg_repo)
    assert_git_author(author="totally <bad  quote can be used in hg>")

