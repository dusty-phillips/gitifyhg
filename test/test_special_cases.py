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
import sys
import os
from path import path as p
from .helpers import (clone_repo,
    assert_hg_count, assert_git_messages, write_to_test_file)


def test_unicode_path(tmpdir, git_dir, monkeypatch):
    monkeypatch.setenv('LANG', 'en_US.utf8')
    tmpdir = p(tmpdir.strpath).abspath()
    hg_base = tmpdir.joinpath(u'hg\u2020base')  # an hg repo to clone from
    hg_base.mkdir()
    sh.cd(hg_base)
    write_to_test_file(u'\u2020\n'.encode('utf-8'), u'\u2020')
    sh.hg.init()
    sh.hg.add(u'\u2020')
    sh.hg.commit(message=u"\u2020")
    sh.cd('..')

    sh.cd(git_dir)
    sh.git.clone("gitifyhg::" + hg_base, _err=sys.stderr)
    git_repo = git_dir.joinpath(u'hg\u2020base')
    sh.cd(git_repo)
    assert_git_messages([u"\u2020"])

    write_to_test_file(u'\u2020\n'.encode('utf-8'), u'\u2020')
    sh.git.add(u'\u2020')
    sh.git.commit(message=u"\u2020")
    sh.git.push()
    sh.cd(hg_base)
    sh.hg.update()
    assert_hg_count(2)

    write_to_test_file(u'\u2020\u2015'.encode('utf-8'), u'\u2020\u2015')
    sh.hg.add(u'\u2020\u2015')
    sh.hg.commit(message=u"\u2015")
    sh.cd(git_repo)
    sh.git.pull()
    assert_git_messages([u'\u2015', u"\u2020", u"\u2020"])


def test_executable_bit(git_dir, hg_repo):
    sh.cd(hg_repo)
    write_to_test_file("b")
    sh.chmod('644', 'test_file')
    sh.hg.add('test_file')
    sh.hg.commit(message='add file')
    sh.chmod('755', 'test_file')
    sh.hg.commit(message='make executable')
    sh.chmod('644', 'test_file')
    sh.hg.commit(message='make unexecutable')

    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    assert git_repo.joinpath('test_file').access(os.X_OK) == False
    sh.git.checkout('HEAD^')
    assert git_repo.joinpath('test_file').access(os.X_OK) == True
    sh.git.checkout('HEAD^')
    assert git_repo.joinpath('test_file').access(os.X_OK) == False

    sh.git.checkout('master')
    sh.chmod('755', 'test_file')
    sh.git.add('test_file')
    sh.git.commit(message="make executable again")
    sh.git.push()

    sh.cd(hg_repo)
    sh.update()
    assert git_repo.joinpath('test_file').access(os.X_OK) == True


def test_sym_link(git_dir, hg_repo):
    sh.cd(hg_repo)
    write_to_test_file('b')
    sh.hg.add('test_file')
    sh.hg.commit(message="b")
    sh.ln('-s', 'test_file', 'linked')
    sh.hg.add('linked')
    sh.hg.commit(message="c")
    git_repo = clone_repo(git_dir, hg_repo)
    sh.cd(git_repo)
    assert p('linked').islink()
    sh.ln('-s', 'test_file', 'second_link')
    sh.git.add('second_link')
    sh.git.commit(message="d")
    sh.git.push()
    sh.cd(hg_repo)
    sh.hg.update()
    assert p('second_link').islink()
