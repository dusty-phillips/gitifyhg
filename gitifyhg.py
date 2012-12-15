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
# along with gitifyhg.  If not, see <http://www.gnu.org/licenses/>.import sh


import sys
import re

import sh
from path import path as p
from six.moves import configparser


class GitifyHGError(Exception):
    pass


def clone(hg_url):
    '''Set up a new git repository that is subconsciously linked to the hg
    repository in the hg_url. The link uses an intermediate 'patches' directory
    where patches are stored as input to/from git am/format_patch
    and hg import/export. Once cloned the state of the master branch will be
    the same as the state of the upstream default tip. However, the history
    may not be identical, since merged branches are ignored.'''
    repo_name = hg_url.split('/')[-1]
    git_repo = p(repo_name).abspath()
    git_repo.mkdir()
    gitify_hg = git_repo.joinpath('.gitifyhg')
    gitify_hg.mkdir()
    patches = gitify_hg.joinpath('patches')
    patches.mkdir()
    hg_repo = gitify_hg.joinpath('hg_clone')
    sh.cd(gitify_hg)
    sh.hg.clone(hg_url, hg_repo)
    sh.cd(hg_repo)

    # Disable colored output in all hg commands.
    hgconfig = configparser.ConfigParser()
    hgconfig.read('.hg/hgrc')
    hgconfig.add_section('color')
    hgconfig.set('color', 'mode', 'off')
    with open('.hg/hgrc', 'w') as file:
        hgconfig.write(file)

    hg_export(patches, "branch(default)")
    sh.cd(git_repo)
    sh.git.init()
    sh.git.config('alias.hgrebase', '!gitifyhg rebase')
    sh.git.config('alias.hgpush', '!gitifyhg push')
    git_import(patches)
    sh.git.branch('hgdefault')  # hgdefault points at last commit from upstream
    with open('.gitignore', 'w') as gitignore:
        gitignore.write('.gitignore\n')
        gitignore.write('.gitifyhg')

    empty_directory(patches)


def rebase():
    '''If commits have happened in the upstream hg default branch, rebase
    master onto those commits. This method assumes that gitifyhg created the
    current git repository, and therefore a .gitifyhg/hg_clone exists.'''

    git_dir = p('.').abspath()
    patches = git_dir.joinpath('.gitifyhg/patches')
    sh.cd('.gitifyhg/hg_clone')
    last_pulled_commit = sh.grep(sh.hg.log(rev='default'), 'changeset').stdout
    last_pulled_commit = int(re.match(
        b'changeset:\s+(\d+):', last_pulled_commit).groups()[0])
    sh.hg.pull(update=True)
    hg_export(patches, "{0}:default and branch(default)".format(
        last_pulled_commit + 1))
    sh.git.checkout('hgdefault')
    git_import(patches)
    sh.git.checkout('master')
    sh.git.rebase('hgdefault')
    empty_directory(patches)


def push():
    '''If commits have not happened upstream hg repo, but they have happened
    in the local master, push the new commits to upstream.'''
    git_dir = p('.').abspath()
    patches = git_dir.joinpath('.gitifyhg/patches')
    hg_clone = git_dir.joinpath('.gitifyhg/hg_clone')
    sh.cd(hg_clone)
    try:
        sh.hg.incoming()
    except sh.ErrorReturnCode:
        # Raises an exception when there are NO incoming patches, so we invert
        # the exception in else
        pass
    else:
        raise GitifyHGError("Refusing to push: upstream changes. Rebase first")

    sh.cd(git_dir)
    sh.git('format-patch', 'hgdefault..master', output_directory=patches)
    sh.cd(hg_clone)
    hg_import(patches)
    sh.hg.push()
    sh.cd(git_dir)
    sh.git.checkout('hgdefault')
    sh.git.merge('master')
    sh.git.checkout('master')


# HELPERS
def hg_export(patch_directory, revision_spec):
    '''Export all patches matching the given mercurial revspec into the
    patches directory.'''
    sh.hg.export(git=True, output=patch_directory.joinpath('%R.patch'),
        rev=revision_spec)


def hg_import(patch_directory):
    '''Import all patches in the patch_directory onto the current branch in
    hg'''
    patch_files = [patch_directory.joinpath(patch) for patch in
        sorted(patch_directory.listdir()) if patch.endswith('.patch')]
    sh.hg('import', patch_files)


def git_import(patch_directory):
    '''Import all patches in the patch_directory onto the current branch in
    git.'''
    patch_files = [patch_directory.joinpath(patch) for patch in
        sorted(patch_directory.listdir()) if patch.endswith('.patch')]
    sh.git.am(*patch_files)


def empty_directory(directory):
    for file in directory.listdir():
        directory.joinpath(file).remove()


# MAIN
def main():
    if sys.argv[1] in ('clone', 'rebase', 'push'):
        print(sys.argv[1:])
        globals()[sys.argv[1]](*sys.argv[2:])

if __name__ == '__main__':
    main()
